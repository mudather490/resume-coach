import { api } from "./api.js";

const form = document.getElementById("upload-form");

if (form) {
  const maxMb = Number(form.dataset.maxMb) || 10;
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const emptyBox = document.getElementById("dropzone-empty");
  const fileBox = document.getElementById("dropzone-file");
  const fileName = document.getElementById("file-name");
  const fileSize = document.getElementById("file-size");
  const errorBox = document.getElementById("upload-error");
  const errorText = document.getElementById("upload-error-text");
  const successBox = document.getElementById("upload-success");
  const successTitle = document.getElementById("upload-success-title");
  const submit = document.getElementById("upload-submit");
  const submitLabel = document.getElementById("upload-submit-label");
  const submitIcon = document.getElementById("upload-submit-icon");
  const spinner = document.getElementById("upload-spinner");
  const activeCard = document.getElementById("active-resume");
  const activeName = document.getElementById("active-resume-name");
  const activeChunks = document.getElementById("active-resume-chunks");

  let file = null;
  let uploading = false;

  const show = (el) => el && el.classList.remove("hidden");
  const hide = (el) => el && el.classList.add("hidden");

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function updateSubmit() {
    submit.disabled = uploading || !file;
  }

  function setBusy(busy) {
    uploading = busy;
    submit.disabled = busy || !file;
    submitLabel.textContent = busy ? "Saving resume..." : "Save resume";
    spinner.classList.toggle("hidden", !busy);
    submitIcon.classList.toggle("hidden", busy);
    dropzone.setAttribute("aria-disabled", busy ? "true" : "false");
  }

  function showError(message) {
    errorText.textContent = message;
    show(errorBox);
    hide(successBox);
  }

  function resetFileSelection() {
    file = null;
    input.value = "";
    hide(fileBox);
    show(emptyBox);
    updateSubmit();
  }

  function showSelected(next) {
    file = next;
    fileName.textContent = next.name;
    fileSize.textContent = formatSize(next.size);
    hide(emptyBox);
    show(fileBox);
    hide(errorBox);
    hide(successBox);
    updateSubmit();
  }

  function pickFile(next) {
    if (!next) return;
    const isPdf =
      next.name.toLowerCase().endsWith(".pdf") || next.type === "application/pdf";
    if (!isPdf) {
      resetFileSelection();
      showError("Only PDF resumes are supported. Choose a different file.");
      return;
    }
    if (next.size > maxMb * 1024 * 1024) {
      resetFileSelection();
      showError(
        `That PDF is too large (max ${maxMb} MB). Choose a smaller file.`
      );
      return;
    }
    showSelected(next);
  }

  // Open the picker from the drop zone (but not when the input itself bubbles).
  dropzone.addEventListener("click", (event) => {
    if (uploading || event.target === input) return;
    input.click();
  });

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (!uploading) input.click();
    }
  });

  input.addEventListener("change", () => {
    pickFile(input.files && input.files[0]);
  });

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (!uploading) dropzone.classList.add("is-dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("is-dragover");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragover");
    if (uploading) return;
    pickFile(event.dataTransfer && event.dataTransfer.files[0]);
  });

  document.getElementById("choose-another").addEventListener("click", () => {
    if (!uploading) input.click();
  });

  document.getElementById("upload-another").addEventListener("click", () => {
    hide(successBox);
    hide(errorBox);
    resetFileSelection();
    input.click();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!file || uploading) return;

    setBusy(true);
    hide(errorBox);
    hide(successBox);

    const body = new FormData();
    body.append("file", file);

    try {
      const result = await api.upload("/ingest", body);

      if (activeCard) {
        activeName.textContent = result.filename;
        activeChunks.textContent = String(result.chunks);
        show(activeCard);
      }

      successTitle.textContent = `${result.filename} saved — ${result.chunks} chunk${
        result.chunks === 1 ? "" : "s"
      }`;
      show(successBox);
      resetFileSelection();
    } catch (err) {
      showError(
        err && err.message
          ? err.message
          : "Upload failed. Please try again."
      );
      // A rejected file is useless here — clear it so the user can pick a new one.
      if (err && (err.status === 400 || err.status === 413)) {
        resetFileSelection();
      }
    } finally {
      setBusy(false);
    }
  });

  updateSubmit();
}
