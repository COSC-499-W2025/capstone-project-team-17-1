export function createSiennaSpeechInput({ onResult, onStateChange, onError } = {}) {
  // Electron desktop builds frequently trigger Chromium network speech backend
  // failures (e.g. chunked_data_pipe upload errors). Keep mic input disabled
  // there to avoid broken UX; browser contexts still use Web Speech API.
  const isElectronDesktop = Boolean(window?.api && typeof window.api.platform === "string");
  if (isElectronDesktop) {
    return {
      supported: false,
      reason: "electron_unsupported",
      listening: false,
      start: () => false,
      stop: () => false,
      toggle: () => false,
    };
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    return {
      supported: false,
      reason: "browser_unsupported",
      listening: false,
      start: () => false,
      stop: () => false,
      toggle: () => false,
    };
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";
  recognition.maxAlternatives = 1;

  let listening = false;
  let finalText = "";

  function updateState(next) {
    listening = Boolean(next);
    if (typeof onStateChange === "function") {
      onStateChange({ listening });
    }
  }

  recognition.onstart = () => {
    finalText = "";
    updateState(true);
  };

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result.isFinal) {
        finalText += `${result[0]?.transcript || ""} `;
      } else {
        interim += result[0]?.transcript || "";
      }
    }

    if (typeof onResult === "function") {
      onResult({
        text: `${finalText}${interim}`.trim(),
        finalText: finalText.trim(),
        isFinal: Boolean(finalText.trim()),
      });
    }
  };

  recognition.onerror = (event) => {
    if (typeof onError === "function") {
      onError(event?.error || "speech_error");
    }
  };

  recognition.onend = () => {
    updateState(false);
  };

  function start() {
    if (listening) return true;
    try {
      recognition.start();
      return true;
    } catch (err) {
      if (typeof onError === "function") {
        onError(err?.message || "speech_start_failed");
      }
      return false;
    }
  }

  function stop() {
    if (!listening) return true;
    try {
      recognition.stop();
      return true;
    } catch (err) {
      if (typeof onError === "function") {
        onError(err?.message || "speech_stop_failed");
      }
      return false;
    }
  }

  function toggle() {
    if (listening) return stop();
    return start();
  }

  return {
    supported: true,
    get listening() {
      return listening;
    },
    start,
    stop,
    toggle,
  };
}
