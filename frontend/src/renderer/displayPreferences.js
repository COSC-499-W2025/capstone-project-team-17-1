import { getCurrentUser, isPrivateMode } from "./auth.js";
import {
  DASHBOARD_OPTIONS,
  DEFAULT_DASHBOARD_STATE,
  getDefaultDashboardSelection,
  normalizeSelectedIds,
  shouldShowDashboardWidget,
} from "./displayPreferencesShared.mjs";

const DASHBOARD_STATE_KEY = "loom_dashboard_state";
const PRIVATE_SELECTION_KEY = "loom_private_dashboard_selection";

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
  // Keep private dashboard selections scoped to the logged-in user
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

function loadPrivateDashboardSelection() {
  if (!isPrivateMode()) {
    return getDefaultDashboardSelection();
  }

  try {
    const raw = localStorage.getItem(getPrivateSelectionKey());
    if (!raw) return getDefaultDashboardSelection();
    const parsed = JSON.parse(raw);
    return normalizeSelectedIds(parsed?.selectedIds);
  } catch (_) {
    return getDefaultDashboardSelection();
  }
}

function savePrivateDashboardSelection(selectedIds) {
  if (!isPrivateMode()) return;
  localStorage.setItem(getPrivateSelectionKey(), JSON.stringify({ selectedIds }));
}

function renderPrivateSelectionPanel() {
  const wrapper = document.getElementById("dashboard-selection-wrapper");
  const panel = document.getElementById("dashboard-selection-panel");
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
        <div class="dashboard-selection-title">Visible Widgets</div>
        <div class="dashboard-selection-subtitle">Private mode only</div>
      </div>
      <div class="dashboard-selection-options">
        ${DASHBOARD_OPTIONS.map(
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
  const selectedIds = new Set(loadPrivateDashboardSelection());

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
        isPrivateMode: isPrivateMode(),
        selectedIds: [...selectedIds],
      })
    );
  });
}

export function applyDisplayPreferences() {
  applyDashboardVisibility();
}

export function initDisplayPreferences() {
  const searchInput = document.getElementById("dashboard-search-input");
  const filterSelect = document.getElementById("dashboard-filter-select");
  const selectionToggle = document.getElementById("dashboard-selection-toggle");
  const selectionPanel = document.getElementById("dashboard-selection-panel");
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

  selectionToggle?.addEventListener("click", () => {
    selectionPanel?.classList.toggle("hidden");
  });

  document.addEventListener("click", (event) => {
    const wrapper = document.getElementById("dashboard-selection-wrapper");
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
