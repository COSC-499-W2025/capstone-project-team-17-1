import { authFetch, openSettingsAndPromptLogin, captureAuthDataEpoch, authDomWriteAllowed } from "./auth.js";
import { switchPage } from "./navigation.js";

const API_BASE = "http://127.0.0.1:8002";

async function fetchConsentState() {
  const res = await authFetch("/privacy-consent");
  if (!res.ok) {
    throw new Error(`Failed to fetch consent state: ${res.status}`);
  }
  return res.json();
}

function renderLocalConsentPrompt(container, { inline = false } = {}) {
  // Local processing consent is required
  container.innerHTML = `
    <div class="${inline ? "error-healthy-state" : "error-empty-state"}">
      <p>Local processing consent is required before running analysis. Grant consent in Settings to continue.</p>
      <button id="open-settings-consent-btn" class="ai-consent-btn">
        Open Settings
      </button>
    </div>
  `;

  document.getElementById("open-settings-consent-btn")?.addEventListener("click", () => {
    openSettingsAndPromptLogin("privacy");
  });
}

async function runErrorAnalysis(container) {
  // Re-check consent
  try {
    const consent = await fetchConsentState();
    if (!consent.local_consent) {
      renderLocalConsentPrompt(container, { inline: true });
      return;
    }
  } catch (err) {
    console.error("Failed to verify local consent:", err);
  }

  container.innerHTML = `
    <div class="error-loading">
      Running AI analysis...
    </div>
  `;

  const res = await authFetch("/errors/analyze", {
    method: "POST"
  });
  const payload = await res.json();

  if (payload.status === "local_consent_required") {
    renderLocalConsentPrompt(container, { inline: true });
    return;
  }

  if (payload.status === "consent_required") {
    container.innerHTML = `
      <div class="error-empty-state">
        <p>External AI consent is required to continue.</p>
        <button id="enable-ai-btn" class="ai-consent-btn">
          Enable AI Analysis
        </button>
      </div>
    `;

    document.getElementById("enable-ai-btn")?.addEventListener("click", async () => {
      await authFetch("/privacy-consent/external", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent: true })
      });

      loadErrorAnalysis();
    });
    return;
  }

  setTimeout(loadErrorAnalysis, 500);
}

export async function loadErrorAnalysis() {
  const epoch = captureAuthDataEpoch();
  const container = document.getElementById("error-analysis-container");
  if (!container) return;

  container.innerHTML = `
    <div class="error-loading">
      Loading analysis...
    </div>
  `;

  try {
    const res = await authFetch("/errors");
    const data = await res.json();

    if (!authDomWriteAllowed(epoch)) return;

    container.innerHTML = "";

    // -----------------------------
    // CONSENT REQUIRED
    // -----------------------------
    if (data.status === "consent_required") {
      container.innerHTML = `
        <div class="error-empty-state">
          <p>AI analysis is disabled.</p>
          <button id="enable-ai-btn" class="ai-consent-btn">
            Enable AI Analysis
          </button>
        </div>
      `;

      document.getElementById("enable-ai-btn")?.addEventListener("click", async () => {
        await authFetch("/privacy-consent/external", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ consent: true })
        });

        loadErrorAnalysis();
      });

      return;
    }

    if (data.status === "local_consent_required") {
      renderLocalConsentPrompt(container);
      return;
    }

    // -----------------------------
    // NO PROJECTS
    // -----------------------------
    if (data.status === "no_projects") {
      container.innerHTML = `
        <div class="error-empty-state">
          <h3>No projects found 📁</h3>
          <p>Upload a project to enable AI error analysis.</p>
        </div>
      `;
      return;
    }

    // -----------------------------
    // NEVER ANALYZED
    // -----------------------------
    if (data.status === "not_analyzed") {
      container.innerHTML = `
        <div class="error-healthy-state">
          <p>No AI analysis has been run yet.</p>
          <button id="run-analysis-btn" class="ai-consent-btn">
            Run AI Analysis
          </button>
        </div>
      `;

      document.getElementById("run-analysis-btn")?.addEventListener("click", async () => {
        await runErrorAnalysis(container);
      });

      return;
    }

if (data.status === "ok") {

  // Header bar with re-run button
  const headerBar = document.createElement("div");
  headerBar.className = "error-header-bar";
  headerBar.innerHTML = `
    <button id="rerun-analysis-btn" class="ai-consent-btn small">
      Re-run
    </button>
  `;
  container.appendChild(headerBar);

  document.getElementById("rerun-analysis-btn")?.addEventListener("click", async () => {
    await runErrorAnalysis(container);
  });

  // No issues found
  if (!data.errors || data.errors.length === 0) {
    const healthyBox = document.createElement("div");
    healthyBox.className = "error-healthy-state";
    healthyBox.innerHTML = `
      ✓ No issues found. Projects look healthy.
    `;
    container.appendChild(healthyBox);
    return;
  }

  // Render actual errors
  data.errors.forEach(error => {
    const box = document.createElement("div");
    box.className = "error-item";

    box.innerHTML = `
      <div class="error-header">
        <div class="severity-circle ${error.severity}"></div>
        <div class="error-title">${error.title}</div>
      </div>

      <div class="error-project">Project: ${error.project_id}</div>
      <div class="error-detail">${error.detail}</div>

      <div class="error-actions">
        <button class="fix-btn">Fix Issue</button>
      </div>
    `;

    box.querySelector(".fix-btn")?.addEventListener("click", () => {
      const prompt = `Please help me fix this issue in project "${error.project_id}".\n\nError: ${error.title}\nDetails: ${error.detail}`;
      const siennaTab = document.querySelector('.nav-tab[data-tab="chat"]');
      document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
      siennaTab?.classList.add("active");
      switchPage("chat-page");
      document.dispatchEvent(new CustomEvent("sienna:autoprompt", {
        detail: {
          projectId: error.project_id,
          message: prompt,
        },
      }));
    });

    container.appendChild(box);
  });

  return;
}

    // -----------------------------
    // FALLBACK
    // -----------------------------
    container.innerHTML = `
      <div class="error-empty-state">
        Unexpected response from server.
      </div>
    `;

  } catch (err) {
    if (authDomWriteAllowed(epoch)) {
      container.innerHTML = `
      <div class="error-empty-state">
        Failed to load error analysis.
      </div>
    `;
    }
    console.error("Error loading analysis:", err);
  }
}
