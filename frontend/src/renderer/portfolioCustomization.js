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

let previewProjectsCache = [];
let portfolioCustomizationInitialized = false;
let draggedFeaturedProjectId = null;

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

function getPreviewContainer() {
  return document.getElementById("portfolio-live-preview-container");
}

function getFeaturedOrderContainer() {
  return document.getElementById("portfolio-featured-order-container");
}

function renderPublicModeMessage() {
  const toggleContainer = document.getElementById("portfolio-section-toggle-container");
  const featuredContainer = document.getElementById("portfolio-featured-projects-container");
  const orderContainer = getFeaturedOrderContainer();
  const editorContainer = document.getElementById("portfolio-project-editor-container");
  const previewContainer = getPreviewContainer();
  const saveBtn = document.getElementById("portfolio-customization-save-btn");

  if (toggleContainer) {
    toggleContainer.innerHTML =
      `<p class="resume-summary-text">Switch to Private Mode to customize your portfolio.</p>`;
  }
  if (featuredContainer) {
    featuredContainer.innerHTML =
      `<p class="resume-summary-text">Featured project selection is only available in Private Mode.</p>`;
  }
  if (orderContainer) {
    orderContainer.innerHTML =
      `<p class="resume-summary-text">Reordering is only available in Private Mode.</p>`;
  }
  if (editorContainer) {
    editorContainer.innerHTML =
      `<p class="resume-summary-text">Project portfolio edits are only available in Private Mode.</p>`;
  }
  if (previewContainer) {
    previewContainer.innerHTML =
      `<p class="resume-summary-text">Live preview is only available in Private Mode.</p>`;
  }
  if (saveBtn) {
    saveBtn.disabled = true;
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
    container.innerHTML =
      `<p class="resume-summary-text">Upload projects first to choose featured items.</p>`;
    return;
  }

  container.innerHTML = projects
    .map(
      (project) => `
        <label class="customization-project-pick">
          <input
            type="checkbox"
            data-featured-project-id="${escapeHtml(project.project_id)}"
            ${selected.has(project.project_id) ? "checked" : ""}
          />
          <div>
            <div class="customization-project-title">${escapeHtml(project.project_id)}</div>
            <div class="customization-project-meta">
              ${project.total_files || 0} files • ${project.total_skills || 0} skills
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
    container.innerHTML =
      `<p class="resume-summary-text">No projects available for customization yet.</p>`;
    return;
  }

  container.innerHTML = projects
    .map((project) => {
      const override = customization.projectOverrides?.[project.project_id] || {};
      const isFeatured = (customization.featuredProjectIds || []).includes(project.project_id);

      return `
        <div class="customization-project-editor" data-project-editor-id="${escapeHtml(project.project_id)}">
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
            </div>
          </div>

          <div class="customization-form-grid">
            <label>
              <span>Key role</span>
              <input
                type="text"
                data-field="keyRole"
                value="${escapeHtml(override.keyRole || "")}"
                placeholder="Example: Frontend integration lead"
              />
            </label>

            <label class="customization-full-row">
              <span>Evidence of success</span>
              <textarea
                data-field="evidence"
                rows="3"
                placeholder="Example: Built the portfolio UI, integrated the summary endpoints, and improved milestone demo readiness."
              >${escapeHtml(override.evidence || "")}</textarea>
            </label>

            <label class="customization-full-row">
              <span>Portfolio blurb</span>
              <textarea
                data-field="portfolioBlurb"
                rows="3"
                placeholder="Short description that should appear in the portfolio showcase."
              >${escapeHtml(override.portfolioBlurb || "")}</textarea>
            </label>
          </div>
        </div>
      `;
    })
    .join("");
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

  const sectionVisibility = {};
  SECTION_LABELS.forEach((section) => {
    const input = document.querySelector(
      `[data-section-visibility="${CSS.escape(section.id)}"]`
    );
    sectionVisibility[section.id] = input ? !!input.checked : true;
  });

  let featuredProjectIds = getFeaturedOrderFromDom();
  if (!featuredProjectIds.length) {
    featuredProjectIds = getSelectedProjectIdsFromInputs(projects);
  }

  const projectOverrides = {};
  projects.forEach((project) => {
    const editor = document.querySelector(
      `[data-project-editor-id="${CSS.escape(project.project_id)}"]`
    );

    const keyRole = editor?.querySelector('[data-field="keyRole"]')?.value?.trim() || "";
    const evidence = editor?.querySelector('[data-field="evidence"]')?.value?.trim() || "";
    const portfolioBlurb =
      editor?.querySelector('[data-field="portfolioBlurb"]')?.value?.trim() || "";

    projectOverrides[project.project_id] = {
      keyRole,
      evidence,
      portfolioBlurb,
    };
  });

  return {
    ...current,
    sectionVisibility,
    featuredProjectIds,
    projectOverrides,
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

function renderLivePreview(projects, draftCustomization) {
  const container = getPreviewContainer();
  if (!container) return;

  const sectionVisibility = {
    "resume-summary": true,
    "top-projects": true,
    "portfolio-stats": true,
    "skills-timeline": true,
    "activity-heatmap": true,
    ...(draftCustomization.sectionVisibility || {}),
  };

  const projectMap = new Map(
    projects.map((project) => [String(project.project_id), project])
  );

  const featuredProjects = (draftCustomization.featuredProjectIds || [])
    .map((id) => projectMap.get(String(id)))
    .filter(Boolean)
    .slice(0, 3);

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);

  container.innerHTML = `
    <div class="live-preview-section ${sectionVisibility["resume-summary"] ? "" : "hidden"}">
      <h3>Resume Snapshot</h3>
      <p>${totalProjects} project${totalProjects === 1 ? "" : "s"} • ${totalFiles} files • ${totalSkills} skill signals</p>
    </div>

    <div class="live-preview-section ${sectionVisibility["top-projects"] ? "" : "hidden"}">
      <h3>Top 3 Project Showcase</h3>
      ${
        featuredProjects.length
          ? featuredProjects
              .map((project) => {
                const override =
                  draftCustomization.projectOverrides?.[project.project_id] || {};

                return `
                  <div class="live-preview-project-card">
                    <h4>${escapeHtml(project.project_id)}</h4>
                    <div class="live-preview-meta">
                      ${project.total_files || 0} files • ${project.total_skills || 0} skills
                    </div>
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
                  </div>
                `;
              })
              .join("")
          : `<p class="live-preview-empty">No featured projects selected.</p>`
      }
    </div>

    <div class="live-preview-section ${sectionVisibility["portfolio-stats"] ? "" : "hidden"}">
      <h3>Portfolio Stats</h3>
      <p>${totalProjects} Projects • ${totalFiles} Files • ${totalSkills} Skill Signals</p>
    </div>

    <div class="live-preview-section ${sectionVisibility["skills-timeline"] ? "" : "hidden"}">
      <h3>Skills Timeline</h3>
      <p class="live-preview-empty">Timeline preview follows the saved portfolio layout.</p>
    </div>

    <div class="live-preview-section ${sectionVisibility["activity-heatmap"] ? "" : "hidden"}">
      <h3>Activity Heatmap</h3>
      <p class="live-preview-empty">Heatmap preview follows the saved portfolio layout.</p>
    </div>
  `;
}

function updateLivePreview() {
  const draftCustomization = collectDraftCustomization();
  renderLivePreview(previewProjectsCache, draftCustomization);
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

function rerenderFeaturedOrdering() {
  const draftCustomization = collectDraftCustomization();
  renderFeaturedOrderList(previewProjectsCache, draftCustomization);
  updateLivePreview();
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

async function renderPortfolioCustomizationPage() {
  const saveBtn = document.getElementById("portfolio-customization-save-btn");
  if (!saveBtn) return;

  if (!isPrivateMode()) {
    previewProjectsCache = [];
    renderPublicModeMessage();
    setStatus("Private Mode is required for portfolio customization.", "warning");
    return;
  }

  saveBtn.disabled = false;
  setStatus("");

  try {
    const customization = loadPortfolioCustomization();
    const projects = await fetchProjects();

    previewProjectsCache = projects;

    renderSectionToggles(customization);
    renderFeaturedProjects(projects, customization);
    renderProjectEditors(projects, customization);
    renderFeaturedOrderList(projects, customization);
    updateLivePreview();

    saveBtn.onclick = async () => {
      try {
        saveBtn.disabled = true;
        setStatus("Saving customization...", "info");

        const nextCustomization = collectCustomization(projects);
        savePortfolioCustomization(nextCustomization);
        await persistProjectOverrides(projects, nextCustomization);

        await loadPortfolioResume();
        window.dispatchEvent(new CustomEvent("portfolio:customization-updated"));

        setStatus("Portfolio customization saved.", "success");
      } catch (error) {
        console.error("Failed to save portfolio customization:", error);
        setStatus("Failed to save portfolio customization.", "error");
      } finally {
        saveBtn.disabled = false;
      }
    };
  } catch (error) {
    console.error("Failed to render portfolio customization page:", error);
    setStatus("Failed to load portfolio customization data.", "error");
  }
}

export function initPortfolioCustomization() {
  const tab = document.getElementById("customization-tab");
  const root = document.getElementById("portfolio-customization-root");
  const orderContainer = getFeaturedOrderContainer();

  if (!portfolioCustomizationInitialized) {
    portfolioCustomizationInitialized = true;

    tab?.addEventListener("click", renderPortfolioCustomizationPage);

    document.addEventListener("auth:mode-changed", () => {
      renderPortfolioCustomizationPage();
    });

    window.addEventListener("portfolio:customization-updated", () => {
      renderPortfolioCustomizationPage();
    });

    root?.addEventListener("input", () => {
      updateLivePreview();
    });

    root?.addEventListener("change", (event) => {
      const target = event.target;

      if (target instanceof HTMLInputElement) {
        if (target.matches("[data-featured-project-id]")) {
          syncFeaturedCheckboxes(target.dataset.featuredProjectId, target.checked);
          rerenderFeaturedOrdering();
          return;
        }

        if (target.matches("[data-project-selected]")) {
          syncFeaturedCheckboxes(target.dataset.projectSelected, target.checked);
          rerenderFeaturedOrdering();
          return;
        }
      }

      updateLivePreview();
    });

    orderContainer?.addEventListener("dragstart", handleFeaturedOrderDragStart);
    orderContainer?.addEventListener("dragover", handleFeaturedOrderDragOver);
    orderContainer?.addEventListener("dragleave", handleFeaturedOrderDragLeave);
    orderContainer?.addEventListener("drop", handleFeaturedOrderDrop);
    orderContainer?.addEventListener("dragend", handleFeaturedOrderDragEnd);
  }

  renderPortfolioCustomizationPage();
}