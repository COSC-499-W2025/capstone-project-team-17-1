import { fetchProjects } from "./projects.js";
import { authFetch, isPrivateMode } from "./auth.js";
import { loadPortfolio } from "./portfolio.js";
import {
  loadPortfolioCustomization,
  savePortfolioCustomization,
} from "./portfolioState.js";

const API_BASE = "http://127.0.0.1:8002";
const AUTOSAVE_DELAY_MS = 1200;

let previewProjectsCache = [];
let portfolioEditorInitialized = false;
let draggedFeaturedProjectId = null;
let autosaveTimer = null;
let isDirty = false;
let isSaving = false;
let lastSavedSnapshot = "";
let activePortfolioProjectId = null;


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// helper to support different portfolio theme layouts
function buildProjectThemeDetails(project, override = {}) {
  const templateId = String(override.templateId || "classic");
  const images = Array.isArray(override.images) ? override.images : [];
  const coverImage = images.find((img) => img?.is_cover) || images[0] || null;

  const coverMarkup = coverImage?.id
    ? `
      <img
        class="portfolio-theme-cover-image"
        src="${escapeHtml(getPortfolioImageUrl(project.project_id, coverImage.id))}"
        alt="${escapeHtml(project.project_id)} cover image"
      />
    `
    : "";

  if (templateId === "gallery") {
    return `
      <div class="portfolio-theme-layout portfolio-theme-gallery">
        ${coverMarkup}
        <div class="portfolio-theme-gallery-grid">
          ${images
            .slice(0, 6)
            .map(
              (image) => `
                <div class="portfolio-theme-gallery-item">
                  <img
                    src="${escapeHtml(getPortfolioImageUrl(project.project_id, image.id))}"
                    alt="${escapeHtml(image.caption || "Project image")}"
                  />
                  <p>${escapeHtml(image.caption || override.portfolioBlurb || "")}</p>
                </div>
              `
            )
            .join("")}
        </div>
      </div>
    `;
  }

  if (templateId === "case_study") {
    return `
      <div class="portfolio-theme-layout portfolio-theme-case-study">
        ${coverMarkup}
        <div class="portfolio-theme-block">
          <span class="portfolio-theme-label">Overview</span>
          <p>${escapeHtml(override.portfolioBlurb || "")}</p>
        </div>
        <div class="portfolio-theme-block">
          <span class="portfolio-theme-label">My role</span>
          <p>${escapeHtml(override.keyRole || "")}</p>
        </div>
        <div class="portfolio-theme-block">
          <span class="portfolio-theme-label">Evidence of success</span>
          <p>${escapeHtml(override.evidence || "")}</p>
        </div>
        <div class="portfolio-theme-block">
          <span class="portfolio-theme-label">Discussion</span>
          <p>This layout is meant to read more like a formal project writeup or case study.</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="portfolio-theme-layout portfolio-theme-classic">
      ${coverMarkup}
      <div class="portfolio-theme-block">
        <span class="portfolio-theme-label">Summary</span>
        <p>${escapeHtml(override.portfolioBlurb || "")}</p>
      </div>
      <div class="portfolio-theme-block">
        <span class="portfolio-theme-label">Key role</span>
        <p>${escapeHtml(override.keyRole || "")}</p>
      </div>
      <div class="portfolio-theme-block">
        <span class="portfolio-theme-label">Evidence</span>
        <p>${escapeHtml(override.evidence || "")}</p>
      </div>
    </div>
  `;
}

async function fetchProjectPortfolioEntry(projectId) {
  const res = await authFetch(`/portfolio/${encodeURIComponent(projectId)}`);
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch portfolio entry for ${projectId}: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || null;
}

async function saveProjectPortfolioEntry(projectId, body) {
  const res = await authFetch(`/portfolio/${encodeURIComponent(projectId)}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Failed to save portfolio entry for ${projectId}: ${res.status}`);
  }

  const payload = await res.json();
  return payload?.data || null;
}

async function saveProjectFeaturedState(projectId, { selected, rank }) {
  const res = await authFetch(`/projects/${encodeURIComponent(projectId)}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      selected: !!selected,
      rank: rank >= 0 ? rank + 1 : null,
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to save featured state for ${projectId}: ${res.status}`);
  }

  return true;
}

