export function createSiennaVoicePlayer({ authFetch }) {
  let activeAudio = null;
  let activeObjectUrl = null;

  function cleanupObjectUrl() {
    if (activeObjectUrl) {
      URL.revokeObjectURL(activeObjectUrl);
      activeObjectUrl = null;
    }
  }

  function stop() {
    if (activeAudio) {
      try {
        activeAudio.pause();
      } catch (_) {}
      activeAudio = null;
    }
    cleanupObjectUrl();
    if ("speechSynthesis" in window) {
      // Last-resort fallback speech should never overlap with OpenAI audio
      window.speechSynthesis.cancel();
    }
  }

  async function playAudioBase64(audioBase64, format = "mp3") {
    if (!audioBase64) return false;
    stop();
    try {
      const binary = atob(audioBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: `audio/${format || "mp3"}` });
      const url = URL.createObjectURL(blob);
      activeObjectUrl = url;
      const audio = new Audio(url);
      activeAudio = audio;
      await audio.play();
      audio.addEventListener("ended", () => {
        if (activeAudio === audio) {
          activeAudio = null;
        }
        cleanupObjectUrl();
      });
      return true;
    } catch (err) {
      console.warn("[sienna-voice] Failed to play OpenAI audio:", err);
      return false;
    }
  }

  async function requestVoiceFromBackend(text) {
    const value = String(text || "").trim();
    if (!value) return null;
    try {
      const res = await authFetch("/sienna/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      if (!data?.audio) return null;
      return {
        audio: data.audio,
        audio_format: data.audio_format || "mp3",
      };
    } catch (err) {
      console.warn("[sienna-voice] Backend voice request failed:", err);
      return null;
    }
  }

  function fallbackBrowserTts(text) {
    if (!("speechSynthesis" in window)) return false;
    const value = String(text || "").trim();
    if (!value) return false;
    try {
      stop();
      const utterance = new SpeechSynthesisUtterance(value);
      utterance.lang = "en-US";
      utterance.rate = 1;
      utterance.pitch = 1.02;
      window.speechSynthesis.speak(utterance);
      return true;
    } catch (_) {
      return false;
    }
  }

  async function playReplyAudio({ text, audio, audio_format, allowBrowserFallback = true }) {
    if (audio) {
      const ok = await playAudioBase64(audio, audio_format || "mp3");
      if (ok) return true;
    }

    const synthesized = await requestVoiceFromBackend(text);
    if (synthesized?.audio) {
      const ok = await playAudioBase64(synthesized.audio, synthesized.audio_format || "mp3");
      if (ok) return true;
    }

    if (allowBrowserFallback) {
      return fallbackBrowserTts(text);
    }
    return false;
  }

  return {
    stop,
    playReplyAudio,
  };
}
