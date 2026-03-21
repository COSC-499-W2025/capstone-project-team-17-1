import { fetchProjects } from "./projects.js";
import { authFetch, isPrivateMode } from "./auth.js";
import { loadPortfolioResume } from "./portfolioResume.js";
import {
  loadPortfolioCustomization,
  savePortfolioCustomization,
} from "./portfolioCustomizationState.js";


const AUTOSAVE_DELAY_MS = 1200;

let previewProjectsCache = [];
let portfolioCustomizationInitialized = false;
let draggedFeaturedProjectId = null;
let autosaveTimer = null;
let isDirty = false;
let isSaving = false;
let lastSavedSnapshot = "";


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
      };
    });

  return {
    sectionVisibility,
    featuredProjectIds,
    projectOverrides,
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

  const selected = new Set(customization.featuredProjectIds || []);

  if (!projects.length) {
    container.innerHTML =
      `<p class="muted-text">Upload projects first to choose featured items.</p>`;
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
            data-featured-project-id="${escapeHtml(project.project_id)}"
            ${selected.has(project.project_id) ? "checked" : ""}
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
  if (!container) return;

  if (!projects.length) {
    container.innerHTML =
      `<p class="muted-text">No projects available for customization yet.</p>`;
    return;
  }

  container.innerHTML = projects
    .map((project) => {
      const override = customization.projectOverrides?.[project.project_id] || {};
      const isFeatured = (customization.featuredProjectIds || []).includes(project.project_id);
      const index = (customization.featuredProjectIds || []).indexOf(project.project_id);
      const rank = index >= 0 ? index + 1 : 1;

      const initialSnapshot = JSON.stringify({
        keyRole: override.keyRole || "",
        evidence: override.evidence || "",
        portfolioBlurb: override.portfolioBlurb || "",
        isFeatured,
      });

      return `
        <div class="customization-project-editor" data-project-editor-id="${escapeHtml(project.project_id)}" data-saved-snapshot="${escapeHtml(initialSnapshot)}">
          <div class="customization-project-editor-header">
            <div>
              <h3>${escapeHtml(project.project_id)}</h3>
              <p class="muted-text">
                ${project.total_files || 0} files analyzed • ${project.total_skills || 0} skill signals
              </p>
            </div>

            <div class="customization-project-editor-meta">
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
              <span>Portfolio blurb</span>
              <textarea
                data-field="portfolioBlurb"
                rows="3"
                placeholder="Short description that should appear in the portfolio showcase."
              >${escapeHtml(override.portfolioBlurb || "")}</textarea>
            </label>
          </div>

          <div class="customization-project-editor-actions">
            <span class="customization-project-save-status"></span>
            <button
              type="button"
              class="secondary-btn customization-project-save-btn"
              data-project-save="${escapeHtml(project.project_id)}"
            >
              Save
            </button>
          </div>
        </div>
      `;
    })
    .join("");

    const checkboxes = container.querySelectorAll("[data-project-selected]");
    const saveButtons = container.querySelectorAll("[data-project-save]");
    const starButtons = container.querySelectorAll("[data-project-star]");

    starButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const projectId = btn.dataset.projectStar;
        const cb = container.querySelector(`[data-project-selected="${CSS.escape(projectId)}"]`);
        if (!cb) return;

        const wouldCheck = !cb.checked;
        const checked = container.querySelectorAll("[data-project-selected]:checked");

        if (wouldCheck && checked.length >= 3) {
          setStatus("You can only feature up to 3 projects.", "warning");
          return;
        }

        cb.checked = wouldCheck;
        btn.classList.toggle("starred", wouldCheck);
        setStatus(checked.length <= 3 ? "" : "");
        cb.dispatchEvent(new Event("change"));
      });
    });

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

    return authFetch(`/projects/${encodeURIComponent(project.project_id)}/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

async function saveProjectById(projectId) {
  if (!isPrivateMode()) return "no-changes";

  const editor = document.querySelector(`[data-project-editor-id="${CSS.escape(projectId)}"]`);
  if (!editor) return "no-changes";

  const keyRole = editor.querySelector('[data-field="keyRole"]')?.value?.trim() || "";
  const evidence = editor.querySelector('[data-field="evidence"]')?.value?.trim() || "";
  const portfolioBlurb = editor.querySelector('[data-field="portfolioBlurb"]')?.value?.trim() || "";
  const isFeatured = !!editor.querySelector(`[data-project-selected="${CSS.escape(projectId)}"]`)?.checked;

  const snapshot = JSON.stringify({ keyRole, evidence, portfolioBlurb, isFeatured });
  if (editor.dataset.savedSnapshot === snapshot) return "no-changes";

  const current = loadPortfolioCustomization();
  const featuredIds = current?.featuredProjectIds || [];
  const rank = featuredIds.indexOf(projectId);

  await authFetch(`/projects/${encodeURIComponent(projectId)}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      key_role: keyRole || null,
      evidence: evidence || null,
      portfolio_blurb: portfolioBlurb || null,
      selected: isFeatured,
      rank: rank >= 0 ? rank + 1 : null,
    }),
  });

  // Update local customization store
  const overrides = { ...(current?.projectOverrides || {}), [projectId]: { keyRole, evidence, portfolioBlurb } };
  savePortfolioCustomization({ ...current, projectOverrides: overrides });

  editor.dataset.savedSnapshot = snapshot;

  await loadPortfolioResume();
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

function rerenderFeaturedOrdering() {
  const draftCustomization = collectDraftCustomization();
  renderFeaturedOrderList(previewProjectsCache, draftCustomization);
  updateLivePreview();
  scheduleAutosave();
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
    if (!silent) {
      setStatus("No changes to save", "info");
    } else {
      setStatus("Saved", "success");
    }
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

    await loadPortfolioResume();
    window.dispatchEvent(new CustomEvent("portfolio:customization-updated"));

    setStatus("Saved", "success");
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
    const customization = loadPortfolioCustomization();
    const projects = await fetchProjects();

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

export function initPortfolioCustomization() {
  const tab = document.getElementById("portfolio-tab");
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
      scheduleAutosave();
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
  }

  renderPortfolioCustomizationPage();
}