async function uploadPortfolioImage(projectId, file, caption = "", isCover = false) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("caption", caption);
  formData.append("is_cover", String(isCover));

  const res = await authFetch(`/portfolio/${encodeURIComponent(projectId)}/images`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Failed to upload portfolio image for ${projectId}: ${res.status}`);
  }

  const payload = await res.json();
  return payload?.data || null;
}

async function deletePortfolioImage(projectId, imageId) {
  const res = await authFetch(
    `/portfolio/${encodeURIComponent(projectId)}/images/${encodeURIComponent(imageId)}`,
    { method: "DELETE" }
  );

  if (!res.ok) {
    throw new Error(`Failed to delete image ${imageId}: ${res.status}`);
  }

  return true;
}

async function setPortfolioCoverImage(projectId, imageId) {
  const res = await authFetch(
    `/portfolio/${encodeURIComponent(projectId)}/images/${encodeURIComponent(imageId)}/cover`,
    { method: "POST" }
  );

  if (!res.ok) {
    throw new Error(`Failed to set cover image ${imageId}: ${res.status}`);
  }

  return true;
}

function getPortfolioImageUrl(projectId, imageId) {
  return `${API_BASE}/portfolio/${encodeURIComponent(projectId)}/images/${encodeURIComponent(imageId)}/file`;
}

async function hydrateCustomizationFromBackend(projects) {
  const current = loadPortfolioCustomization();

  if (!Array.isArray(projects) || !projects.length) {
    return current;
  }

  const portfolioResults = await Promise.allSettled(
    projects.map((project) => fetchProjectPortfolioEntry(project.project_id))
  );

  const backendOverrides = {};

  portfolioResults.forEach((result, index) => {
    const projectId = String(projects[index]?.project_id || "");
    if (!projectId) return;

    if (result.status !== "fulfilled") {
      console.error(`Portfolio fetch failed for ${projectId}:`, result.reason);
      return;
    }

    if (!result.value) {
      console.warn(`No portfolio payload returned for ${projectId}`);
      return;
    }

    const data = result.value;
    const resolved = data.resolved || {};
    const defaults = data.analysis_defaults || {};

    console.log(`Portfolio payload for ${projectId}:`, data);
    console.log(`Resolved role for ${projectId}:`, resolved.key_role);

    backendOverrides[projectId] = {
      keyRole: String(resolved.key_role || defaults.key_role || ""),
      evidence: String(resolved.evidence_of_success || defaults.evidence_of_success || ""),
      portfolioBlurb: String(
        resolved.portfolio_blurb || defaults.portfolio_blurb || data.summary || ""
      ),
      templateId: String(data.template_id || "classic"),
      images: Array.isArray(data.images) ? data.images : [],
      analysisDefaults: {
        keyRole: String(defaults.key_role || ""),
        evidence: String(defaults.evidence_of_success || ""),
        portfolioBlurb: String(defaults.portfolio_blurb || "")
      }
    };
  });

  const nextCustomization = {
    ...current,
    projectOverrides: {
      ...(current?.projectOverrides || {}),
      ...backendOverrides
    },
  };

  savePortfolioCustomization(nextCustomization);
  return nextCustomization;
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

function getPreviewContainer() {
  return document.getElementById("portfolio-live-preview-container");
}

function getFeaturedOrderContainer() {
  return document.getElementById("portfolio-featured-order-container");
}

function getSaveButton() {
  return document.getElementById("portfolio-customization-save-btn");
}

function clearAutosaveTimer() {
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }
}

function normalizeCustomization(customization) {
  const sectionVisibility = customization?.sectionVisibility || {};

  const featuredProjectIds = Array.isArray(customization?.featuredProjectIds)
    ? customization.featuredProjectIds.map((id) => String(id))
    : [];

  const projectOverrides = {};
  const rawOverrides =
    customization?.projectOverrides && typeof customization.projectOverrides === "object"
      ? customization.projectOverrides
      : {};

  Object.keys(rawOverrides)
    .sort()
    .forEach((projectId) => {
      const override = rawOverrides[projectId] || {};

      projectOverrides[String(projectId)] = {
        keyRole: String(override.keyRole || ""),
        evidence: String(override.evidence || ""),
        portfolioBlurb: String(override.portfolioBlurb || ""),
        templateId: String(override.templateId || "classic"),
        images: Array.isArray(override.images) ? override.images : [],
        analysisDefaults: {
          keyRole: String(override.analysisDefaults?.keyRole || ""),
          evidence: String(override.analysisDefaults?.evidence || ""),
          portfolioBlurb: String(override.analysisDefaults?.portfolioBlurb || "")
        }
      };
    });

    const jobTarget =
      customization?.jobTarget && typeof customization.jobTarget === "object"
        ? {
          title: String(customization.jobTarget.title || ""),
          company: String(customization.jobTarget.company || ""),
          description: String(customization.jobTarget.description || "")
        }
      : { title: "", company: "", description: ""};

  return {
    sectionVisibility,
    featuredProjectIds,
    projectOverrides,
    jobTarget
  };
}

function snapshotCustomization(customization) {
  return JSON.stringify(normalizeCustomization(customization));
}

function updateSaveButtonState() {
  const saveBtn = getSaveButton();
  const projectSaveButtons = document.querySelectorAll("[data-project-save]");

  if (!saveBtn && !projectSaveButtons.length) return;

  if (!isPrivateMode()) {
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = "Save Customization";
    }
    projectSaveButtons.forEach((button) => {
      button.disabled = true;
      button.textContent = "Save Project Details";
    });
    return;
  }

  if (isSaving) {
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";
    }
    projectSaveButtons.forEach((button) => {
      button.disabled = true;
    });
    return;
  }

  if (saveBtn) {
    saveBtn.disabled = !isDirty;
    saveBtn.textContent = isDirty ? "Save Customization" : "Saved";
  }
  projectSaveButtons.forEach((button) => {
    button.disabled = false;
  });
}

function markDirtyState(nextCustomization) {
  const snapshot = snapshotCustomization(nextCustomization);
  isDirty = snapshot !== lastSavedSnapshot;

  if (!isSaving) {
    if (isDirty) {
      setStatus("Unsaved changes", "warning");
    } else {
      setStatus("Saved", "success");
    }
  }

  updateSaveButtonState();
}

function renderPublicModeMessage() {
  const featuredContainer = document.getElementById("portfolio-featured-projects-container");
  const orderContainer = getFeaturedOrderContainer();
  const editorContainer = document.getElementById("portfolio-project-editor-container");
  const saveBtn = document.getElementById("portfolio-customization-save-btn");
  const jobContainer = document.getElementById("portfolio-job-target-container");

  if (featuredContainer) {
    featuredContainer.innerHTML =
      `<p class="muted-text">Featured project selection is only available in Private Mode.</p>`;
  }
  if (orderContainer) {
    orderContainer.innerHTML =
      `<p class="muted-text">Reordering is only available in Private Mode.</p>`;
  }
  if (editorContainer) {
    editorContainer.innerHTML =
      `<p class="muted-text">Project portfolio edits are only available in Private Mode.</p>`;
  }
  const previewContainer = getPreviewContainer();
  if (previewContainer) {
    previewContainer.innerHTML =
      `<p class="muted-text">Live preview is only available in Private Mode.</p>`;
  }
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Save Customization";
  }
  if (jobContainer) {
    jobContainer.innerHTML = `<p class="muted-text">Switch to Private Mode to analyze job descriptions.</p>`;
  }
}


function renderFeaturedProjects(projects, customization) {
  const container = document.getElementById("portfolio-featured-projects-container");
  if (!container) return;

  const selected = new Set((customization.featuredProjectIds || []).map(String));
  const featuredOrder = customization.featuredProjectIds || [];

  if (!projects.length) {
    container.innerHTML =
      `<p class="muted-text">Upload projects first to choose featured items.</p>`;
    return;
  }

  const matchScores = window.__jobMatchResults || [];
  const scoreMap = new Map(matchScores.map(m => [m.project_id, m.score]));
  // Keep starred projects visible at the top 
  const orderedProjects = [...projects].sort((a, b) => {
    const aIndex = featuredOrder.indexOf(String(a.project_id));
    const bIndex = featuredOrder.indexOf(String(b.project_id));
    const aFeatured = aIndex >= 0;
    const bFeatured = bIndex >= 0;

    if (aFeatured && bFeatured) return aIndex - bIndex;
    if (aFeatured) return -1;
    if (bFeatured) return 1;
    return String(a.project_id).localeCompare(String(b.project_id));
  });

  container.innerHTML = orderedProjects
    .map(
      (project) => `
        <label class="customization-project-pick">
          <input
            type="checkbox"
            data-featured-project-id="${escapeHtml(project.project_id)}"
            ${selected.has(String(project.project_id)) ? "checked" : ""}
          />
          <div>
            <div class="customization-project-title">${escapeHtml(project.project_id)}</div>
            <div class="customization-project-meta">
              ${project.total_files || 0} files • ${project.total_skills || 0} skills
              ${scoreMap.has(project.project_id)
                ? ` • <span class="customization-job-match-score">${Math.round(scoreMap.get(project.project_id) * 100)}% match</span>`
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
  const featuredIds = (customization.featuredProjectIds || []).map(String);
  if (!container) return;

  if (!projects.length) {
    container.innerHTML =
      `<p class="muted-text">No projects available for customization yet.</p>`;
    return;
  }

  // Mirror the starred ordering in the editor list 
  const featuredOrder = customization.featuredProjectIds || [];
  const orderedProjects = [...projects].sort((a, b) => {
    const aIndex = featuredOrder.indexOf(String(a.project_id));
    const bIndex = featuredOrder.indexOf(String(b.project_id));
    const aFeatured = aIndex >= 0;
    const bFeatured = bIndex >= 0;

    if (aFeatured && bFeatured) return aIndex - bIndex;
    if (aFeatured) return -1;
    if (bFeatured) return 1;
    return String(a.project_id).localeCompare(String(b.project_id));
  });

  container.innerHTML = orderedProjects
    .map((project) => {
      const override = customization.projectOverrides?.[project.project_id] || {};
      const isFeatured = featuredIds.includes(String(project.project_id));
      const isActive = activePortfolioProjectId === project.project_id;
      const selectedTemplate = String(override.templateId || "classic");

      const initialSnapshot = JSON.stringify({
        keyRole: override.keyRole || "",
        evidence: override.evidence || "",
        portfolioBlurb: override.portfolioBlurb || "",
        templateId: selectedTemplate,
        isFeatured,
      });

      return `
        <div 
          class="customization-project-editor ${isActive ? "active" : "collapsed"}" 
          data-project-editor-id="${escapeHtml(project.project_id)}" 
          data-saved-snapshot="${escapeHtml(initialSnapshot)}"
        >
          <div 
            class="customization-project-editor-header" 
            data-open-project-card="${escapeHtml(project.project_id)}">
            <div>
              <h3>${escapeHtml(project.project_id)}</h3>
              <p class="muted-text">
                ${project.total_files || 0} files analyzed • ${project.total_skills || 0} skill signals
              </p>
            </div>
            <div class="portfolio-card-header-actions">
              <span class="portfolio-template-pill">${escapeHtml(selectedTemplate.replaceAll("_", " "))}</span>
              <input
                type="checkbox"
                data-project-selected="${escapeHtml(project.project_id)}"
                ${isFeatured ? "checked" : ""}
                style="display:none"
              />
              <button
                type="button"
                class="portfolio-star-btn${isFeatured ? " starred" : ""}"
                data-project-star="${escapeHtml(project.project_id)}"
                title="Mark as featured"
              >★</button>
            </div>
          </div>
          ${
            !isActive
              ? `
                <div class="portfolio-card-collapsed-preview">
                  <p>${escapeHtml(override.portfolioBlurb || "Click to open project portfolio details.")}</p>
                </div>
              `
              : `
              <div class="portfolio-card-expanded-content">
                <div class="portfolio-template-picker">
                  <button
                    type="button"
                    class="portfolio-template-card${selectedTemplate === "classic" ? " active" : ""}"
                    data-template-choice="classic"
                    data-project-template="${escapeHtml(project.project_id)}"
                  >
                    <div class="portfolio-template-title">Classic</div>
                    <div class="portfolio-template-copy">Simple hero image and clean project summary.</div>
                  </button>
                  
                  <button
                    type="button"
                    class="portfolio-template-card${selectedTemplate === "case_study" ? " active" : ""}"
                    data-template-choice="case_study"
                    data-project-template="${escapeHtml(project.project_id)}"
                  >
                    <div class="portfolio-template-title">Case Study</div>
                    <div class="portfolio-template-copy">Problem, role, build work, and result layout.</div>
                  </button>
                  
                  <button
                    type="button"
                    class="portfolio-template-card${selectedTemplate === "gallery" ? " active" : ""}"
                    data-template-choice="gallery"
                    data-project-template="${escapeHtml(project.project_id)}"
                  >
                    <div class="portfolio-template-title">Gallery</div>
                    <div class="portfolio-template-copy">More visual layout focused on screenshots.</div>
                  </button>
                </div>

                <input
                  type="hidden"
                  data-field="templateId"
                  value="${escapeHtml(selectedTemplate)}"
                />

                <div class="form-grid">
                  <label>
                    <span>Key role</span>
                    <input
                      type="text"
                      data-field="keyRole"
                      value="${escapeHtml(override.keyRole || "")}"
                      placeholder="Example: Frontend integration lead"
                    />
                  </label>

                  <label class="form-full-row">
                    <span>Evidence of success</span>
                    <textarea
                      data-field="evidence"
                      rows="3"
                      placeholder="Example: Built the portfolio UI, integrated the summary endpoints, and improved milestone demo readiness."
                    >${escapeHtml(override.evidence || "")}</textarea>
                  </label>

                  <label class="form-full-row">
                    <span>Portfolio Summary</span>
                    <textarea
                      data-field="portfolioBlurb"
                      rows="3"
                      placeholder="Short description that should appear in the portfolio showcase."
                    >${escapeHtml(override.portfolioBlurb || "")}</textarea>
                  </label>
                </div>

                <div class="portfolio-upload-block">
                  <label class="portfolio-upload-dropzone">
                    <span class="portfolio-upload-trigger">Upload images</span>
                    <div class="portfolio-upload-help">PNG, JPG, WEBP, or GIF screenshots for this project.</div>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      data-project-image-upload="${escapeHtml(project.project_id)}"
                    />
                  </label>

                  <div class="portfolio-image-grid">
                    ${(Array.isArray(override.images) ? override.images : []).map((image) => `
                      <div class="portfolio-image-card" data-portfolio-image-id="${escapeHtml(image.id)}">
                        <div class="portfolio-image-preview-wrap">
                          <img
                            class="portfolio-image-preview"
                            src="${escapeHtml(getPortfolioImageUrl(project.project_id, image.id))}"
                            alt="${escapeHtml(image.caption || "Portfolio image")}"
                          />
                          ${image.is_cover ? `<span class="portfolio-image-cover-badge">Cover</span>` : ""}
                        </div>
                        <div class="portfolio-image-meta">
                          <div class="portfolio-image-caption">${escapeHtml(image.caption || "Project image")}</div>
                          <div class="portfolio-image-actions">
                            <button
                              type="button"
                              class="portfolio-image-btn"
                              data-set-cover-image="${escapeHtml(image.id)}"
                              data-project-id="${escapeHtml(project.project_id)}"
                            >
                              ${image.is_cover ? "Cover Image" : "Set Cover"}
                            </button>
                            <button
                              type="button"
                              class="portfolio-image-btn danger"
                              data-delete-image="${escapeHtml(image.id)}"
                              data-project-id="${escapeHtml(project.project_id)}"
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      </div>
                    `).join("")}
                  </div>
                </div>

                <div class="portfolio-card-theme-preview">
                  ${buildProjectThemeDetails(project, override)}
                </div>

                <div class="customization-project-editor-actions">
                  <span class="customization-project-save-status"></span>

                  <button
                      type="button"
                      class="secondary-btn portfolio-reset-btn"
                      data-reset-analysis-defaults="${escapeHtml(project.project_id)}"
                  >
                      Reset to default analysis
                  </button>

                  <button
                    type="button"
                    class="secondary-btn customization-project-save-btn"
                    data-project-save="${escapeHtml(project.project_id)}"
                  >
                    Save
                  </button>
                </div>
              </div>
            `
        }
      </div>
    `;
  })
  .join("");

  container.querySelectorAll("[data-project-star]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();

      const projectId = String(button.dataset.projectStar || "");
      if (!projectId) return;

      const current = loadPortfolioCustomization();
      const featured = [...((current.featuredProjectIds || []).map(String))];

      const existingIndex = featured.indexOf(projectId);
      if (existingIndex >= 0) {
        featured.splice(existingIndex, 1);
      } else {
        featured.unshift(projectId);
      }

      const nextFeatured = featured.slice(0, 3);

      const nextCustomization = {
        ...current,
        featuredProjectIds: nextFeatured,
      };

      savePortfolioCustomization(nextCustomization);

      renderFeaturedProjects(previewProjectsCache, nextCustomization);
      renderProjectEditors(previewProjectsCache, nextCustomization);
      renderFeaturedOrderList(previewProjectsCache, nextCustomization);
      updateLivePreview();
      scheduleAutosave();

      try {
        await Promise.all(
          previewProjectsCache.map((project) => {
            const pid = String(project.project_id);
            const rank = nextFeatured.indexOf(pid);

            return saveProjectFeaturedState(pid, {
              selected: rank >= 0,
              rank,
            });
          })
        );
      } catch (error) {
        console.error("Failed to persist featured project order:", error);
        setStatus("Failed to save featured project order.", "error");
      }
    });
  });

  container.querySelectorAll("[data-reset-analysis-defaults]").forEach((button) => {
    button.addEventListener("click", () => {
      const projectId = button.dataset.resetAnalysisDefaults;
      const customization = loadPortfolioCustomization();
      const currentOverride = customization.projectOverrides?.[projectId] || {};
      const defaults = currentOverride.analysisDefaults || {};

      customization.projectOverrides = {
        ...(customization.projectOverrides || {}),
        [projectId]: {
          ...currentOverride,
          keyRole: defaults.keyRole || "",
          evidence: defaults.evidence || "",
          portfolioBlurb: defaults.portfolioBlurb || "",
        },
      };

      savePortfolioCustomization(customization);
      renderProjectEditors(previewProjectsCache, customization);
      updateLivePreview();
      scheduleAutosave();
      setStatus("Reset to analysis defaults.", "info");
    });
  });

  container.querySelectorAll("[data-open-project-card]").forEach((header) => {
  header.addEventListener("click", (event) => {
    if (event.target.closest("[data-project-star]")) {
      return;
    }

    const projectId = header.dataset.openProjectCard;
    activePortfolioProjectId =
      activePortfolioProjectId === projectId ? null : projectId;

    const customization = loadPortfolioCustomization();
    renderProjectEditors(previewProjectsCache, customization);
  });
});

    const checkboxes = container.querySelectorAll("[data-project-selected]");
    const saveButtons = container.querySelectorAll("[data-project-save]");

    checkboxes.forEach((cb) => {
      cb.addEventListener("change", () => {
        const checked = container.querySelectorAll("[data-project-selected]:checked");
        if (checked.length > 3) {
          cb.checked = false;
          setStatus("You can only feature up to 3 projects.", "warning");
        } else {
          setStatus("");
        }
      });
    });

    saveButtons.forEach((button) => {
      const projectId = button.dataset.projectSave;
      button.addEventListener("click", async () => {
        const statusSpan = button.parentElement?.querySelector(".customization-project-save-status");
        const showLocal = (msg, kind) => {
          if (!statusSpan) return;
          statusSpan.textContent = msg;
          statusSpan.dataset.kind = kind;
        };

        showLocal("Saving...", "info");
        try {
          const result = await saveProjectById(projectId);
          if (result === "no-changes") {
            showLocal("No changes to save", "info");
          } else {
            showLocal("Saved", "success");
          }
          setTimeout(() => showLocal("", ""), 2500);
        } catch (_) {
          showLocal("Failed to save", "error");
        }
      });
    });

    const templateButtons = container.querySelectorAll("[data-project-template]");
    templateButtons.forEach((button) => {
      button.addEventListener("click", () => {
      const projectId = button.dataset.projectTemplate;
      const templateId = button.dataset.templateChoice;
      const editor = container.querySelector(
        `[data-project-editor-id="${CSS.escape(projectId)}"]`
      );
      const hiddenInput = editor?.querySelector('[data-field="templateId"]');
      if (!hiddenInput) return;

      hiddenInput.value = templateId;

      const customization = loadPortfolioCustomization();
      const currentOverride = customization.projectOverrides?.[projectId] || {};

      customization.projectOverrides = {
        ...(customization.projectOverrides || {}),
        [projectId]: {
          ...currentOverride,
          templateId
        }
      };

      savePortfolioCustomization(customization);
      renderProjectEditors(previewProjectsCache, customization);
      updateLivePreview();
      scheduleAutosave();
    });
  });

  const imageUploadInputs = container.querySelectorAll("[data-project-image-upload]");
  imageUploadInputs.forEach((input) => {
    input.addEventListener("change", async (event) => {
      const projectId = input.dataset.projectImageUpload;
      const files = Array.from(event.target.files || []);
      if (!files.length) return;

      try {
        setStatus("Uploading images...", "info");

        for (const file of files) {
          await uploadPortfolioImage(projectId, file);
        }

        const latest = await fetchProjectPortfolioEntry(projectId);
        const customization = loadPortfolioCustomization();
        const current = customization.projectOverrides?.[projectId] || {};

        customization.projectOverrides = {
          ...(customization.projectOverrides || {}),
          [projectId]: {
            ...current,
            keyRole: String(latest?.resolved?.key_role || current.keyRole || ""),
            evidence: String(latest?.resolved?.evidence_of_success || current.evidence || ""),
            portfolioBlurb: String(latest?.resolved?.portfolio_blurb || latest?.summary || current.portfolioBlurb || ""),
            templateId: String(latest?.template_id || current.templateId || "classic"),
            images: Array.isArray(latest?.images) ? latest.images : [],
            analysisDefaults: {
              keyRole: String(latest?.analysis_defaults?.key_role || current.analysisDefaults?.keyRole || ""),
              evidence: String(latest?.analysis_defaults?.evidence_of_success || current.analysisDefaults?.evidence || ""),
              portfolioBlurb: String(latest?.analysis_defaults?.portfolio_blurb || current.analysisDefaults?.portfolioBlurb || "")
            }
          },
        };

        savePortfolioCustomization(customization);
        lastSavedSnapshot = snapshotCustomization(customization);
        isDirty = false;
        updateSaveButtonState();
        renderProjectEditors(previewProjectsCache, customization);
        updateLivePreview();
        setStatus("Images uploaded.", "success");
      } catch (error) {
        console.error(error);
        setStatus("Failed to upload images.", "error");
      } finally {
        input.value = "";
      }
    });
  });

  container.querySelectorAll("[data-set-cover-image]").forEach((button) => {
    button.addEventListener("click", async () => {
      const projectId = button.dataset.projectId;
      const imageId = button.dataset.setCoverImage;

      try {
        await setPortfolioCoverImage(projectId, imageId);
        const latest = await fetchProjectPortfolioEntry(projectId);
        const customization = loadPortfolioCustomization();
        const current = customization.projectOverrides?.[projectId] || {};

        customization.projectOverrides = {
          ...(customization.projectOverrides || {}),
          [projectId]: {
            ...current,
            keyRole: String(latest?.resolved?.key_role || current.keyRole || ""),
            evidence: String(latest?.resolved?.evidence_of_success || current.evidence || ""),
            portfolioBlurb: String(latest?.resolved?.portfolio_blurb || latest?.summary || current.portfolioBlurb || ""),
            templateId: String(latest?.template_id || current.templateId || "classic"),
            images: Array.isArray(latest?.images) ? latest.images : [],
            analysisDefaults: {
              keyRole: String(latest?.analysis_defaults?.key_role || current.analysisDefaults?.keyRole || ""),
              evidence: String(latest?.analysis_defaults?.evidence_of_success || current.analysisDefaults?.evidence || ""),
              portfolioBlurb: String(latest?.analysis_defaults?.portfolio_blurb || current.analysisDefaults?.portfolioBlurb || "")
            }
          },
        };

        savePortfolioCustomization(customization);
        lastSavedSnapshot = snapshotCustomization(customization);
        isDirty = false;
        updateSaveButtonState();
        renderProjectEditors(previewProjectsCache, customization);
        updateLivePreview();
        setStatus("Cover image updated.", "success");
      } catch (error) {
        console.error(error);
        setStatus("Failed to update cover image.", "error");
      }
    });
  });

  container.querySelectorAll("[data-delete-image]").forEach((button) => {
    button.addEventListener("click", async () => {
      const projectId = button.dataset.projectId;
      const imageId = button.dataset.deleteImage;

      try {
        await deletePortfolioImage(projectId, imageId);
        const latest = await fetchProjectPortfolioEntry(projectId);
        const customization = loadPortfolioCustomization();
        const current = customization.projectOverrides?.[projectId] || {};

        customization.projectOverrides = {
          ...(customization.projectOverrides || {}),
          [projectId]: {
            ...current,
            keyRole: String(latest?.resolved?.key_role || current.keyRole || ""),
            evidence: String(latest?.resolved?.evidence_of_success || current.evidence || ""),
            portfolioBlurb: String(latest?.resolved?.portfolio_blurb || latest?.summary || current.portfolioBlurb || ""),
            templateId: String(latest?.template_id || current.templateId || "classic"),
            images: Array.isArray(latest?.images) ? latest.images : [],
            analysisDefaults: {
              keyRole: String(latest?.analysis_defaults?.key_role || current.analysisDefaults?.keyRole || ""),
              evidence: String(latest?.analysis_defaults?.evidence_of_success || current.analysisDefaults?.evidence || ""),
              portfolioBlurb: String(latest?.analysis_defaults?.portfolio_blurb || current.analysisDefaults?.portfolioBlurb || "")
            }
          },
        };

        savePortfolioCustomization(customization);
        lastSavedSnapshot = snapshotCustomization(customization);
        isDirty = false;
        updateSaveButtonState();
        renderProjectEditors(previewProjectsCache, customization);
        updateLivePreview();
        setStatus("Image removed.", "success");
      } catch (error) {
        console.error(error);
        setStatus("Failed to remove image.", "error");
      }
    });
  });
}

