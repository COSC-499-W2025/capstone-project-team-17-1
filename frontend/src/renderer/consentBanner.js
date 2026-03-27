const API_BASE = "http://127.0.0.1:8002";
const AUTH_TOKEN_KEY = "loom_auth_token";
import { formatConsentSummary, shouldShowConsentBanner } from "./consentShared.mjs";

const CONSENT_COPY = {
  summary:
    "We use consent controls to manage local data processing and optional external AI features before portfolio outputs are shared or generated.",
  local:
    "Local consent allows Loom to analyze uploaded projects, generate portfolio summaries, and store customization data on this device.",
  external:
    "External AI consent allows Loom to send selected project metadata or user-approved files to external AI services for optional insights.",
};
let pendingConsentSettingsMessage = "";

function getBanner() {
  return document.getElementById("consent-banner");
}

function getModal() {
  return document.getElementById("consent-details-modal");
}

function buildAuthHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function fetchConsentState() {
  // Keep banner and settings aligned with the backend source
  const res = await fetch(`${API_BASE}/privacy-consent`, {
    headers: buildAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch consent state: ${res.status}`);
  }
  return res.json();
}

async function saveConsent(path, consent) {
  // Persist one consent choice without forcing the user
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: buildAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ consent }),
  });
  if (!res.ok) {
    throw new Error(`Failed to save consent: ${res.status}`);
  }
  return res.json();
}

function setBannerVisible(visible) {
  const banner = getBanner();
  if (!banner) return;
  banner.classList.toggle("hidden", !visible);
}

function setBannerBusy(isBusy, primaryLabel = "Accept") {
  const acceptAll = document.getElementById("consent-accept-all");
  const rejectExternal = document.getElementById("consent-reject-external");
  const detailsBtn = document.getElementById("consent-view-details");

  [acceptAll, rejectExternal, detailsBtn].forEach((button) => {
    if (button) button.disabled = isBusy;
  });

  if (acceptAll) {
    acceptAll.textContent = isBusy ? "Saving..." : primaryLabel;
  }
}

function setConsentSummary(state) {
  const summary = document.getElementById("consent-settings-summary");
  if (!summary) return;
  summary.textContent = formatConsentSummary(state);
}

export function setConsentSettingsMessage(message = "") {
  // Keep the latest message 
  pendingConsentSettingsMessage = message;
  const msg = document.getElementById("consent-settings-msg");
  if (!msg) return;
  msg.textContent = message;
}

function renderSettingsConsent(state) {
  // Settings acts as the long-term place
  const container = document.getElementById("settings-consent");
  if (!container) return;

  container.innerHTML = `
    <h3>Consent & Privacy</h3>
    <p class="settings-consent-text">${CONSENT_COPY.summary}</p>
    <div id="consent-settings-summary" class="consent-status-line"></div>
    <div class="consent-settings-grid">
      <div class="consent-settings-item">
        <div>
          <div class="consent-settings-label">Local processing consent</div>
          <p>${CONSENT_COPY.local}</p>
        </div>
        <button
          id="consent-toggle-local"
          class="consent-action-btn ${state.local_consent ? "danger" : ""}"
          type="button"
        >
          ${state.local_consent ? "Revoke" : "Grant"}
        </button>
      </div>
      <div class="consent-settings-item">
        <div>
          <div class="consent-settings-label">External AI consent</div>
          <p>${CONSENT_COPY.external}</p>
        </div>
        <button
          id="consent-toggle-external"
          class="consent-action-btn ${state.external_consent ? "danger" : ""}"
          type="button"
        >
          ${state.external_consent ? "Revoke" : "Grant"}
        </button>
      </div>
    </div>
    <div class="profile-actions">
      <button id="consent-settings-details" class="auth-btn" type="button">View Details</button>
      <span id="consent-settings-msg"></span>
    </div>
  `;

  setConsentSummary(state);
  setConsentSettingsMessage(pendingConsentSettingsMessage);

  document.getElementById("consent-toggle-local")?.addEventListener("click", async () => {
    await handleConsentToggle("/privacy-consent/local", !state.local_consent);
  });

  document.getElementById("consent-toggle-external")?.addEventListener("click", async () => {
    await handleConsentToggle("/privacy-consent/external", !state.external_consent);
  });

  document.getElementById("consent-settings-details")?.addEventListener("click", () => {
    openConsentDetails();
  });
}

function renderConsentDetails(state) {
  // The details modal explains exactly what each consent type allow
  const body = document.getElementById("consent-details-body");
  if (!body) return;

  body.innerHTML = `
    <p class="settings-consent-text">${CONSENT_COPY.summary}</p>
    <div class="consent-detail-list">
      <div class="consent-detail-item">
        <h4>Local Processing</h4>
        <p>${CONSENT_COPY.local}</p>
        <p class="consent-detail-status">Current status: ${state.local_consent ? "Granted" : "Not granted"}</p>
      </div>
      <div class="consent-detail-item">
        <h4>External AI</h4>
        <p>${CONSENT_COPY.external}</p>
        <p class="consent-detail-status">Current status: ${state.external_consent ? "Granted" : "Not granted"}</p>
      </div>
      <div class="consent-detail-item">
        <h4>How to revoke consent</h4>
        <p>You can revisit the Settings tab at any time and revoke either local processing consent or external AI consent.</p>
      </div>
    </div>
  `;
}

function openConsentDetails() {
  const modal = getModal();
  if (!modal) return;
  modal.classList.remove("hidden");
}

function closeConsentDetails() {
  const modal = getModal();
  if (!modal) return;
  modal.classList.add("hidden");
}

export async function refreshConsentUI() {
  // Refresh every consent surface together
  try {
    const state = await fetchConsentState();
    const bannerVisible = shouldShowConsentBanner(state);
    setBannerVisible(bannerVisible);
    renderSettingsConsent(state);
    renderConsentDetails(state);
    window.dispatchEvent(
      new CustomEvent("consent:state-changed", {
        detail: {
          ...state,
          bannerVisible,
        },
      })
    );
    return {
      ...state,
      bannerVisible,
    };
  } catch (_) {
    setBannerVisible(false);
    return {
      local_consent: false,
      external_consent: false,
      bannerVisible: false,
    };
  }
}

async function handleConsentToggle(path, granted) {
  setConsentSettingsMessage("Saving...");

  try {
    await saveConsent(path, granted);
    setConsentSettingsMessage(granted ? "Consent granted." : "Consent revoked.");
    await refreshConsentUI();
  } catch (_) {
    setConsentSettingsMessage("Failed to update consent.");
  }
}

export function renderConsentSettings() {
  refreshConsentUI();
}

export function initConsentBanner() {
  const acceptAll = document.getElementById("consent-accept-all");
  const detailsBtn = document.getElementById("consent-view-details");
  const rejectExternal = document.getElementById("consent-reject-external");
  const closeBtn = document.getElementById("consent-details-close");
  const modal = getModal();

  acceptAll?.addEventListener("click", async () => {
    setBannerBusy(true);
    try {
      setBannerVisible(false);
      await Promise.all([
        saveConsent("/privacy-consent/local", true),
        saveConsent("/privacy-consent/external", true),
      ]);
      await refreshConsentUI();
    } catch (_) {
      setBannerVisible(true);
    } finally {
      setBannerBusy(false);
    }
  });

  rejectExternal?.addEventListener("click", async () => {
    setBannerBusy(true, "Accept");
    try {
      setBannerVisible(false);
      await Promise.all([
        saveConsent("/privacy-consent/local", true),
        saveConsent("/privacy-consent/external", false),
      ]);
      await refreshConsentUI();
    } catch (_) {
      setBannerVisible(true);
    } finally {
      setBannerBusy(false, "Accept");
    }
  });

  detailsBtn?.addEventListener("click", () => {
    openConsentDetails();
  });

  closeBtn?.addEventListener("click", () => {
    closeConsentDetails();
  });

  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeConsentDetails();
    }
  });

  refreshConsentUI();
}
