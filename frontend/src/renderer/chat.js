import { authFetch } from "./auth.js";
import { createSiennaVoicePlayer } from "./AskSienna/voicePlayer.js";
import { createSiennaSpeechInput } from "./AskSienna/speechInput.js";

const CHAT_STORAGE_KEY = "loom_sienna_history_v1";
const PROJECT_STORAGE_KEY = "loom_sienna_project_id_v1";
const VOICE_STORAGE_KEY = "loom_sienna_voice_v1";

const SIENNA_GREETING = "Hello, I'm Sienna, your Loom AI copilot. How can I help you today?";

function safeParse(raw, fallback) {
  try {
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function messageHtmlSafe(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function isDebugIntent(text) {
  const lowered = String(text || "").toLowerCase();
  return [
    "debug",
    "bug",
    "error",
    "issue",
    "fix",
    "stack trace",
    "inspect",
    "review code",
    "trace",
    "failing",
    "broken",
  ].some((token) => lowered.includes(token));
}

export function initChat() {
  const chatPage = document.getElementById("chat-page");
  const messagesEl = document.getElementById("sienna-messages");
  const inputEl = document.getElementById("sienna-input");
  const sendBtn = document.getElementById("sienna-send-btn");
  const micBtn = document.getElementById("sienna-mic-btn");
  const inputShellEl = document.getElementById("sienna-input-shell");
  const clearBtn = document.getElementById("sienna-clear-btn");
  const errorEl = document.getElementById("sienna-error");
  const projectSelectEl = document.getElementById("sienna-project-select");
  const voiceToggleEl = document.getElementById("sienna-voice-toggle");
  const emptyStateEl = document.getElementById("sienna-empty-state");

  if (!chatPage || !messagesEl || !inputEl || !sendBtn || !micBtn || !inputShellEl || !projectSelectEl || !voiceToggleEl || !emptyStateEl) {
    console.warn("[sienna] Ask Sienna elements not found. Skipping init.");
    return;
  }

  const voicePlayer = createSiennaVoicePlayer({ authFetch });
  const speechInput = createSiennaSpeechInput({
    onResult: ({ text }) => {
      if (!text) return;
      inputEl.value = text;
      autoResizeComposer();
      updateSendEnabled();
    },
    onStateChange: ({ listening }) => {
      micBtn.classList.toggle("active", listening);
      inputShellEl.classList.toggle("listening", listening);
      micBtn.setAttribute("aria-pressed", listening ? "true" : "false");
      micBtn.title = listening ? "Stop voice input" : "Voice input";
    },
    onError: (code) => {
      const friendly = (() => {
        if (!code) return "Voice input failed.";
        if (String(code).includes("not-allowed") || String(code).includes("permission")) {
          return "Microphone permission is blocked. Enable it in your browser settings.";
        }
        return "Voice input is unavailable right now.";
      })();
      setError(friendly, "warning");
    },
  });

  let messages = safeParse(localStorage.getItem(CHAT_STORAGE_KEY), []);
  if (!Array.isArray(messages)) messages = [];
  messages = messages
    .filter((m) => m && typeof m.content === "string" && (m.role === "user" || m.role === "assistant"))
    .map((m) => ({ role: m.role, content: m.content }));

  let selectedProjectId = localStorage.getItem(PROJECT_STORAGE_KEY) || "";
  let voiceEnabled = localStorage.getItem(VOICE_STORAGE_KEY) !== "false";
  let externalConsentGranted = true;
  let sending = false;
  let greeted = false;
  let availableProjects = [];

  voiceToggleEl.checked = voiceEnabled;

  function saveState() {
    // Store only text history to avoid localStorage bloat from base64 audio blobs.
    const historyOnly = messages.map((m) => ({ role: m.role, content: m.content }));
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(historyOnly));
    localStorage.setItem(PROJECT_STORAGE_KEY, selectedProjectId || "");
    localStorage.setItem(VOICE_STORAGE_KEY, String(voiceEnabled));
  }

  function setError(message = "", kind = "") {
    if (!errorEl) return;
    if (!message) {
      errorEl.textContent = "";
      errorEl.classList.add("hidden");
      errorEl.dataset.kind = "";
      return;
    }
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
    errorEl.dataset.kind = kind || "warning";
  }

  function setComposerEnabled(baseEnabled) {
    const enabled = Boolean(baseEnabled && externalConsentGranted);
    inputEl.disabled = !enabled;
    if (!enabled) {
      sendBtn.disabled = true;
    }
    micBtn.disabled = !enabled || !speechInput.supported;
    if (!selectedProjectId) {
      inputEl.placeholder = "Select a project to start chatting with Sienna...";
    } else if (!externalConsentGranted) {
      inputEl.placeholder = "Enable external AI consent in Settings > Privacy & Consent...";
    } else {
      inputEl.placeholder = "Ask Sienna about your project or Loom...";
    }
    updateSendEnabled();
  }

  function autoResizeComposer() {
    inputEl.style.height = "auto";
    const next = Math.min(Math.max(inputEl.scrollHeight, 46), 132);
    inputEl.style.height = `${next}px`;
  }

  function updateSendEnabled() {
    const hasText = Boolean((inputEl.value || "").trim());
    const canSend = Boolean(
      hasText
      && !sending
      && selectedProjectId
      && externalConsentGranted
      && !inputEl.disabled
    );
    sendBtn.disabled = !canSend;
    inputShellEl.classList.toggle("has-text", hasText);
  }

  function scrollToBottom(force = false) {
    const nearBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 120;
    if (force || nearBottom) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  function renderMessages(showThinking = false) {
    messagesEl.innerHTML = "";

    messages.forEach((message, index) => {
      const isUser = message.role === "user";
      const row = document.createElement("div");
      row.className = `sienna-message-row ${isUser ? "user" : "assistant"}`;

      const bubble = document.createElement("div");
      bubble.className = `sienna-bubble ${isUser ? "user" : "assistant"}`;
      bubble.innerHTML = messageHtmlSafe(message.content).replaceAll("\n", "<br>");

      if (!isUser) {
        const actions = document.createElement("div");
        actions.className = "sienna-message-actions";
        actions.innerHTML = `<button class="sienna-replay-btn" data-replay-index="${index}" type="button">Replay</button>`;
        bubble.appendChild(actions);
      }

      row.appendChild(bubble);
      messagesEl.appendChild(row);
    });

    if (showThinking) {
      const row = document.createElement("div");
      row.className = "sienna-message-row assistant";
      row.innerHTML = `<div class="sienna-bubble assistant sienna-thinking">Sienna is thinking...</div>`;
      messagesEl.appendChild(row);
    }

    const hasUserMessages = messages.some((m) => m.role === "user");
    emptyStateEl.classList.toggle("hidden", hasUserMessages || showThinking);
    scrollToBottom(true);
  }

  async function playReplyAudio(payload) {
    if (!voiceEnabled) return;
    void voicePlayer.playReplyAudio({
      text: payload.text,
      audio: payload.audio,
      audio_format: payload.audio_format,
      allowBrowserFallback: true,
    });
  }

  async function typeAssistantReply(payload) {
    const replyText = String(payload.text || "").trim();
    const message = {
      role: "assistant",
      content: "",
      audio: payload.audio || null,
      audio_format: payload.audio_format || "mp3",
    };
    messages.push(message);
    renderMessages(false);

    const chunks = replyText.split(/(\s+)/);
    for (let i = 0; i < chunks.length; i += 1) {
      message.content += chunks[i];
      const bubble = messagesEl.querySelector(".sienna-message-row:last-child .sienna-bubble.assistant");
      if (bubble) {
        // Keep replay action pinned at the bottom while text streams.
        bubble.innerHTML = `${messageHtmlSafe(message.content).replaceAll("\n", "<br>")}<div class="sienna-message-actions"><button class="sienna-replay-btn" data-replay-index="${messages.length - 1}" type="button">Replay</button></div>`;
      }
      scrollToBottom();
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 14));
    }

    saveState();
    playReplyAudio({
      text: message.content,
      audio: message.audio,
      audio_format: message.audio_format,
    });
  }

  async function ensureGreeting() {
    if (greeted) return;
    if (!messages.some((m) => m.role === "assistant")) {
      messages.push({ role: "assistant", content: SIENNA_GREETING });
      saveState();
      renderMessages(false);
    }
    if (voiceEnabled) {
      void voicePlayer.playReplyAudio({
        text: SIENNA_GREETING,
        allowBrowserFallback: true,
      });
    }
    greeted = true;
  }

  async function loadConsentState() {
    try {
      const res = await authFetch("/privacy-consent");
      if (!res.ok) throw new Error("consent check failed");
      const state = await res.json();
      externalConsentGranted = Boolean(state?.external_consent);
    } catch (_) {
      externalConsentGranted = false;
    }
  }

  async function loadProjects() {
    try {
      const res = await authFetch("/sienna/projects");
      if (!res.ok) {
        throw new Error(`Failed to load projects: ${res.status}`);
      }
      const data = await res.json();
      availableProjects = Array.isArray(data) ? data : [];
    } catch (err) {
      console.error("[sienna] Failed loading projects:", err);
      availableProjects = [];
      setError("Unable to load projects right now. Please try again.", "warning");
    }

    projectSelectEl.innerHTML = '<option value="">Select a project...</option>';
    availableProjects.forEach((project) => {
      const option = document.createElement("option");
      option.value = project.project_id;
      option.textContent = `${project.project_id} (${project.total_files || 0} files)`;
      projectSelectEl.appendChild(option);
    });

    if (selectedProjectId && availableProjects.some((p) => p.project_id === selectedProjectId)) {
      projectSelectEl.value = selectedProjectId;
    } else {
      selectedProjectId = "";
      projectSelectEl.value = "";
    }
    setComposerEnabled(Boolean(selectedProjectId));
    saveState();
  }

  async function sendMessage(prefilled = "") {
    if (sending) return;

    const text = (prefilled || inputEl.value || "").trim();
    if (!text) return;

    if (!selectedProjectId) {
      setComposerEnabled(false);
      setError("Select a project first to chat with Sienna.", "warning");
      return;
    }
    if (!externalConsentGranted) {
      setError("External AI consent is required for Ask Sienna. Open Settings > Privacy & Consent.", "warning");
      return;
    }

    sending = true;
    speechInput.stop();
    setError("");
    setComposerEnabled(true);
    sendBtn.disabled = true;
    inputEl.disabled = true;

    messages.push({ role: "user", content: text });
    saveState();
    renderMessages(true);
    inputEl.value = "";
    autoResizeComposer();
    updateSendEnabled();

    try {
      const payload = {
        message: text,
        project_id: selectedProjectId,
        debug: isDebugIntent(text),
        history: messages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
      };

      const res = await authFetch("/sienna/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || `Sienna request failed: ${res.status}`);
      }

      const reply = (data?.text || data?.reply || "").trim()
        || "I can only help with your Loom projects or Loom features.";

      renderMessages(false);
      await typeAssistantReply({
        text: reply,
        audio: data?.audio || null,
        audio_format: data?.audio_format || "mp3",
      });
    } catch (err) {
      console.error("[sienna] send failed:", err);
      renderMessages(false);
      setError(err?.message || "Sienna is unavailable right now.", "error");
      messages.push({
        role: "assistant",
        content: "I had trouble answering just now. Please try again in a moment.",
      });
      saveState();
      renderMessages(false);
    } finally {
      sending = false;
      inputEl.disabled = false;
      setComposerEnabled(Boolean(selectedProjectId));
      updateSendEnabled();
      inputEl.focus();
    }
  }

  function clearConversation() {
    voicePlayer.stop();
    speechInput.stop();
    messages = [{ role: "assistant", content: SIENNA_GREETING }];
    saveState();
    setError("");
    renderMessages(false);
    if (chatPage.classList.contains("active") && voiceEnabled) {
      void voicePlayer.playReplyAudio({
        text: SIENNA_GREETING,
        allowBrowserFallback: true,
      });
    }
  }

  sendBtn.addEventListener("click", () => sendMessage());
  micBtn.addEventListener("click", () => {
    if (!speechInput.supported) return;
    setError("");
    speechInput.toggle();
  });
  inputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  inputEl.addEventListener("input", () => {
    autoResizeComposer();
    updateSendEnabled();
  });
  clearBtn?.addEventListener("click", clearConversation);

  messagesEl.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const replayIndex = target.dataset.replayIndex;
    if (!replayIndex) return;
    const idx = Number(replayIndex);
    if (!Number.isInteger(idx) || idx < 0 || idx >= messages.length) return;
    const msg = messages[idx];
    if (!msg || msg.role !== "assistant") return;
    if (!voiceEnabled) return;
    void voicePlayer.playReplyAudio({
      text: msg.content,
      audio: msg.audio || null,
      audio_format: msg.audio_format || "mp3",
      allowBrowserFallback: true,
    });
  });

  projectSelectEl.addEventListener("change", () => {
    selectedProjectId = projectSelectEl.value || "";
    speechInput.stop();
    saveState();
    setComposerEnabled(Boolean(selectedProjectId));
    if (!selectedProjectId) {
      setError("Select a project first to chat with Sienna.", "warning");
    } else if (externalConsentGranted) {
      setError("");
    }
  });

  voiceToggleEl.addEventListener("change", () => {
    voiceEnabled = Boolean(voiceToggleEl.checked);
    if (!voiceEnabled) {
      voicePlayer.stop();
    }
    saveState();
  });

  document.addEventListener("navigation:page-changed", async (event) => {
    if (event.detail?.pageId !== "chat-page") return;
    await Promise.all([loadConsentState(), loadProjects()]);
    await ensureGreeting();
    if (!selectedProjectId) {
      setError("Select a project first to chat with Sienna.", "warning");
    } else if (!externalConsentGranted) {
      setError("External AI consent is required for Ask Sienna. Open Settings > Privacy & Consent.", "warning");
    } else {
      setError("");
    }
    renderMessages(false);
    autoResizeComposer();
    updateSendEnabled();
  });

  window.addEventListener("consent:state-changed", (event) => {
    externalConsentGranted = Boolean(event.detail?.external_consent);
    if (!externalConsentGranted) {
      setError("External AI consent is required for Ask Sienna. Open Settings > Privacy & Consent.", "warning");
    } else if (selectedProjectId) {
      setError("");
    }
    setComposerEnabled(Boolean(selectedProjectId));
    updateSendEnabled();
  });

  if (!messages.length) {
    messages.push({ role: "assistant", content: SIENNA_GREETING });
    saveState();
  }

  renderMessages(false);
  if (!speechInput.supported) {
    micBtn.classList.add("hidden");
  }
  autoResizeComposer();
  setComposerEnabled(Boolean(selectedProjectId));
  updateSendEnabled();
}