function getSelectedProjectIdsFromInputs(projects) {
  return projects
    .filter((project) => {
      const editorCheckbox = document.querySelector(
        `[data-project-selected="${CSS.escape(project.project_id)}"]`
      );
      const pickerCheckbox = document.querySelector(
        `[data-featured-project-id="${CSS.escape(project.project_id)}"]`
      );
      return !!(editorCheckbox?.checked || pickerCheckbox?.checked);
    })
    .map((project) => project.project_id)
    .slice(0, 3);
}

function getFeaturedOrderFromDom() {
  const items = [...document.querySelectorAll("[data-featured-order-item]")];
  return items.map((item) => String(item.dataset.featuredOrderItem)).slice(0, 3);
}

function renderFeaturedOrderList(projects, customization) {
  const container = getFeaturedOrderContainer();
  if (!container) return;

  const selectedIds = getSelectedProjectIdsFromInputs(projects);
  const orderedIdsFromState = (customization.featuredProjectIds || []).filter((id) =>
    selectedIds.includes(id)
  );

  const mergedOrder = [
    ...orderedIdsFromState,
    ...selectedIds.filter((id) => !orderedIdsFromState.includes(id)),
  ].slice(0, 3);

  if (!mergedOrder.length) {
    container.innerHTML = `
      <p class="customization-featured-order-empty">
        Select up to 3 featured projects to enable drag-and-drop ordering.
      </p>
    `;
    return;
  }

  const projectMap = new Map(projects.map((project) => [project.project_id, project]));

  container.innerHTML = mergedOrder
    .map((projectId, index) => {
      const project = projectMap.get(projectId);
      if (!project) return "";

      return `
        <div
          class="customization-featured-order-item"
          data-featured-order-item="${escapeHtml(project.project_id)}"
          draggable="true"
        >
          <div class="customization-featured-order-rank">${index + 1}</div>
          <div class="customization-featured-order-content">
            <div class="customization-featured-order-title">${escapeHtml(project.project_id)}</div>
            <div class="customization-featured-order-meta">
              ${project.total_files || 0} files • ${project.total_skills || 0} skills
            </div>
          </div>
          <div class="customization-featured-order-handle">⋮⋮</div>
        </div>
      `;
    })
    .join("");
}

