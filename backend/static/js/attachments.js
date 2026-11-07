import { api } from "./api.js";

const dropzone = document.getElementById("attachment-dropzone");
const input = document.getElementById("attachment-input");
const list = document.getElementById("attachment-list");
const empty = document.getElementById("attachment-empty");
const errorBox = document.getElementById("attachment-error");
const errorText = document.getElementById("attachment-error-text");
const clearButton = document.getElementById("clear-attachments");
const activeCard = document.getElementById("active-resume");
const activeCount = document.getElementById("active-attachment-count");
const activeWord = document.getElementById("active-attachment-word");

if (dropzone && input && list) {
  const form = document.getElementById("upload-form");
  const maxMb = Number(form?.dataset.maxMb) || 10;
  const maxFiles = Number(dropzone.dataset.maxFiles) || 3;

  let busy = false;

  const show = (el) => el && el.classList.remove("hidden");
  const hide = (el) => el && el.classList.add("hidden");

  function showError(message) {
    if (!errorBox || !errorText) return;
    errorText.textContent = message;
    show(errorBox);
  }

  function hideError() {
    hide(errorBox);
  }

  function rowCount() {
    return list.querySelectorAll(".attachment-row").length;
  }

  function updateCount() {
    const count = rowCount();
    if (activeCount) activeCount.textContent = String(count);
    if (activeWord) activeWord.textContent = count === 1 ? "doc" : "docs";
    if (empty) empty.classList.toggle("hidden", count > 0);
    list.classList.toggle("hidden", count === 0);
    if (clearButton) clearButton.classList.toggle("hidden", count === 0);
  }

  function rowFromAttachment(attachment) {
    const row = document.createElement("li");
    row.className = "attachment-row";
    row.dataset.id = attachment.id;

    const badge = document.createElement("div");
    badge.className = "file-badge";
    badge.innerHTML =
      '<svg class="icon" aria-hidden="true"><use href="#i-file-text"/></svg>';

    const info = document.createElement("div");
    info.className = "attachment-info";

    const name = document.createElement("p");
    name.className = "attachment-name";
    name.textContent = attachment.filename;

    const meta = document.createElement("p");
    meta.className = "attachment-meta";
    const chunks = Number(attachment.chunks) || 0;
    meta.textContent = `${chunks} chunk${chunks === 1 ? "" : "s"}${
      attachment.truncated ? " · shortened" : ""
    }`;

    info.append(name, meta);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-btn danger remove-attachment";
    remove.dataset.id = attachment.id;
    remove.setAttribute("aria-label", `Remove ${attachment.filename}`);
    remove.innerHTML =
      '<svg class="icon" aria-hidden="true"><use href="#i-x"/></svg>';
    remove.addEventListener("click", () => removeOne(attachment.id, row));

    row.append(badge, info, remove);
    return row;
  }

  async function removeOne(id, row) {
    if (busy) return;
    busy = true;
    try {
      await api.delete(`/ingest/attachments/${encodeURIComponent(id)}`);
      row.remove();
      hideError();
      updateCount();
    } catch (err) {
      showError(err?.message || "Could not remove that document.");
    } finally {
      busy = false;
    }
  }

  async function uploadOne(file) {
    const body = new FormData();
    body.append("file", file);
    return api.upload("/ingest/attachments", body);
  }

  async function addFiles(files) {
    if (busy) return;
    const selected = Array.from(files || []);
    if (!selected.length) return;

    const current = rowCount();
    if (current >= maxFiles) {
      showError(`You can add up to ${maxFiles} supporting PDFs.`);
      return;
    }

    const accepted = [];
    for (const file of selected) {
      const isPdf =
        file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
      if (!isPdf) {
        showError(`${file.name} is not a PDF. Only PDF supporting documents are supported.`);
        continue;
      }
      if (file.size > maxMb * 1024 * 1024) {
        showError(`${file.name} is too large (max ${maxMb} MB).`);
        continue;
      }
      if (current + accepted.length >= maxFiles) {
        showError(`You can add up to ${maxFiles} supporting PDFs.`);
        break;
      }
      accepted.push(file);
    }

    if (!accepted.length) return;

    busy = true;
    dropzone.setAttribute("aria-disabled", "true");
    hideError();
    try {
      for (const file of accepted) {
        try {
          const result = await uploadOne(file);
          list.appendChild(rowFromAttachment(result));
          updateCount();
        } catch (err) {
          showError(err?.message || `Could not upload ${file.name}.`);
        }
      }
      if (activeCard) show(activeCard);
    } finally {
      busy = false;
      dropzone.removeAttribute("aria-disabled");
      input.value = "";
      updateCount();
    }
  }

  dropzone.addEventListener("click", (event) => {
    if (busy || event.target === input) return;
    input.click();
  });

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (!busy) input.click();
    }
  });

  input.addEventListener("change", () => addFiles(input.files));

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (!busy) dropzone.classList.add("is-dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("is-dragover");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragover");
    if (!busy) addFiles(event.dataTransfer?.files);
  });

  list.querySelectorAll(".remove-attachment").forEach((button) => {
    button.addEventListener("click", () => {
      const row = button.closest(".attachment-row");
      if (row) removeOne(button.dataset.id, row);
    });
  });

  if (clearButton) {
    clearButton.addEventListener("click", async () => {
      if (busy) return;
      const rows = Array.from(list.querySelectorAll(".attachment-row"));
      if (!rows.length) return;

      busy = true;
      try {
        for (const row of rows) {
          await api.delete(
            `/ingest/attachments/${encodeURIComponent(row.dataset.id)}`
          );
          row.remove();
        }
        hideError();
      } catch (err) {
        showError(err?.message || "Could not remove all supporting documents.");
      } finally {
        busy = false;
        updateCount();
      }
    });
  }

  updateCount();
}
