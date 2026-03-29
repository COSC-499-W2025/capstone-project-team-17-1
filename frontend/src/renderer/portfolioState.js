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
          ? {
            title: typeof parsed.jobTarget.title === "string" ? parsed.jobTarget.title: "",
            company: typeof parsed.jobTarget.company === "string" ? parsed.jobTarget.company : "",
              description:
                typeof parsed.jobTarget.description === "string"
                  ? parsed.jobTarget.description
                  : "",
            }
          : { ...DEFAULT_STATE.jobTarget },
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
      templateId: typeof override.templateId === "string" ? override.templateId : "classic",
      images: Array.isArray(override.images) ? override.images : [],
      analysisDefaults:
        override.analysisDefaults && typeof override.analysisDefaults === "object"
          ? {
              keyRole:
                typeof override.analysisDefaults.keyRole === "string"
                  ? override.analysisDefaults.keyRole
                  : "",
              evidence:
                typeof override.analysisDefaults.evidence === "string"
                  ? override.analysisDefaults.evidence
                  : "",
              portfolioBlurb:
                typeof override.analysisDefaults.portfolioBlurb === "string"
                  ? override.analysisDefaults.portfolioBlurb
                  : "",
            }
          : {
              keyRole: "",
              evidence: "",
              portfolioBlurb: "",
            },
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
    ? value.featuredProjectIds.map((id) => String(id).trim()).filter(Boolean)
    : [];

  const projectOverrides = normalizeProjectOverrides(value.projectOverrides);

  const jobTarget =
    value.jobTarget && typeof value.jobTarget === "object"
      ? {
          title: typeof value.jobTarget.title === "string" ? value.jobTarget.title : "",
          company: typeof value.jobTarget.company === "string" ? value.jobTarget.company : "",
          description:
            typeof value.jobTarget.description === "string"
              ? value.jobTarget.description
              : "",
        }
      : { ...DEFAULT_STATE.jobTarget };

  return {
    sectionVisibility,
    featuredProjectIds,
    projectOverrides,
    jobTarget
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

  const projectMap = new Map(
    projects.map((project) => [String(project.project_id), project])
  );

  return customization.featuredProjectIds
    .map((projectId) => projectMap.get(String(projectId)))
    .filter(Boolean)
    .slice(0, 3);
}

export function notifyPortfolioDataUpdated() {
  window.dispatchEvent(new CustomEvent("portfolio:data-updated"));
}