function collectCustomization(projects) {
  const current = loadPortfolioCustomization();

  const sectionVisibility = current?.sectionVisibility || {};

  const selectedIds = projects
    .filter((project) => {
      const checked = document.querySelector(
        `[data-project-selected="${CSS.escape(project.project_id)}"]`
      );
      return !!checked?.checked;
    })
    .map((project) => project.project_id);

  if (selectedIds.length > 3) {
    setStatus("You can only select up to 3 featured projects. The top 3 were used.", "warning");
  }

  const orderedIds = getFeaturedOrderFromDom().filter((id) => selectedIds.includes(id));
  const featuredProjectIds = [
    ...orderedIds,
    ...selectedIds.filter((id) => !orderedIds.includes(id)),
  ].slice(0, 3);

  const projectOverrides = {};

  projects.forEach((project) => {
    const editor = document.querySelector(
      `[data-project-editor-id="${CSS.escape(project.project_id)}"]`
    );

    const existingOverride = current?.projectOverrides?.[project.project_id] || {};

    const keyRole =
      editor?.querySelector('[data-field="keyRole"]')?.value?.trim() ??
      existingOverride.keyRole ??
      "";

    const evidence =
      editor?.querySelector('[data-field="evidence"]')?.value?.trim() ??
      existingOverride.evidence ??
      "";

    const portfolioBlurb =
      editor?.querySelector('[data-field="portfolioBlurb"]')?.value?.trim() ??
      existingOverride.portfolioBlurb ??
      "";

    const templateId =
      editor?.querySelector('[data-field="templateId"]')?.value?.trim() ??
      existingOverride.templateId ??
      "classic";

    projectOverrides[project.project_id] = {
      keyRole,
      evidence,
      portfolioBlurb,
      templateId,
      images: Array.isArray(existingOverride.images) ? existingOverride.images : [],
      analysisDefaults: {
        keyRole: String(existingOverride.analysisDefaults?.keyRole || ""),
        evidence: String(existingOverride.analysisDefaults?.evidence || ""),
        portfolioBlurb: String(existingOverride.analysisDefaults?.portfolioBlurb || "")
      }
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
    featuredProjectIds,
    projectOverrides,
    jobTarget,
  };
}

function collectDraftCustomization() {
  return collectCustomization(previewProjectsCache);
}

async function persistProjectOverrides(projects, customization) {
  const selectedIds = new Set(customization.featuredProjectIds || []);

  const updates = projects.map(async (project) => {
    const override = customization.projectOverrides?.[project.project_id] || {};
    const rank = (customization.featuredProjectIds || []).indexOf(project.project_id);

    await saveProjectPortfolioEntry(project.project_id, {
      template_id: override.templateId || "classic",
      key_role: override.keyRole || null,
      evidence_of_success: override.evidence || null,
      portfolio_blurb: override.portfolioBlurb || null
    });

    await saveProjectFeaturedState(project.project_id, {
      selected: selectedIds.has(project.project_id),
      rank,
    });
  });

  await Promise.allSettled(updates);
}

async function saveProjectById(projectId) {
  if (!isPrivateMode()) return "no-changes";

  const editor = document.querySelector(`[data-project-editor-id="${CSS.escape(projectId)}"]`);
  if (!editor) return "no-changes";

  const keyRole = editor.querySelector('[data-field="keyRole"]')?.value?.trim() || "";
  const evidence = editor.querySelector('[data-field="evidence"]')?.value?.trim() || "";
  const portfolioBlurb = editor.querySelector('[data-field="portfolioBlurb"]')?.value?.trim() || "";
  const templateId = editor.querySelector('[data-field="templateId"]')?.value?.trim() || "classic";
  const isFeatured = !!editor.querySelector(`[data-project-selected="${CSS.escape(projectId)}"]`)?.checked;

  const snapshot = JSON.stringify({ keyRole, evidence, portfolioBlurb, templateId, isFeatured });
  if (editor.dataset.savedSnapshot === snapshot) return "no-changes";

  const current = loadPortfolioCustomization();
  const featuredIds = current?.featuredProjectIds || [];
  const rank = featuredIds.indexOf(projectId);

  await saveProjectPortfolioEntry(projectId, {
    template_id: templateId,
    key_role: keyRole || null,
    evidence_of_success: evidence || null,
    portfolio_blurb: portfolioBlurb || null
  });

  await saveProjectFeaturedState(projectId, {
    selected: isFeatured,
    rank
  });

  const existing = current?.projectOverrides?.[projectId] || {};
  const overrides = {
    ...(current?.projectOverrides || {}),
    [projectId]: {
      ...existing,
      keyRole,
      evidence,
      portfolioBlurb,
      templateId
    },
  };

  const nextCustomization = { ...current, projectOverrides: overrides };
  savePortfolioCustomization(nextCustomization);
  lastSavedSnapshot = snapshotCustomization(nextCustomization);
  isDirty = false;
  updateSaveButtonState();

  editor.dataset.savedSnapshot = snapshot;

  await loadPortfolio();
}

function renderLivePreview(projects, draftCustomization) {
  const container = getPreviewContainer();
  if (!container) return;

  const sectionVisibility = {
    "top-projects": true,
    ...(draftCustomization.sectionVisibility || {}),
  };

  const projectMap = new Map(
    projects.map((project) => [String(project.project_id), project])
  );

  const featuredProjects = (draftCustomization.featuredProjectIds || [])
    .map((id) => projectMap.get(String(id)))
    .filter(Boolean)
    .slice(0, 3);

  const draftProjects = projects
    .map((project) => {
      const override = draftCustomization.projectOverrides?.[project.project_id] || {};
      const hasDraftContent = Boolean(
        String(override.portfolioBlurb || "").trim() ||
        String(override.keyRole || "").trim() ||
        String(override.evidence || "").trim() ||
        String(override.templateId || "").trim() ||
        (Array.isArray(override.images) && override.images.length)
      );

      return {
        project,
        override,
        isFeatured: (draftCustomization.featuredProjectIds || []).includes(project.project_id),
        hasDraftContent,
      };
    })
    .filter((item) => item.hasDraftContent)
    .sort((a, b) => {
      if (a.isFeatured && !b.isFeatured) return -1;
      if (!a.isFeatured && b.isFeatured) return 1;
      return String(a.project.project_id).localeCompare(String(b.project.project_id));
    });

  const renderPreviewCard = ({ project, override, isFeatured = false, showMeta = false }) => {
  const templateId = String(override.templateId || "classic");
  const templateLabel = templateId.replaceAll("_", " ");
  const images = Array.isArray(override.images) ? override.images : [];
  const coverImage = images.find((img) => img?.is_cover) || images[0] || null;

  const coverImageMarkup = coverImage?.id
    ? `
      <img
        class="live-preview-hero-image"
        src="${escapeHtml(getPortfolioImageUrl(project.project_id, coverImage.id))}"
        alt="${escapeHtml(project.project_id)} cover image"
      />
    `
    : "";

  const badges = `
    <div class="live-preview-badge-row">
      ${isFeatured ? `<span class="live-preview-badge">Starred</span>` : ""}
      <span class="live-preview-badge">${escapeHtml(templateLabel)}</span>
    </div>
  `;

  const metaMarkup = showMeta
    ? `
      <div class="live-preview-meta">
        ${project.total_files || 0} files • ${project.total_skills || 0} skills
      </div>
    `
    : "";

  const galleryMarkup =
    templateId === "gallery" && images.length > 1
      ? `
        <div class="live-preview-gallery-grid">
          ${images
            .slice(0, 6)
            .map(
              (image) => `
                <img
                  src="${escapeHtml(getPortfolioImageUrl(project.project_id, image.id))}"
                  alt="${escapeHtml(image.caption || "Project image")}"
                />
              `
            )
            .join("")}
        </div>
      `
      : "";

  return `
    <div class="live-preview-project-card live-preview-template-${escapeHtml(templateId)}">
      <h4>${escapeHtml(project.project_id)}</h4>
      ${badges}
      ${metaMarkup}
      ${coverImageMarkup}
      ${
        override.portfolioBlurb
          ? `<p>${escapeHtml(override.portfolioBlurb)}</p>`
          : `<p class="live-preview-empty">No portfolio blurb yet.</p>`
      }
      ${
        override.keyRole
          ? `<p><strong>Key role:</strong> ${escapeHtml(override.keyRole)}</p>`
          : ""
      }
      ${
        override.evidence
          ? `<p><strong>Evidence:</strong> ${escapeHtml(override.evidence)}</p>`
          : ""
      }
      ${galleryMarkup}
    </div>
  `;
};

  // Keep drafts separate from starred showcase 
  container.innerHTML = `
    <div id="live-preview-drafts-section" class="live-preview-section">
      <h3>Project Detail Drafts</h3>
      ${
        draftProjects.length
          ? draftProjects
              .map(({ project, override, isFeatured }) => 
                renderPreviewCard({
                  project,
                  override,
                  isFeatured,
                  showMeta: false
                })
              )
              .join("")
            : `<p class="live-preview-empty">Edit a project in Project Portfolio Details to preview its draft here.</p>`
          }
        </div>

        <div
          id="live-preview-starred-section"
          class="live-preview-section ${sectionVisibility["top-projects"] ? "" : "hidden"}"
        >
          <h3>My Starred Projects</h3>
          ${
            featuredProjects.length
              ? featuredProjects
                  .map((project) => {
                    const override =
                      draftCustomization.projectOverrides?.[project.project_id] || {};

                    return renderPreviewCard({
                      project,
                      override,
                      isFeatured: true,
                      showMeta: true,
                    });
                  })
                  .join("")
              : `<p class="live-preview-empty">No featured projects selected.</p>`
          }
        </div>
      `;
}

function updateLivePreview() {
  const draftCustomization = collectDraftCustomization();
  renderLivePreview(previewProjectsCache, draftCustomization);
  markDirtyState(draftCustomization);
}

function scheduleAutosave() {
  if (!isPrivateMode() || !isDirty || isSaving) return;

  clearAutosaveTimer();
  autosaveTimer = setTimeout(() => {
    performSave({ silent: true });
  }, AUTOSAVE_DELAY_MS);
}

function syncFeaturedCheckboxes(projectId, checked) {
  const picker = document.querySelector(
    `[data-featured-project-id="${CSS.escape(projectId)}"]`
  );
  const editor = document.querySelector(
    `[data-project-selected="${CSS.escape(projectId)}"]`
  );

  if (picker) picker.checked = checked;
  if (editor) editor.checked = checked;
}

async function rerenderFeaturedOrdering({ saveNow = false } = {}) {
  const draftCustomization = collectDraftCustomization();
  renderFeaturedOrderList(previewProjectsCache, draftCustomization);
  updateLivePreview();
  markDirtyState(draftCustomization);
  if (saveNow) {
    // Star/unstar should feel immediate
    await performSave({ silent: true });
  } else {
    scheduleAutosave();
  }
}

function handleFeaturedOrderDragStart(event) {
  const item = event.target.closest("[data-featured-order-item]");
  if (!item) return;

  draggedFeaturedProjectId = item.dataset.featuredOrderItem;
  item.classList.add("dragging");

  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedFeaturedProjectId);
  }
}

