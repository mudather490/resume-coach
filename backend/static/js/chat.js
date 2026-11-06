import { api } from "./api.js";

const page = document.getElementById("chat-page");

if (page) {
  const messageLog = document.getElementById("message-log");
  const emptyState = document.getElementById("empty-state");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const historyPanel = document.getElementById("history-panel");
  const historyList = document.getElementById("history-list");
  const toggleHistoryBtn = document.getElementById("toggle-history");
  const newChatBtn = document.getElementById("new-chat");

  let sessionId = null;
  let loading = false;
  let hasResume = page.dataset.hasResume === "true";
  let thinkingTimer = null;

  const show = (el) => el && el.classList.remove("hidden");
  const hide = (el) => el && el.classList.add("hidden");
  const AUTO_GROW_MAX = 144;

  /* ---------------------------------------------------------------- */
  /* Helpers                                                           */
  /* ---------------------------------------------------------------- */

  function scrollToBottom() {
    messageLog.scrollTop = messageLog.scrollHeight;
  }

  function autoGrow() {
    input.style.height = "auto";
    const contentHeight = input.scrollHeight + 2;
    input.style.height = `${Math.min(contentHeight, AUTO_GROW_MAX)}px`;
    input.style.overflowY = contentHeight > AUTO_GROW_MAX ? "auto" : "hidden";
  }

  function updateSend() {
    sendBtn.disabled = loading || !input.value.trim();
  }

  function setLoading(value) {
    loading = value;
    input.disabled = value;
    newChatBtn.disabled = value;
    toggleHistoryBtn.disabled = value;
    document.querySelectorAll(".quick-action").forEach((button) => {
      button.disabled = value;
    });
    updateSend();
  }

  function formatSessionDate(iso) {
    if (!iso) return "";
    const normalized =
      iso.endsWith("Z") || /[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`;
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return "";
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const time = date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    if (date.toDateString() === now.toDateString()) return `Today ${time}`;
    if (date.toDateString() === yesterday.toDateString()) {
      return `Yesterday ${time}`;
    }
    return `${date.toLocaleDateString([], {
      month: "short",
      day: "numeric",
    })} ${time}`;
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
  }

  function flashCopied(button) {
    button.classList.add("copied");
    if (button.classList.contains("compact")) {
      const copyIcon = button.querySelector(".copy-icon");
      const checkIcon = button.querySelector(".check-icon");
      copyIcon?.classList.add("hidden");
      checkIcon?.classList.remove("hidden");
      setTimeout(() => {
        button.classList.remove("copied");
        copyIcon?.classList.remove("hidden");
        checkIcon?.classList.add("hidden");
      }, 1500);
      return;
    }
    const label = button.querySelector("span");
    if (!label) return;
    const original = label.textContent;
    label.textContent = "Copied";
    setTimeout(() => {
      label.textContent = original;
      button.classList.remove("copied");
    }, 1500);
  }

  function insertIntoInput(text) {
    input.value = text;
    input.dispatchEvent(new Event("input"));
    input.focus();
    autoGrow();
    input.scrollTop = input.scrollHeight;
  }

  function hideEmptyState() {
    hide(emptyState);
  }

  function showEmptyState() {
    show(emptyState);
  }

  /* ---------------------------------------------------------------- */
  /* Message rendering                                                 */
  /* ---------------------------------------------------------------- */

  function addUserMessage(text) {
    const node = document
      .getElementById("tpl-user-message")
      .content.firstElementChild.cloneNode(true);
    node.querySelector(".bubble-user").textContent = text;

    const copyButton = node.querySelector(".copy-btn");
    copyButton.addEventListener("click", async () => {
      await copyText(text);
      flashCopied(copyButton);
    });

    messageLog.appendChild(node);
    scrollToBottom();
    return node;
  }

  function addSourceChips(container, sources) {
    container.innerHTML = "";
    sources.forEach((source) => {
      const chip = document.createElement("span");
      chip.className = "source-chip";

      const name = document.createElement("span");
      name.className = "source-name";
      name.textContent = source.doc_id || "resume";
      chip.appendChild(name);

      if (source.page != null) {
        const page = document.createElement("span");
        page.className = "source-page";
        page.textContent = `· p.${source.page}`;
        chip.appendChild(page);
      }
      container.appendChild(chip);
    });
  }

  function addAssistantMessage({ html, text, sources, kind, error }) {
    const node = document
      .getElementById("tpl-assistant-message")
      .content.firstElementChild.cloneNode(true);
    const bubble = node.querySelector(".bubble-assistant");
    const actions = node.querySelector(".msg-actions");
    const uploadLink = node.querySelector(".upload-link");
    const sourcesButton = node.querySelector(".sources-btn");
    const sourcesBox = node.querySelector(".sources");

    if (error) {
      node.classList.add("msg-error");
      bubble.textContent = text || "Something went wrong.";
      hide(actions);
    } else if (html) {
      bubble.innerHTML = html;
    } else {
      bubble.textContent = text || "";
    }

    const plain = (bubble.innerText || text || "").trim();

    if (!error) {
      const copyButton = node.querySelector(".copy-btn");
      copyButton.addEventListener("click", async () => {
        await copyText(plain);
        flashCopied(copyButton);
      });

      node.querySelector(".insert-btn").addEventListener("click", () => {
        insertIntoInput(plain);
      });

      if (sources && sources.length) {
        show(sourcesButton);
        sourcesButton.querySelector(
          ".sources-label"
        ).textContent = `${sources.length} source${
          sources.length > 1 ? "s" : ""
        }`;
        addSourceChips(sourcesBox, sources);
        sourcesButton.addEventListener("click", () => {
          sourcesBox.classList.toggle("hidden");
          sourcesButton
            .querySelector(".chevron")
            .classList.toggle("is-open", !sourcesBox.classList.contains("hidden"));
        });
      }

      if (kind === "no_resume" || kind === "not_found") {
        show(uploadLink);
      }
    }

    messageLog.appendChild(node);
    scrollToBottom();
    return node;
  }

  function showThinking() {
    const node = document
      .getElementById("tpl-thinking")
      .content.firstElementChild.cloneNode(true);
    const elapsedEl = node.querySelector(".thinking-elapsed");
    const hintEl = node.querySelector(".thinking-hint");
    const started = Date.now();

    const tick = () => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      elapsedEl.textContent = `${seconds}s`;
      if (seconds >= 12) show(hintEl);
    };
    tick();
    thinkingTimer = setInterval(tick, 1000);

    messageLog.appendChild(node);
    scrollToBottom();
    return node;
  }

  function hideThinking(node) {
    if (thinkingTimer) {
      clearInterval(thinkingTimer);
      thinkingTimer = null;
    }
    node?.remove();
  }

  /* ---------------------------------------------------------------- */
  /* Sending                                                           */
  /* ---------------------------------------------------------------- */

  async function send(text, intent) {
    const clean = (text || "").trim();
    if (!clean || loading) return;

    hideEmptyState();

    if (!hasResume) {
      addAssistantMessage({
        text: "Upload a resume PDF first — then I can review, expand, or shorten it right away.",
        kind: "no_resume",
      });
      return;
    }

    addUserMessage(clean);
    input.value = "";
    autoGrow();
    setLoading(true);
    const thinking = showThinking();

    try {
      const result = await api.post("/chat", {
        message: clean,
        session_id: sessionId,
        intent: intent || undefined,
      });

      sessionId = result.session_id;
      hideThinking(thinking);
      addAssistantMessage({
        html: result.answer_html,
        text: result.answer,
        sources: result.sources,
        kind: result.kind,
      });

      if (result.kind === "no_resume") hasResume = false;
      refreshSessions();
    } catch (err) {
      hideThinking(thinking);
      addAssistantMessage({
        text:
          (err && err.message) ||
          "Could not get a response from the LLM provider. Check the backend log for details.",
        error: true,
      });
    } finally {
      setLoading(false);
      input.focus();
    }
  }

  /* ---------------------------------------------------------------- */
  /* Sessions / history                                                */
  /* ---------------------------------------------------------------- */

  function markCurrentSession() {
    historyList.querySelectorAll(".history-row").forEach((row) => {
      row.classList.toggle("is-current", row.dataset.sessionId === sessionId);
    });
  }

  function renderSessions(sessions) {
    historyList.innerHTML = "";
    if (!sessions.length) {
      const empty = document.createElement("div");
      empty.className = "history-empty";
      empty.textContent = "No previous chats yet";
      historyList.appendChild(empty);
      return;
    }

    sessions.forEach((session) => {
      const row = document.createElement("div");
      row.className = "history-row";
      row.dataset.sessionId = session.id;
      row.setAttribute("role", "button");
      row.tabIndex = 0;

      const dot = document.createElement("span");
      dot.className = "history-dot";

      const main = document.createElement("div");
      main.className = "history-main";

      const title = document.createElement("p");
      title.className = "history-title";
      title.textContent = (session.title || "Empty chat").trim() || "Empty chat";

      const date = document.createElement("p");
      date.className = "history-date";
      date.textContent = formatSessionDate(session.created_at);

      main.append(title, date);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "icon-btn danger delete-session";
      remove.setAttribute("aria-label", "Delete chat");
      remove.innerHTML =
        '<svg class="icon" aria-hidden="true"><use href="#i-trash-2"/></svg>';

      row.append(dot, main, remove);

      row.addEventListener("click", (event) => {
        if (event.target.closest(".delete-session")) return;
        openSession(session.id);
      });
      row.addEventListener("keydown", (event) => {
        if (event.target.closest(".delete-session")) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openSession(session.id);
        }
      });
      remove.addEventListener("click", (event) => {
        event.stopPropagation();
        removeSession(session.id);
      });

      historyList.appendChild(row);
    });

    markCurrentSession();
  }

  async function refreshSessions() {
    try {
      const sessions = await api.get("/sessions");
      renderSessions(Array.isArray(sessions) ? sessions : []);
    } catch {
      /* history is optional; keep the current list on failure */
    }
  }

  function clearMessages() {
    messageLog.querySelectorAll(".msg").forEach((node) => node.remove());
  }

  async function openSession(id) {
    if (loading) return;
    try {
      const session = await api.get(`/sessions/${encodeURIComponent(id)}`);
      sessionId = session.id;
      clearMessages();

      const messages = session.messages || [];
      if (messages.length) {
        hideEmptyState();
      } else {
        showEmptyState();
      }

      messages.forEach((message) => {
        if (message.role === "user") {
          addUserMessage(message.content);
        } else {
          addAssistantMessage({
            html: message.html,
            text: message.content,
          });
        }
      });

      hide(historyPanel);
      toggleHistoryBtn.classList.remove("is-active");
      markCurrentSession();
      scrollToBottom();
    } catch {
      refreshSessions();
    }
  }

  async function removeSession(id) {
    try {
      await api.delete(`/sessions/${encodeURIComponent(id)}`);
    } catch {
      /* already gone — remove it locally below */
    }
    if (id === sessionId) startNewChat();
    await refreshSessions();
  }

  function startNewChat() {
    sessionId = null;
    clearMessages();
    showEmptyState();
    input.value = "";
    autoGrow();
    updateSend();
    hide(historyPanel);
    toggleHistoryBtn.classList.remove("is-active");
    input.focus();
  }

  /* ---------------------------------------------------------------- */
  /* Events                                                            */
  /* ---------------------------------------------------------------- */

  document.querySelectorAll(".quick-action").forEach((button) => {
    button.addEventListener("click", () => {
      send(button.dataset.message, button.dataset.intent);
    });
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    autoGrow();
    updateSend();
    send(text);
  });

  input.addEventListener("input", () => {
    autoGrow();
    updateSend();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  newChatBtn.addEventListener("click", () => {
    if (!loading) startNewChat();
  });

  toggleHistoryBtn.addEventListener("click", async () => {
    if (loading) return;
    const opening = historyPanel.classList.contains("hidden");
    if (opening) {
      show(historyPanel);
      toggleHistoryBtn.classList.add("is-active");
      await refreshSessions();
    } else {
      hide(historyPanel);
      toggleHistoryBtn.classList.remove("is-active");
    }
  });

  // Format the server-rendered history dates on first paint.
  historyList.querySelectorAll(".history-date").forEach((el) => {
    el.textContent = formatSessionDate(el.dataset.createdAt);
  });
  markCurrentSession();

  autoGrow();
  updateSend();
}
