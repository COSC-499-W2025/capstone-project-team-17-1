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
    <div class="dashboard-selection-content">
      <div class="dashboard-selection-header">
        <div class="dashboard-selection-title">Web Portfolio</div>
        <div class="dashboard-selection-subtitle">Visible sections in private mode</div>
      </div>
      <div class="dashboard-selection-options">
        ${PORTFOLIO_OPTIONS.map(
          (option) => `
            <label class="dashboard-selection-option">
              <input type="checkbox" value="${escapeHtml(option.id)}" ${selectedIds.includes(option.id) ? "checked" : ""} />
              <span class="dashboard-selection-option-check"></span>
              <span class="dashboard-selection-option-label">${escapeHtml(option.label)}</span>
            </label>
          `
        ).join("")}
      </div>
    </div>
  `;

  panel.querySelectorAll('input[type="checkbox"]').forEach((input) => {
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
  const portfolioSearchInput = document.getElementById("portfolio-search-input");
  const portfolioFilterSelect = document.getElementById("portfolio-filter-select");
  const selectionToggle = document.getElementById("portfolio-selection-toggle");
  const selectionPanel = document.getElementById("portfolio-selection-panel");
  const initialState = loadDashboardState();
  const initialPortfolioState = loadPortfolioState();

  if (searchInput) searchInput.value = initialState.search;
  if (filterSelect) filterSelect.value = initialState.category;
  if (portfolioSearchInput) portfolioSearchInput.value = initialPortfolioState.search;
  if (portfolioFilterSelect) portfolioFilterSelect.value = initialPortfolioState.category;

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

  portfolioSearchInput?.addEventListener("input", () => {
    savePortfolioState({
      search: portfolioSearchInput.value,
      category: portfolioFilterSelect?.value || "all",
    });
    applyDisplayPreferences();
  });

  portfolioFilterSelect?.addEventListener("change", () => {
    savePortfolioState({
      search: portfolioSearchInput?.value || "",
      category: portfolioFilterSelect.value,
    });
    applyDisplayPreferences();
  });

  selectionToggle?.addEventListener("click", () => {
    selectionPanel?.classList.toggle("hidden");
  });

  document.addEventListener("click", (event) => {
    const wrapper = document.getElementById("portfolio-selection-wrapper");
    if (!wrapper || !selectionPanel || selectionPanel.classList.contains("hidden")) return;
    // Close the popover
    if (!wrapper.contains(event.target)) {
      selectionPanel.classList.add("hidden");
    }
  });

  document.addEventListener("auth:mode-changed", () => {
    renderPrivateSelectionPanel();
    applyDisplayPreferences();
  });

  renderPrivateSelectionPanel();
  applyDisplayPreferences();
}
