import { openSettingsAndPromptLogin } from "./auth.js";

const CHAT_STORAGE_KEY = "loom-chat-history";
const API_BASE = "http://127.0.0.1:8002";
const AUTH_TOKEN_KEY = "loom_auth_token";

function buildAuthHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function fetchConsentState() {
  const res = await fetch(`${API_BASE}/privacy-consent`, {
    headers: buildAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch consent state: ${res.status}`);
  }
  return res.json();
}

export function initChat() {
  const chatPage = document.getElementById("chat-page");
  const messagesEl = document.getElementById("chat-messages");
  const inputEl = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send-btn");
  const clearBtn = document.getElementById("chat-clear-btn");
  const errorEl = document.getElementById("chat-error");
  const suggestionBtns = document.querySelectorAll(".chat-suggestion-btn");

  if (!chatPage || !messagesEl || !inputEl || !sendBtn) {
    console.warn("[chat] Chat elements not found. Skipping chat init.");
    return;
  }

  let messages = [];
  let sending = false;
  let externalConsentGranted = true;

  try {
    const saved = localStorage.getItem(CHAT_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        messages = parsed;
      }
    }
  } catch (err) {
    console.warn("[chat] Failed to parse saved chat history:", err);
  }

  if (messages.length === 0) {
    messages = [
      {
        role: "assistant",
        content:
          "Hi — I’m Loom Copilot. Ask me about resumes, portfolios, projects, or job matching."
      }
    ];
  }

  function saveMessages() {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  }

  function setError(message = "") {
    if (!errorEl) return;
    if (!message) {
      errorEl.textContent = "";
      errorEl.classList.add("hidden");
      return;
    }
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function openSettingsConsent() {
    openSettingsAndPromptLogin("privacy");
  }

  function updateConsentGate() {
    const blockedMessage = "External AI consent is required to use chat normally. Grant it in Settings > Privacy & Consent.";

    inputEl.disabled = !externalConsentGranted;
    sendBtn.disabled = sending || !externalConsentGranted;
    suggestionBtns.forEach((button) => {
      button.disabled = !externalConsentGranted;
    });

    if (!externalConsentGranted) {
      setError(blockedMessage);
      if (!chatPage.querySelector("[data-chat-consent-cta]")) {
        const action = document.createElement("button");
        action.type = "button";
        action.className = "ai-consent-btn";
        action.dataset.chatConsentCta = "true";
        action.textContent = "Open Settings";
        action.addEventListener("click", openSettingsConsent);
        errorEl?.insertAdjacentElement("afterend", action);
      }
      return;
    }

    setError("");
    chatPage.querySelector("[data-chat-consent-cta]")?.remove();
  }

  function renderMessages(showTyping = false) {
    messagesEl.innerHTML = "";

    messages.forEach((message) => {
      const row = document.createElement("div");
      row.className = `chat-message-row ${message.role}`;

      const bubble = document.createElement("div");
      bubble.className = `chat-bubble ${message.role}`;
      bubble.textContent = message.content;

      row.appendChild(bubble);
      messagesEl.appendChild(row);
    });

    if (showTyping) {
      const row = document.createElement("div");
      row.className = "chat-message-row assistant";

      const bubble = document.createElement("div");
      bubble.className = "chat-bubble assistant";
      bubble.textContent = "Thinking...";

      row.appendChild(bubble);
      messagesEl.appendChild(row);
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function sendMessage(prefilled = "") {
    if (sending) return;
    if (!externalConsentGranted) {
      updateConsentGate();
      return;
    }

    const text = (prefilled || inputEl.value || "").trim();
    if (!text) return;

    setError("");
    sending = true;
    sendBtn.disabled = true;

    messages.push({ role: "user", content: text });
    saveMessages();
    renderMessages(true);
    inputEl.value = "";

    try {
      if (!window.loomAI || typeof window.loomAI.chat !== "function") {
        throw new Error("window.loomAI.chat is not available. Check preload.js.");
      }

      const result = await window.loomAI.chat(messages);
      const reply =
        result && typeof result.reply === "string"
          ? result.reply
          : "No reply returned.";

      messages.push({ role: "assistant", content: reply });
      saveMessages();
      renderMessages(false);
    } catch (err) {
      console.error("[chat] send failed:", err);

      const message =
        err && err.message
          ? err.message
          : "Something went wrong while sending the message.";

      setError(message);

      messages.push({
        role: "assistant",
        content:
          "I hit an error while trying to respond. Check preload.js, main.js, and the ai:chat IPC handler."
      });

      saveMessages();
      renderMessages(false);
    } finally {
      sending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  sendBtn.addEventListener("click", () => {
    sendMessage();
  });

  inputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      messages = [
        {
          role: "assistant",
          content:
            "Chat cleared. Ask me anything about resumes, portfolios, projects, or jobs."
        }
      ];
      saveMessages();
      setError("");
      renderMessages();
    });
  }

  suggestionBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.dataset.prompt || "";
      sendMessage(prompt);
    });
  });

  window.addEventListener("consent:state-changed", (event) => {
    externalConsentGranted = Boolean(event.detail?.external_consent);
    updateConsentGate();
  });

  fetchConsentState()
    .then((state) => {
      externalConsentGranted = Boolean(state?.external_consent);
      updateConsentGate();
    })
    .catch(() => {
      externalConsentGranted = false;
      updateConsentGate();
    });

  renderMessages();
}
