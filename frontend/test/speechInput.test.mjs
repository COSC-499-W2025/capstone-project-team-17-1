import test from "node:test";
import assert from "node:assert/strict";
import { createSiennaSpeechInput } from "../src/renderer/AskSienna/speechInput.mjs";

test("speech input is disabled in Electron desktop runtime", () => {
  globalThis.window = {
    api: { platform: "win32" },
  };

  const speech = createSiennaSpeechInput();
  assert.equal(speech.supported, false);
  assert.equal(speech.reason, "electron_unsupported");
});

test("speech input is disabled when browser API is unavailable", () => {
  globalThis.window = {};

  const speech = createSiennaSpeechInput();
  assert.equal(speech.supported, false);
  assert.equal(speech.reason, "browser_unsupported");
});

test("speech input toggles and emits interim/final text", () => {
  class FakeSpeechRecognition {
    constructor() {
      this.continuous = false;
      this.interimResults = false;
      this.lang = "en-US";
      this.maxAlternatives = 1;
      this.onstart = null;
      this.onresult = null;
      this.onerror = null;
      this.onend = null;
    }
    start() {
      this.onstart?.();
      this.onresult?.({
        resultIndex: 0,
        results: [
          [{ transcript: "hello " }],
          Object.assign([{ transcript: "world" }], { isFinal: true }),
        ],
      });
    }
    stop() {
      this.onend?.();
    }
  }

  // Mark first result as interim
  Object.defineProperty(FakeSpeechRecognition.prototype, "results", {
    value: undefined,
    writable: true,
  });

  globalThis.window = {
    SpeechRecognition: FakeSpeechRecognition,
  };

  const states = [];
  const results = [];
  const speech = createSiennaSpeechInput({
    onStateChange: (state) => states.push(state.listening),
    onResult: (value) => results.push(value.text),
  });

  assert.equal(speech.supported, true);
  speech.start();
  speech.stop();

  assert.equal(states[0], true);
  assert.equal(states.at(-1), false);
  assert.equal(results.length > 0, true);
});
