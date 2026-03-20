import test from "node:test";
import assert from "node:assert/strict";

import {
  formatConsentSummary,
  shouldShowConsentBanner,
} from "../src/renderer/consentShared.mjs";

test("shouldShowConsentBanner shows the cookie banner until local consent is granted", () => {
  assert.equal(
    shouldShowConsentBanner({ local_consent: false, external_consent: false }),
    true
  );
  assert.equal(
    shouldShowConsentBanner({ local_consent: false, external_consent: true }),
    true
  );
  assert.equal(
    shouldShowConsentBanner({ local_consent: true, external_consent: false }),
    false
  );
  assert.equal(
    shouldShowConsentBanner({ local_consent: true, external_consent: true }),
    false
  );
});

test("formatConsentSummary reports local and external consent status clearly", () => {
  assert.equal(
    formatConsentSummary({ local_consent: true, external_consent: false }),
    "Local processing: Granted • External AI: Not granted"
  );
  assert.equal(
    formatConsentSummary({ local_consent: false, external_consent: true }),
    "Local processing: Not granted • External AI: Granted"
  );
});