function handleFeaturedOrderDragOver(event) {
  const target = event.target.closest("[data-featured-order-item]");
  if (!target || !draggedFeaturedProjectId) return;

  event.preventDefault();
  target.classList.add("drag-over");
}

function handleFeaturedOrderDragLeave(event) {
  const target = event.target.closest("[data-featured-order-item]");
  target?.classList.remove("drag-over");
}

function handleFeaturedOrderDrop(event) {
  const target = event.target.closest("[data-featured-order-item]");
  if (!target || !draggedFeaturedProjectId) return;

  event.preventDefault();

  const targetId = target.dataset.featuredOrderItem;
  if (!targetId || targetId === draggedFeaturedProjectId) {
    target.classList.remove("drag-over");
    return;
  }

  const orderedIds = getFeaturedOrderFromDom();
  const fromIndex = orderedIds.indexOf(draggedFeaturedProjectId);
  const toIndex = orderedIds.indexOf(targetId);

  if (fromIndex === -1 || toIndex === -1) {
    target.classList.remove("drag-over");
    return;
  }

  const nextOrder = [...orderedIds];
  const [moved] = nextOrder.splice(fromIndex, 1);
  nextOrder.splice(toIndex, 0, moved);

  const draftCustomization = collectDraftCustomization();
  draftCustomization.featuredProjectIds = nextOrder;

  renderFeaturedOrderList(previewProjectsCache, draftCustomization);
  updateLivePreview();
  scheduleAutosave();
}

