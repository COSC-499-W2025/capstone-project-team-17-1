const DASHBOARD_STATE_KEY = "loom_dashboard_state";

function loadDashboardState() {
  try {
    const raw = localStorage.getItem(DASHBOARD_STATE_KEY);
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

function saveDashboardState(state) {
  localStorage.setItem(DASHBOARD_STATE_KEY, JSON.stringify(state));
}

function shouldShowWidget({ label, category, state }) {
  const query = String(state?.search || "").trim().toLowerCase();
  const activeCategory = String(state?.category || "all");
  const normalizedLabel = String(label || "").toLowerCase();
  const normalizedCategory = String(category || "all");

  const matchesSearch = !query || normalizedLabel.includes(query);
  const matchesCategory = activeCategory === "all" || normalizedCategory === activeCategory;
  return matchesSearch && matchesCategory;
}

export function applyDisplayPreferences() {
  const state = loadDashboardState();

  document.querySelectorAll(".dashboard-widget").forEach((element) => {
    const label = element.dataset.widgetLabel || element.dataset.widgetId || "";
    const category = element.dataset.widgetCategory || "all";
    element.classList.toggle(
      "section-hidden",
      !shouldShowWidget({ label, category, state })
    );
  });
}

export function initDisplayPreferences() {
  const searchInput = document.getElementById("dashboard-search-input");
  const filterSelect = document.getElementById("dashboard-filter-select");
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

  applyDisplayPreferences();
}
