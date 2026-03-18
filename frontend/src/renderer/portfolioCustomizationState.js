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

  // target info for pasted job listing
  jobTarget: {
    title: "",
    company: "",
    description: ""
  }
};

function cloneDefaultState() {
  return {
    sectionVisibility: { ...DEFAULT_STATE.sectionVisibility },
    featuredProjectIds: [],
    projectOverrides: {},
    jobTarget: { ...DEFAULT_STATE.jobTarget },
  };
}

function createDefaultCustomization() {
  return cloneDefaultState();
}

function safeParse(raw) {
  try {
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
      jobTarget:
        parsed?.jobTarget && typeof parsed.jobTarget === "object"
          ? parsed.jobTarget
          : cloneDefaultState().jobTarget,
    };
  } catch {
    return null;
  }
}

function normalizeProjectOverrides(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }

  const normalized = {};

  Object.entries(value).forEach(([projectId, override]) => {
    if (!override || typeof override !== "object" || Array.isArray(override)) {
      return;
    }

    normalized[String(projectId)] = {
      keyRole: typeof override.keyRole === "string" ? override.keyRole : "",
      evidence: typeof override.evidence === "string" ? override.evidence : "",
      portfolioBlurb:
        typeof override.portfolioBlurb === "string" ? override.portfolioBlurb : "",
    };
  });

  return normalized;
}

function normalizeCustomization(value) {
  const defaults = createDefaultCustomization();

  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return defaults;
  }

  const sectionVisibility = {
    ...DEFAULT_STATE.sectionVisibility,
    ...(value.sectionVisibility && typeof value.sectionVisibility === "object"
      ? value.sectionVisibility
      : {}),
  };

  const featuredProjectIds = Array.isArray(value.featuredProjectIds)
    ? value.featuredProjectIds.map((id) => String(id))
    : [];

  const projectOverrides = normalizeProjectOverrides(value.projectOverrides);

  return {
    sectionVisibility,
    featuredProjectIds,
    projectOverrides,
  };
}

export function loadPortfolioCustomization() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return createDefaultCustomization();
  }

  return normalizeCustomization(safeParse(raw));
}

export function savePortfolioCustomization(customization) {
  const normalized = normalizeCustomization(customization);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function getProjectOverride(projectId) {
  const customization = loadPortfolioCustomization();
  return customization.projectOverrides[String(projectId)] || null;
}

export function getFeaturedProjects(projects = []) {
  const raw = localStorage.getItem(STORAGE_KEY);
  const parsed = raw ? safeParse(raw) : null;
  const customization = normalizeCustomization(parsed);

  // Only fallback to first 3 projects when there is NO saved customization yet.
  // If featuredProjectIds exists (even as []), respect the saved state.
  if (!parsed || !Array.isArray(parsed.featuredProjectIds)) {
    return projects.slice(0, 3);
  }

  const featuredIds = new Set(customization.featuredProjectIds);
  const selected = projects.filter((p) => featuredIds.has(String(p.project_id)));
  return selected.slice(0, 3);
}