function handleFeaturedOrderDragEnd() {
  document
    .querySelectorAll(".customization-featured-order-item")
    .forEach((item) => {
      item.classList.remove("dragging");
      item.classList.remove("drag-over");
    });

  draggedFeaturedProjectId = null;
}

async function performSave({ silent = false } = {}) {
  if (!isPrivateMode()) return;

  clearAutosaveTimer();

  const nextCustomization = collectCustomization(previewProjectsCache);
  const nextSnapshot = snapshotCustomization(nextCustomization);

  if (nextSnapshot === lastSavedSnapshot) {
    isDirty = false;
    updateSaveButtonState();
    setStatus(silent ? "Saved" : "No changes to save", silent ? "success" : "info");
    return "no-changes";
  }

  try {
    isSaving = true;
    updateSaveButtonState();
    setStatus(silent ? "Autosaving..." : "Saving customization...", "info");

    savePortfolioCustomization(nextCustomization);
    await persistProjectOverrides(previewProjectsCache, nextCustomization);

    lastSavedSnapshot = snapshotCustomization(nextCustomization);
    isDirty = false;
    updateSaveButtonState();

    if (!silent) {
      await loadPortfolio();
      window.dispatchEvent(new CustomEvent("portfolio:customization-updated"));
    }

    setStatus(silent ? "Autosaved" : "Saved", "success");
  } catch (error) {
    console.error("Failed to save portfolio customization:", error);
    isDirty = true;
    setStatus(
      silent
        ? "Autosave failed. Please click Save Customization."
        : "Failed to save portfolio customization.",
      "error"
    );
  } finally {
    isSaving = false;
    updateSaveButtonState();
  }
}

