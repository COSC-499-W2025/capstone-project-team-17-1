const STORAGE_KEY = "loom_portfolio_customization_v1";

const DEFAULT_STATE = {
  sectionVisibility: {
    "resume-summary": true,
    "top-projects": true,
    "portfolio-stats": true,
    "skills-timeline": true,
    "activity-heatmap": true,
  },
  featuredProjectIds: [],
  projectOverrides: {},
};

function cloneDefaultState() {
  return JSON.parse(JSON.stringify(DEFAULT_STATE));
}

export function loadPortfolioCustomization() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return cloneDefaultState();

    const parsed = JSON.parse(raw);
    return {
      sectionVisibility: {
        ...DEFAULT_STATE.sectionVisibility,
        ...(parsed?.sectionVisibility || {}),
      },
      featuredProjectIds: Array.isArray(parsed?.featuredProjectIds)
        ? parsed.featuredProjectIds.map((id) => String(id).trim()).filter(Boolean)
        : [],
      projectOverrides:
        parsed?.projectOverrides && typeof parsed.projectOverrides === "object"
          ? parsed.projectOverrides
          : {},
    };
  } catch {
    return cloneDefaultState();
  }
}

export function savePortfolioCustomization(state) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function getProjectOverride(customization, projectId) {
  return customization?.projectOverrides?.[String(projectId).trim()] || {};
}

export function getFeaturedProjects(projects, customization, fallbackSelector) {
  const featuredIds = Array.isArray(customization?.featuredProjectIds)
    ? customization.featuredProjectIds
    : [];

  const selected = featuredIds
    .map((id) => projects.find((project) => project.project_id === id))
    .filter(Boolean);

  if (selected.length >= 3) {
    return selected.slice(0, 3);
  }

  const fallback = typeof fallbackSelector === "function" ? fallbackSelector(projects) : projects;
  const used = new Set(selected.map((project) => project.project_id));

  for (const project of fallback) {
    if (!used.has(project.project_id)) {
      selected.push(project);
      used.add(project.project_id);
    }
    if (selected.length >= 3) break;
  }

  return selected.slice(0, 3);
}