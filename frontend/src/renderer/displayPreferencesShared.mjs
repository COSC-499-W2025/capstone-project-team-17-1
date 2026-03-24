export const DASHBOARD_OPTIONS = [
  { id: "most-used-skills", label: "Most Used Skills" },
  { id: "error-analysis", label: "Error Analysis" },
  { id: "project-health", label: "Project Health" },
  { id: "recent-projects", label: "Recent Projects" },
  { id: "system-health", label: "System Health" },
  { id: "activity-log", label: "Activity Log" },
];

export const DEFAULT_DASHBOARD_STATE = {
  search: "",
};

export function getDefaultDashboardSelection() {
  return DASHBOARD_OPTIONS.map((option) => option.id);
}

export function normalizeSelectedIds(selectedIds) {
  const selectedSet = new Set(Array.isArray(selectedIds) ? selectedIds : []);
  return getDefaultDashboardSelection().filter((id) => selectedSet.has(id));
}

export function shouldShowDashboardWidget({
  widgetId,
  label,
  category,
  state,
  isPrivateMode,
  selectedIds,
}) {
  const query = String(state?.search || "").trim().toLowerCase();
  const activeCategory = String(state?.category || "all");
  const normalizedLabel = String(label || widgetId || "").toLowerCase();
  const normalizedCategory = String(category || "all");
  const normalizedSelection = new Set(
    isPrivateMode ? normalizeSelectedIds(selectedIds) : getDefaultDashboardSelection()
  );

  const matchesSearch = !query || normalizedLabel.includes(query);
  const matchesCategory = activeCategory === "all" || normalizedCategory === activeCategory;
  const matchesPrivateSelection = !isPrivateMode || normalizedSelection.has(String(widgetId || ""));

  return matchesSearch && matchesCategory && matchesPrivateSelection;
}