async function renderPortfolioCustomizationPage() {
  clearAutosaveTimer();

  if (!isPrivateMode()) {
    previewProjectsCache = [];
    isDirty = false;
    isSaving = false;
    lastSavedSnapshot = "";
    renderPublicModeMessage();
    return;
  }

  try {
    const projects = await fetchProjects();
    const customization = await hydrateCustomizationFromBackend(projects);

    previewProjectsCache = projects;
    lastSavedSnapshot = snapshotCustomization(customization);

    renderFeaturedProjects(projects, customization);
    renderProjectEditors(projects, customization);
    renderFeaturedOrderList(projects, customization);
    renderLivePreview(projects, customization);

    updateSaveButtonState();

    const saveBtn = getSaveButton();
    if (saveBtn) {
      saveBtn.onclick = async () => {
        await performSave({ silent: false });
      };
    }
  } catch (error) {
    console.error("Failed to render portfolio customization page:", error);
    setStatus("Failed to load portfolio customization data.", "error");
  }
}

export function initPortfolioEditor() {
  const tab = document.querySelector('[data-tab="portfolio"]');
  const editorContainer = document.getElementById("portfolio-project-editor-container");
  const featuredContainer = document.getElementById("portfolio-featured-projects-container");
  const orderContainer = getFeaturedOrderContainer();

  if (!portfolioEditorInitialized) {
    portfolioEditorInitialized = true;

    tab?.addEventListener("click", renderPortfolioCustomizationPage);

    document.addEventListener("auth:mode-changed", () => {
      renderPortfolioCustomizationPage();
    });

    window.addEventListener("portfolio:customization-updated", () => {
      renderPortfolioCustomizationPage();
    });

    editorContainer?.addEventListener("input", () => {
      updateLivePreview();
      scheduleAutosave();
    });

    editorContainer?.addEventListener("change", (event) => {
      updateLivePreview();
      scheduleAutosave();
    });

    featuredContainer?.addEventListener("change", async (event) => {
      const target = event.target;

      if (target instanceof HTMLInputElement) {
        if (target.matches("[data-featured-project-id]")) {
          syncFeaturedCheckboxes(target.dataset.featuredProjectId, target.checked);
          await rerenderFeaturedOrdering({ saveNow: true });
          return;
        }

        if (target.matches("[data-project-selected]")) {
          syncFeaturedCheckboxes(target.dataset.projectSelected, target.checked);
          await rerenderFeaturedOrdering({ saveNow: true });
          return;
        }
      }

      updateLivePreview();
      scheduleAutosave();
    });

    orderContainer?.addEventListener("dragstart", handleFeaturedOrderDragStart);
    orderContainer?.addEventListener("dragover", handleFeaturedOrderDragOver);
    orderContainer?.addEventListener("dragleave", handleFeaturedOrderDragLeave);
    orderContainer?.addEventListener("drop", handleFeaturedOrderDrop);
    orderContainer?.addEventListener("dragend", handleFeaturedOrderDragEnd);

    window.addEventListener("beforeunload", (event) => {
      if (!isDirty) return;
      event.preventDefault();
      event.returnValue = "";
    });

    window.addEventListener("portfolio:focus-project-editor", (event) => {
    const projectId = event.detail?.projectId;
    if (!projectId) return;

    activePortfolioProjectId = projectId;
    const customization = loadPortfolioCustomization();
    renderProjectEditors(previewProjectsCache, customization);
  });

  renderPortfolioCustomizationPage();
  }

}
