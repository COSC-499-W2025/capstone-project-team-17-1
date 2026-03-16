import { fetchProjects } from "./projects.js";
import { authFetch, isPrivateMode } from "./auth.js";
import { loadPortfolioResume } from "./portfolioResume.js";
import {
  loadPortfolioCustomization,
  savePortfolioCustomization,
} from "./portfolioCustomizationState.js";

const SECTION_LABELS = [
  { id: "resume-summary", label: "Resume Snapshot" },
  { id: "top-projects", label: "Top 3 Project Showcase" },
  { id: "portfolio-stats", label: "Portfolio Stats" },
  { id: "skills-timeline", label: "Skills Timeline" },
  { id: "activity-heatmap", label: "Activity Heatmap" },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getStatusEl() {
  return document.getElementById("portfolio-customization-status");
}

function setStatus(message, kind = "info") {
  const el = getStatusEl();
  if (!el) return;
  el.textContent = message || "";
  el.dataset.kind = kind;
}

function renderPublicModeMessage() {
  const toggleContainer = document.getElementById("portfolio-section-toggle-container");
  const featuredContainer = document.getElementById("portfolio-featured-projects-container");
  const editorContainer = document.getElementById("portfolio-project-editor-container");
  const saveBtn = document.getElementById("portfolio-customization-save-btn");
  const jobContainer = document.getElementById("portfolio-job-target-container");

  if (toggleContainer) {
    toggleContainer.innerHTML = `<p class="resume-summary-text">Switch to Private Mode to customize your portfolio.</p>`;
  }
  if (featuredContainer) {
    featuredContainer.innerHTML = `<p class="resume-summary-text">Featured project selection is only available in Private Mode.</p>`;
  }
  if (editorContainer) {
    editorContainer.innerHTML = `<p class="resume-summary-text">Project portfolio edits are only available in Private Mode.</p>`;
  }
  if (saveBtn) {
    saveBtn.disabled = true;
  }
  if (jobContainer) {
    jobContainer.innerHTML = `<p class="resume-summary-text">Switch to Private Mode to analyze job descriptions.</p>`;
  }
}

function renderSectionToggles(customization) {
  const container = document.getElementById("portfolio-section-toggle-container");
  if (!container) return;

  container.innerHTML = SECTION_LABELS.map(
    (section) => `
      <label class="customization-toggle-item">
        <input
          type="checkbox"
          data-section-visibility="${section.id}"
          ${customization.sectionVisibility?.[section.id] !== false ? "checked" : ""}
        />
        <span>${escapeHtml(section.label)}</span>
      </label>
    `
  ).join("");
}

function renderFeaturedProjects(projects, customization) {
  const container = document.getElementById("portfolio-featured-projects-container");
  if (!container) return;

  const selected = new Set(customization.featuredProjectIds || []);

  if (!projects.length) {
    container.innerHTML = `<p class="resume-summary-text">Upload projects first to choose featured items.</p>`;
    return;
  }

  const matchScores = window.__jobMatchResults || [];
  const scoreMap = new Map(matchScores.map(m => [m.project_id, m.score]));

  container.innerHTML = projects
    .map(
      (project) => `
        <label class="customization-project-pick">
          <input
            type="checkbox"
            data-featured-project="${escapeHtml(project.project_id)}"
            ${selected.has(project.project_id) ? "checked" : ""}
          />
          <div>
            <div class="customization-project-title">${escapeHtml(project.project_id)}</div>
            <div class="customization-project-meta">
              ${project.total_files || 0} files • ${project.total_skills || 0} skills
              ${scoreMap.has(project.project_id)
                ? ` • <span class="job-match-score">${Math.round(scoreMap.get(project.project_id) * 100)}% match</span>`
                : ""}
            </div>
          </div>
        </label>
      `
    )
    .join("");
}

function renderProjectEditors(projects, customization) {
  const container = document.getElementById("portfolio-project-editor-container");
  if (!container) return;

  if (!projects.length) {
    container.innerHTML = `<p class="resume-summary-text">No projects available for customization yet.</p>`;
    return;
  }

  container.innerHTML = projects
    .map((project) => {
      const override = customization.projectOverrides?.[project.project_id] || {};
      const isFeatured = (customization.featuredProjectIds || []).includes(project.project_id);
      const index = (customization.featuredProjectIds || []).indexOf(project.project_id);
      const rank = index >= 0 ? index + 1 : 1;

      return `
        <div class="customization-project-editor" data-project-editor="${escapeHtml(project.project_id)}">
          <div class="customization-project-editor-header">
            <div>
              <h3>${escapeHtml(project.project_id)}</h3>
              <p class="resume-summary-text">
                ${project.total_files || 0} files analyzed • ${project.total_skills || 0} skill signals
              </p>
            </div>
            <div class="customization-project-editor-meta">
              <label class="customization-inline-check">
                <input
                  type="checkbox"
                  data-project-selected="${escapeHtml(project.project_id)}"
                  ${isFeatured ? "checked" : ""}
                />
                <span>Featured</span>
              </label>
              <label class="customization-rank-wrap">
                <span>Order</span>
                <input
                  type="number"
                  min="1"
                  max="3"
                  data-project-rank="${escapeHtml(project.project_id)}"
                  value="${rank}"
                />
              </label>
            </div>
          </div>

          <div class="customization-form-grid">
            <label>
              <span>Key role</span>
              <input
                type="text"
                data-project-key-role="${escapeHtml(project.project_id)}"
                value="${escapeHtml(override.keyRole || "")}"
                placeholder="Example: Frontend integration lead"
              />
            </label>

            <label class="customization-full-row">
              <span>Evidence of success</span>
              <textarea
                data-project-evidence="${escapeHtml(project.project_id)}"
                rows="3"
                placeholder="Example: Built the portfolio UI, integrated the summary endpoints, and improved milestone demo readiness."
              >${escapeHtml(override.evidence || "")}</textarea>
            </label>

            <label class="customization-full-row">
              <span>Portfolio blurb</span>
              <textarea
                data-project-blurb="${escapeHtml(project.project_id)}"
                rows="3"
                placeholder="Short description that should appear in the portfolio showcase."
              >${escapeHtml(override.portfolioBlurb || "")}</textarea>
            </label>
          </div>
        </div>
      `;
    })
    .join("");

    const checkboxes = container.querySelectorAll("[data-project-selected]");

    checkboxes.forEach((cb) => {
      cb.addEventListener("change", () => {
        const checked = container.querySelectorAll("[data-project-selected]:checked");

        if (checked.length <= 3) {
          setStatus("");
        }
        if (checked.length > 3) {
          cb.checked = false;
          setStatus("You can only feature up to 3 projects.", "warning");
        }
      });
    });
}

function collectCustomization(projects) {
  const current = loadPortfolioCustomization();

  const sectionVisibility = {};
  SECTION_LABELS.forEach((section) => {
    const input = document.querySelector(`[data-section-visibility="${section.id}"]`);
    sectionVisibility[section.id] = input ? !!input.checked : true;
  });

  let featuredRaw = projects
    .filter((project) => {
      const checked = document.querySelector(`[data-project-selected="${project.project_id}"]`);
      return checked?.checked;
    })
    .map((project) => {
      const rankInput = document.querySelector(`[data-project-rank="${project.project_id}"]`);
      const rank = Number(rankInput?.value || 99);
      return { id: project.project_id, rank };
    })
    .sort((a, b) => a.rank - b.rank);

  if (featuredRaw.length > 3) {
    setStatus("You can only select up to 3 featured projects. The top 3 were used.", "warning");
  }

  featuredRaw = featuredRaw
    .slice(0, 3)
    .map((entry) => entry.id);

  const projectOverrides = {};
  projects.forEach((project) => {
    const keyRole = document.querySelector(`[data-project-key-role="${project.project_id}"]`)?.value?.trim() || "";
    const evidence = document.querySelector(`[data-project-evidence="${project.project_id}"]`)?.value?.trim() || "";
    const portfolioBlurb = document.querySelector(`[data-project-blurb="${project.project_id}"]`)?.value?.trim() || "";

    projectOverrides[project.project_id] = {
      keyRole,
      evidence,
      portfolioBlurb,
    };
  });

  // get job info from ui
  const jobTarget = {
    title: document.getElementById("job-target-title")?.value?.trim() || "",
    company: document.getElementById("job-target-company")?.value?.trim() || "",
    description: document.getElementById("job-target-description")?.value?.trim() || ""
  };

  return {
    ...current,
    sectionVisibility,
    featuredProjectIds: featuredRaw,
    projectOverrides,
    jobTarget
  };
}

async function persistProjectOverrides(projects, customization) {
  const selectedIds = new Set(customization.featuredProjectIds || []);

  const updates = projects.map(async (project) => {
    const override = customization.projectOverrides?.[project.project_id] || {};
    const rank = (customization.featuredProjectIds || []).indexOf(project.project_id);

    return authFetch(`/projects/${encodeURIComponent(project.project_id)}/edit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        key_role: override.keyRole || null,
        evidence: override.evidence || null,
        portfolio_blurb: override.portfolioBlurb || null,
        selected: selectedIds.has(project.project_id),
        rank: rank >= 0 ? rank + 1 : null,
      }),
    });
  });

  await Promise.allSettled(updates);
}

async function renderPortfolioCustomizationPage() {
  const saveBtn = document.getElementById("portfolio-customization-save-btn");
  if (!saveBtn) return;

  if (!isPrivateMode()) {
    renderPublicModeMessage();
    setStatus("Private Mode is required for portfolio customization.", "warning");
    return;
  }

  saveBtn.disabled = false;
  setStatus("");

  const customization = loadPortfolioCustomization();
  const projects = await fetchProjects();

  renderJobTargetSection(customization);
  renderSectionToggles(customization);
  renderFeaturedProjects(projects, customization);
  renderProjectEditors(projects, customization);

  // trigger job analysis if user selects analyze job match
  const analyzeBtn = document.getElementById("analyze-job-btn");

  if (analyzeBtn) {
    analyzeBtn.onclick = async () => {
      console.log("Analyze button clicked");
      try {

      setStatus("Analyzing job description...", "info");
      analyzeBtn.disabled = true;

      const customization = loadPortfolioCustomization();

      await autoSelectFeaturedProjects(projects, customization);

      renderFeaturedProjects(projects, customization);
      renderProjectEditors(projects, customization);

      await loadPortfolioResume();

    } catch (err) {
      console.error(err);
      setStatus("Job matching failed.", "error");

    } finally {
      analyzeBtn.disabled = false;
    }
  };
}
      

  saveBtn.onclick = async () => {
    try {
      saveBtn.disabled = true;
      setStatus("Saving customization...", "info");

      const nextCustomization = collectCustomization(projects);
      savePortfolioCustomization(nextCustomization);
      await persistProjectOverrides(projects, nextCustomization);

      await loadPortfolioResume();
      document.dispatchEvent(new CustomEvent("portfolio:customization-updated"));

      setStatus("Portfolio customization saved.", "success");
    } catch (error) {
      console.error("Failed to save portfolio customization:", error);
      setStatus("Failed to save portfolio customization.", "error");
    } finally {
      saveBtn.disabled = false;
    }
  };
}

export function initPortfolioCustomization() {
  const tab = document.getElementById("customization-tab");
  tab?.addEventListener("click", renderPortfolioCustomizationPage);

  document.addEventListener("auth:mode-changed", () => {
    renderPortfolioCustomizationPage();
  });

  document.addEventListener("portfolio:customization-updated", () => {
    renderPortfolioCustomizationPage();
  });

  renderPortfolioCustomizationPage();
}

// let users paste job descriptions in customization
function renderJobTargetSection(customization) {
  const container = document.getElementById("portfolio-job-target-container");
  if (!container)
    return;

  const job = customization?.jobTarget ?? {
    title: "",
    company: "",
    description: ""
  };

  container.innerHTML = `
    <div class="customization-form-grid">

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

        <label class="customization-full-row">
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
    const analyzeBtn = container.querySelector("#analyze-job-btn");

    if (analyzeBtn) {
      analyzeBtn.onclick = async () => {
      try {

        setStatus("Analyzing job description...", "info");
        analyzeBtn.disabled = true;

        const projects = await fetchProjects();
        const customization = collectCustomization(projects);

        await autoSelectFeaturedProjects(projects, customization);

        renderFeaturedProjects(projects, customization);
        renderProjectEditors(projects, customization);

        await loadPortfolioResume();

      } catch (err) {
        console.error(err);
        setStatus("Job matching failed.", "error");

      } finally {
        analyzeBtn.disabled = false;
      }
    };
  }
}

// connect backend to ranking endpoint (analyze + rank)
async function analyzeJobMatch() {

  const jd = document.getElementById("job-target-description")?.value;

  if (!jd || !jd.trim()) {
    setStatus("Please paste a job description first.", "warning");
    return [];
  }

  const res = await authFetch("/job-matching/rank", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      job_description: jd,
    }),
  });

  // safety incase returned is not json
  if (!res.ok) {
    throw new Error(`Job matching API failed: ${res.status}`);
  }

  const data = await res.json();

  console.log("Job match API response:", "data");

  if (Array.isArray(data)) return data;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.matches)) return data.matches;

  return [];

}

// pick best projects based on job match ranking
async function autoSelectFeaturedProjects(projects, customization) {

  const matches = await analyzeJobMatch();

  window.__jobMatchResults = matches;

  if (!matches.length) return;

  // select top 3 highest scoring projects for output
  const topProjects = matches
    .slice(0, 3)
    .map((m) => m.project_id);

  customization.featuredProjectIds = topProjects;

  // save updated state
  savePortfolioCustomization(customization);

  // notify related ui of change
  document.dispatchEvent(new CustomEvent("portfolio:customization-updated"));

  setStatus("Featured projects selected based on job match.", "success");
}