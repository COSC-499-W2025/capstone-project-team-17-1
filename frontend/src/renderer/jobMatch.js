import { authFetch, isPrivateMode } from "./auth.js";
import {
  loadPortfolioCustomization,
  savePortfolioCustomization,
} from "./portfolioState.js";

let jobMatchInitialized = false;

function setStatus(message, kind = "info") {
  const el = document.getElementById("job-match-status");
  if (!el) return;
  el.textContent = message || "";
  el.dataset.kind = kind;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function renderJobTargetSection(customization) {
  const container = document.getElementById("portfolio-job-target-container");
  if (!container) return;

  const job = customization?.jobTarget ?? {
    title: "",
    company: "",
    description: "",
  };

  container.innerHTML = `
    <div class="form-grid">
      <label>
        <span>Job Title</span>
        <input
          id="job-target-title"
          type="text"
          value="${escapeHtml(job.title || "")}"
          placeholder="Example: Frontend Engineer"
        />
      </label>

      <label>
        <span>Company</span>
        <input
          id="job-target-company"
          type="text"
          value="${escapeHtml(job.company || "")}"
          placeholder="Example: Shopify"
        />
      </label>

      <label class="form-full-row">
        <span>Job Description</span>
        <textarea
          id="job-target-description"
          rows="8"
          placeholder="Paste the job description here to tailor your portfolio."
        >${escapeHtml(job.description || "")}</textarea>
      </label>

      <button id="analyze-job-btn" class="primary-btn">
        Analyze Job Match
      </button>
    </div>
  `;

  document.getElementById("analyze-job-btn")?.addEventListener("click", handleAnalyzeClick);
}

async function analyzeJobMatch() {
  const jd = document.getElementById("job-target-description")?.value;

  if (!jd || !jd.trim()) {
    setStatus("Please paste a job description first.", "warning");
    return [];
  }

  const res = await authFetch("/job-matching/rank", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jd }),
  });

  if (!res.ok) {
    throw new Error(`Job matching API failed: ${res.status}`);
  }

  const data = await res.json();

  if (Array.isArray(data)) return data;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.matches)) return data.matches;

  return [];
}

async function autoSelectFeaturedProjects(customization) {
  const matches = await analyzeJobMatch();

  window.__jobMatchResults = matches;

  if (!matches.length) return;

  const topProjects = matches.slice(0, 3).map((m) => m.project_id);
  customization.featuredProjectIds = topProjects;

  savePortfolioCustomization(customization);
  window.dispatchEvent(new CustomEvent("portfolio:customization-updated"));

  setStatus("Featured projects updated based on job match.", "success");
}

async function handleAnalyzeClick() {
  const btn = document.getElementById("analyze-job-btn");
  if (!btn) return;

  try {
    setStatus("Analyzing job description...", "info");
    btn.disabled = true;

    // persist the current job target fields before analyzing
    const customization = loadPortfolioCustomization();
    customization.jobTarget = {
      title: document.getElementById("job-target-title")?.value ?? "",
      company: document.getElementById("job-target-company")?.value ?? "",
      description: document.getElementById("job-target-description")?.value ?? "",
    };
    savePortfolioCustomization(customization);

    await autoSelectFeaturedProjects(customization);
  } catch (err) {
    console.error(err);
    setStatus("Job matching failed.", "error");
  } finally {
    btn.disabled = false;
  }
}

function renderJobMatchPage() {
  if (!isPrivateMode()) {
    const container = document.getElementById("portfolio-job-target-container");
    if (container) {
      container.innerHTML = `<p class="muted-text">Private Mode is required for Job Match.</p>`;
    }
    return;
  }

  const customization = loadPortfolioCustomization();
  renderJobTargetSection(customization);
}

export function initJobMatch() {
  if (jobMatchInitialized) return;
  jobMatchInitialized = true;

  document.addEventListener("navigation:page-changed", (event) => {
    if (event.detail?.pageId === "job-match-page") {
      renderJobMatchPage();
    }
  });

  document.addEventListener("auth:mode-changed", () => {
    const jobMatchPage = document.getElementById("job-match-page");
    if (jobMatchPage?.classList.contains("active")) {
      renderJobMatchPage();
    }
  });
}
