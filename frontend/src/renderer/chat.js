const CHAT_STORAGE_KEY = "loom-chat-history";

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

  renderMessages();
}