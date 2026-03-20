import { getCurrentUser, isPrivateMode } from "./auth.js";
import {
  DASHBOARD_OPTIONS,
  DEFAULT_DASHBOARD_STATE,
  shouldShowDashboardWidget,
} from "./displayPreferencesShared.mjs";

const DASHBOARD_STATE_KEY = "loom_dashboard_state";
const PORTFOLIO_STATE_KEY = "loom_portfolio_state";
const PRIVATE_SELECTION_KEY = "loom_private_portfolio_selection";
const PORTFOLIO_OPTIONS = [
  { id: "project-details", label: "Project Portfolio Details" },
  { id: "top-projects", label: "Top 3 Project Showcase" },
  { id: "portfolio-stats", label: "Portfolio Stats" },
  { id: "skills-timeline", label: "Skills Timeline" },
  { id: "activity-heatmap", label: "Activity Heatmap" },
  { id: "live-preview", label: "Live Preview" },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getPrivateSelectionKey() {
  const user = getCurrentUser();
  // Keep private portfolio selections scoped to the logged-in user
  const scope = user?.id || user?.username || "private";
  return `${PRIVATE_SELECTION_KEY}:${scope}`;
}

function loadDashboardState() {
  try {
    const raw = localStorage.getItem(DASHBOARD_STATE_KEY);
    if (!raw) return { ...DEFAULT_DASHBOARD_STATE };
    const parsed = JSON.parse(raw);
    return {
      search: String(parsed?.search || ""),
      category: String(parsed?.category || "all"),
    };
  } catch (_) {
    return { ...DEFAULT_DASHBOARD_STATE };
  }
}

function saveDashboardState(state) {
  localStorage.setItem(DASHBOARD_STATE_KEY, JSON.stringify(state));
}

function loadPortfolioState() {
  try {
    const raw = localStorage.getItem(PORTFOLIO_STATE_KEY);
    if (!raw) return { search: "", category: "all" };
    const parsed = JSON.parse(raw);
    return {
      search: String(parsed?.search || ""),
      category: String(parsed?.category || "all"),
    };
  } catch (_) {
    return { search: "", category: "all" };
  }
}

function savePortfolioState(state) {
  localStorage.setItem(PORTFOLIO_STATE_KEY, JSON.stringify(state));
}

function loadPrivateDashboardSelection() {
  if (!isPrivateMode()) {
    return PORTFOLIO_OPTIONS.map((option) => option.id);
  }

  try {
    const raw = localStorage.getItem(getPrivateSelectionKey());
    if (!raw) return PORTFOLIO_OPTIONS.map((option) => option.id);
    const parsed = JSON.parse(raw);
    const selectedIds = Array.isArray(parsed?.selectedIds) ? parsed.selectedIds : [];
    return PORTFOLIO_OPTIONS.map((option) => option.id).filter((id) => selectedIds.includes(id));
  } catch (_) {
    return PORTFOLIO_OPTIONS.map((option) => option.id);
  }
}

function savePrivateDashboardSelection(selectedIds) {
  if (!isPrivateMode()) return;
  localStorage.setItem(getPrivateSelectionKey(), JSON.stringify({ selectedIds }));
}

function renderPrivateSelectionPanel() {
  const wrapper = document.getElementById("portfolio-selection-wrapper");
  const panel = document.getElementById("portfolio-selection-panel");
  if (!wrapper || !panel) return;

  wrapper.classList.toggle("hidden", !isPrivateMode());
  if (!isPrivateMode()) {
    panel.classList.add("hidden");
    return;
  }

  const selectedIds = loadPrivateDashboardSelection();

  // Re-render
  panel.innerHTML = `
    <div class="tab-selection-content">
      <div class="tab-selection-header">
        <div class="tab-selection-title">Web Portfolio</div>
        <div class="tab-selection-subtitle">Click row to jump · toggle to show/hide</div>
      </div>
      <div class="tab-selection-options">
        ${PORTFOLIO_OPTIONS.map(
          (option) => `
            <div class="tab-selection-option" data-section-id="${escapeHtml(option.id)}">
              <label class="tab-selection-option-toggle" onclick="event.stopPropagation()">
                <input type="checkbox" value="${escapeHtml(option.id)}" ${selectedIds.includes(option.id) ? "checked" : ""} />
                <span class="tab-selection-option-check"></span>
              </label>
              <span class="tab-selection-option-label">${escapeHtml(option.label)}</span>
              <span class="tab-selection-option-jump" title="Jump to section">↗</span>
            </div>
          `
        ).join("")}
      </div>
    </div>
  `;

  panel.querySelectorAll(".tab-selection-option").forEach((row) => {
    const sectionId = row.dataset.sectionId;
    const input = row.querySelector('input[type="checkbox"]');

    // Row click → jump to section
    row.addEventListener("click", () => {
      const target = document.querySelector(`[data-portfolio-section="${sectionId}"]`);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      panel.classList.add("hidden");
    });

    // Checkbox change → toggle visibility
    input.addEventListener("change", () => {
      const nextSelectedIds = Array.from(panel.querySelectorAll('input[type="checkbox"]:checked')).map(
        (checkbox) => checkbox.value
      );
      savePrivateDashboardSelection(nextSelectedIds);
      applyDisplayPreferences();
    });
  });
}

function applyDashboardVisibility() {
  const { search, category } = loadDashboardState();
  const query = search.trim().toLowerCase();

  document.querySelectorAll(".dashboard-widget").forEach((element) => {
    const widgetId = element.dataset.widgetId || "";
    const label = (element.dataset.widgetLabel || widgetId).toLowerCase();
    const widgetCategory = element.dataset.widgetCategory || "all";
    element.classList.toggle(
      "section-hidden",
      !shouldShowDashboardWidget({
        widgetId,
        label,
        category: widgetCategory,
        state: { search: query, category },
        isPrivateMode: false,
        selectedIds: [],
      })
    );
  });
}

export function applyDisplayPreferences() {
  applyDashboardVisibility();
  const selectedIds = new Set(loadPrivateDashboardSelection());
  const portfolioState = loadPortfolioState();
  const query = portfolioState.search.trim().toLowerCase();

  document.querySelectorAll(".portfolio-section").forEach((element) => {
    const sectionId = element.dataset.portfolioSection || "";
    const label = (element.dataset.portfolioLabel || sectionId).toLowerCase();
    const category = element.dataset.portfolioCategory || "all";
    const matchesSearch = !query || label.includes(query);
    const matchesCategory = portfolioState.category === "all" || category === portfolioState.category;
    const matchesSelection = !isPrivateMode() || selectedIds.has(sectionId);
    const isVisible = matchesSearch && matchesCategory && matchesSelection;
    element.classList.toggle("section-hidden", !isVisible);
  });
}

export function initDisplayPreferences() {
  const searchInput = document.getElementById("dashboard-search-input");
  const filterSelect = document.getElementById("dashboard-filter-select");
  const selectionToggle = document.getElementById("portfolio-selection-toggle");
  const selectionPanel = document.getElementById("portfolio-selection-panel");
  const initialState = loadDashboardState();

  if (searchInput) searchInput.value = initialState.search;
  if (filterSelect) filterSelect.value = initialState.category;

  searchInput?.addEventListener("input", () => {
    saveDashboardState({
      search: searchInput.value,
      category: filterSelect?.value || "all",
    });
    applyDisplayPreferences();
  });

  filterSelect?.addEventListener("change", () => {
    saveDashboardState({
      search: searchInput?.value || "",
      category: filterSelect.value,
    });
    applyDisplayPreferences();
  });

  selectionToggle?.addEventListener("click", (e) => {
    e.stopPropagation();
    selectionPanel?.classList.toggle("hidden");
  });

  document.addEventListener("click", (event) => {
    const wrapper = document.getElementById("portfolio-selection-wrapper");
    if (!wrapper) return;
    if (!wrapper.contains(event.target)) {
      selectionPanel?.classList.add("hidden");
    }
  });

  document.addEventListener("auth:mode-changed", () => {
    renderPrivateSelectionPanel();
    applyDisplayPreferences();
  });

  renderPrivateSelectionPanel();
  applyDisplayPreferences();
}
