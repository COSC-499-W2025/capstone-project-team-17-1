const STORAGE_KEY = "loom_portfolio_customization_v1";

const DEFAULT_SECTION_VISIBILITY = {
  "resume-summary": true,
  "top-projects": true,
  "portfolio-stats": true,
  "skills-timeline": true,
  "activity-heatmap": true,
};

const DEFAULT_STATE = {
  sectionVisibility: { ...DEFAULT_SECTION_VISIBILITY },
  featuredProjectIds: [],
  projectOverrides: {},
  jobTarget: {
    title: "",
    company: "",
    description: "",
  },
};

function cloneDefaultState() {
  return {
    sectionVisibility: { ...DEFAULT_STATE.sectionVisibility },
    featuredProjectIds: [],
    projectOverrides: {},
    jobTarget: { ...DEFAULT_STATE.jobTarget },
  };
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
  const defaults = cloneDefaultState();

  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return defaults;
  }

  return {
    sectionVisibility: {
      ...DEFAULT_SECTION_VISIBILITY,
      ...(value.sectionVisibility && typeof value.sectionVisibility === "object"
        ? value.sectionVisibility
        : {}),
    },
    featuredProjectIds: Array.isArray(value.featuredProjectIds)
      ? value.featuredProjectIds.map((id) => String(id).trim()).filter(Boolean)
      : [],
    projectOverrides: normalizeProjectOverrides(value.projectOverrides),
    jobTarget:
      value.jobTarget && typeof value.jobTarget === "object"
        ? {
            title: typeof value.jobTarget.title === "string" ? value.jobTarget.title : "",
            company: typeof value.jobTarget.company === "string" ? value.jobTarget.company : "",
            description:
              typeof value.jobTarget.description === "string"
                ? value.jobTarget.description
                : "",
          }
        : { ...DEFAULT_STATE.jobTarget },
  };
}

function safeParse(raw) {
  try {
    return normalizeCustomization(JSON.parse(raw));
  } catch {
    return cloneDefaultState();
  }
}

function createDefaultCustomization() {
  return cloneDefaultState();
}

export function loadPortfolioCustomization() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return createDefaultCustomization();
  }

  return safeParse(raw);
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
  const customization = loadPortfolioCustomization();

  if (!customization.featuredProjectIds.length) {
    return projects.slice(0, 3);
  }

  const selected = customization.featuredProjectIds
    .map((id) => projects.find((project) => String(project.project_id) === id))
    .filter(Boolean);

  return selected.slice(0, 3);
}
