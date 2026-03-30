function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function toTitleCase(value) {
  return String(value || "")
    .split(/[\s-/]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function normalizeSkillName(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";

  const lower = raw.toLowerCase();
  const canonicalMap = {
    js: "JavaScript",
    javascript: "JavaScript",
    ts: "TypeScript",
    typescript: "TypeScript",
    json: "JSON",
    html: "HTML",
    css: "CSS",
    sql: "SQL",
    nosql: "NoSQL",
    api: "API",
    rest: "REST",
    graphql: "GraphQL",
    yaml: "YAML",
    xml: "XML",
    csv: "CSV",
    aws: "AWS",
    gcp: "GCP",
    fastapi: "FastAPI",
    sqlite: "SQLite",
    postgresql: "PostgreSQL",
    mongodb: "MongoDB",
    redis: "Redis",
    nodejs: "Node.js",
    expressjs: "Express.js",
    ui: "UI",
    ux: "UX",
    ci: "CI",
    cd: "CD",
  };

  return canonicalMap[lower] || toTitleCase(raw);
}

function dedupeStrings(values) {
  const seen = new Set();
  const result = [];
  asArray(values)
    .map((v) => normalizeSkillName(v))
    .filter(Boolean)
    .forEach((value) => {
      const key = value.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      result.push(value);
    });
  return result;
}

function getEvidenceText(portfolioEntry = {}) {
  const directEvidence = String(
    portfolioEntry?.evidence_of_success ||
      portfolioEntry?.evidenceOfSuccess ||
      ""
  ).trim();

  if (directEvidence) {
    return directEvidence;
  }

  const structuredEvidence = portfolioEntry?.evidence;
  if (
    structuredEvidence &&
    typeof structuredEvidence === "object" &&
    Array.isArray(structuredEvidence.items)
  ) {
    const values = structuredEvidence.items
      .map((item) => String(item?.value || "").trim())
      .filter(Boolean)
      .slice(0, 2);

    if (values.length) {
      return values.join(" • ");
    }
  }

  return "";
}

function buildContributionSummary(project, details, portfolioEntry = {}) {
  const keyRole = String(
    portfolioEntry?.key_role ||
      portfolioEntry?.keyRole ||
      ""
  ).trim();

  const evidence = getEvidenceText(portfolioEntry);

  const highlights = dedupeStrings(details?.highlights);
  const technologies = dedupeStrings(details?.technologies);

  if (keyRole && evidence) {
    return `${keyRole} • ${evidence}`;
  }

  if (keyRole) {
    return keyRole;
  }

  if (highlights.length) {
    return highlights[0];
  }

  if (technologies.length) {
    return `Applied ${technologies.slice(0, 3).join(", ")} across the implementation.`;
  }

  return `Contributed to ${project.total_files || 0} analyzed file${project.total_files === 1 ? "" : "s"} in this project.`;
}

function buildImpactSummary(project, details, portfolioEntry = {}) {
  const evidence = getEvidenceText(portfolioEntry);

  const highlights = dedupeStrings(details?.highlights);
  const impactSignals = [
    `${project.total_files || 0} file${project.total_files === 1 ? "" : "s"} analyzed`,
    `${project.total_skills || 0} skill signal${project.total_skills === 1 ? "" : "s"} detected`,
  ];

  if (evidence) {
    return `${evidence} Backed by ${impactSignals.join(" and ")}.`;
  }

  if (highlights.length > 1) {
    return `${highlights[1]} Backed by ${impactSignals.join(" and ")}.`;
  }

  return `Portfolio impact is supported by ${impactSignals.join(" and ")}.`;
}

function getTopProjects(projects) {
  return [...projects]
    .sort((a, b) => {
      const skillDiff = (b.total_skills || 0) - (a.total_skills || 0);
      if (skillDiff !== 0) return skillDiff;
      return (b.total_files || 0) - (a.total_files || 0);
    })
    .slice(0, 3);
}

function sortProjectsByRankedIds(projects, rankedIds = []) {
  const rankMap = new Map(
    rankedIds.map((projectId, index) => [String(projectId), index])
  );

  return [...projects].sort((a, b) => {
    const aRank = rankMap.get(String(a.project_id));
    const bRank = rankMap.get(String(b.project_id));
    const aHasRank = aRank !== undefined;
    const bHasRank = bRank !== undefined;

    if (aHasRank && bHasRank) return aRank - bRank;
    if (aHasRank) return -1;
    if (bHasRank) return 1;

    const skillDiff = (b.total_skills || 0) - (a.total_skills || 0);
    if (skillDiff !== 0) return skillDiff;
    return (b.total_files || 0) - (a.total_files || 0);
  });
}

function formatTimelineTimestamp(timestamp) {
  const raw = String(timestamp || "").trim();
  if (!raw) return "Unknown";

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }

  return date.toLocaleString("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function buildProjectProcess(project, details, rank) {
  const sourceLabel = project.is_github ? "Imported the working repository from GitHub" : "Uploaded the project source as a ZIP snapshot";
  const analysisLabel = `Analyzed ${project.total_files || 0} file${project.total_files === 1 ? "" : "s"} to surface implementation signals`;
  const refinementLabel = details?.highlights?.length
    ? `Captured improvement highlights such as ${details.highlights.slice(0, 2).join(" and ")}`
    : `Ranked this project in the top ${rank + 1} based on portfolio depth and detected skills`;

  return [sourceLabel, analysisLabel, refinementLabel];
}

function buildProjectEvolution(project, details) {
  const technologies = dedupeStrings(details?.technologies);
  const highlights = dedupeStrings(details?.highlights);

  if (technologies.length && highlights.length) {
    return `Started with ${technologies.slice(0, 2).join(" and ")}, then evolved through ${highlights[0]}.`;
  }

  if (technologies.length) {
    return `Expanded implementation breadth across ${technologies.slice(0, 3).join(", ")} as the project matured.`;
  }

  if (highlights.length) {
    return `Project evolution is reflected by ${highlights[0]}.`;
  }

  return `Evolution is inferred from ${project.total_files || 0} analyzed files and ${project.total_skills || 0} detected skill signals.`;
}

function getProjectDetailsMap(summaryData) {
  const map = new Map();
  asArray(summaryData?.projects).forEach((project) => {
    const projectId = String(project.project_id || "").trim();
    if (!projectId) return;

    map.set(projectId, {
      project_id: projectId,
      title: String(project.title || project.project_id || "").trim(),
      summary: String(project.summary || "").trim(),
      technologies: dedupeStrings(project.technologies),
      highlights: dedupeStrings(project.highlights),
    });
  });
  return map;
}

function getPortfolioProjectDisplay(project, details, portfolioEntry = {}) {
  const title = String(
    portfolioEntry?.name ||
      details?.title ||
      project.project_id ||
      ""
  ).trim();

  const summary = String(
  portfolioEntry?.portfolio_blurb ||
    portfolioEntry?.summary ||
    details?.summary ||
    ""
  ).trim() ||
    `${project.total_files || 0} file${project.total_files === 1 ? "" : "s"} analyzed • ${project.total_skills || 0} detected skill signal${project.total_skills === 1 ? "" : "s"}`;

  const keyRole = String(
    portfolioEntry?.key_role ||
      portfolioEntry?.keyRole ||
      ""
  ).trim();

  const evidence = String(
    portfolioEntry?.evidence_of_success ||
      portfolioEntry?.evidence ||
      ""
  ).trim();

  const templateId = String(portfolioEntry?.template_id || portfolioEntry?.templateId || "classic").trim();

  const caseStudyAbstract = String(
    portfolioEntry?.case_study_abstract || portfolioEntry?.caseStudyAbstract || ""
  ).trim();

  const images = Array.isArray(portfolioEntry?.images) ? portfolioEntry.images : [];
  const coverImage = images.find((img) => img?.is_cover) || images[0] || null;

  return {
    title,
    summary,
    keyRole,
    evidence,
    caseStudyAbstract,
    templateId,
    images,
    coverImage,
  };
}

function getProjectCardImageMedia(projectId, portfolioEntry, getPortfolioImageAuthPath, getProjectThumbnailUrl) {
  const images = Array.isArray(portfolioEntry?.images) ? portfolioEntry.images : [];
  const cover = images.find((img) => img?.is_cover) || images[0];

  if (cover?.id && typeof getPortfolioImageAuthPath === "function") {
    return { kind: "portfolio", path: getPortfolioImageAuthPath(projectId, cover.id) };
  }

  if (typeof getProjectThumbnailUrl === "function") {
    const url = getProjectThumbnailUrl(projectId);
    if (url) return { kind: "thumbnail", url };
  }

  return null;
}

function buildPortfolioEntryMap(entries) {
  const map = new Map();

  asArray(entries).forEach((entry) => {
    const projectId = String(entry?.project_id || "").trim();
    if (!projectId) return;
    map.set(projectId, entry);
  });

  return map;
}

function getTimelineSkillName(skill) {
  return normalizeSkillName(skill?.name || skill?.skill || "unknown") || "unknown";
}

function getTimelineSkillWeight(skill) {
  const rawWeight = Number(skill?.weight ?? skill?.score ?? skill?.confidence ?? 0);
  if (!Number.isFinite(rawWeight)) return 0;
  return Math.max(0, rawWeight);
}

function getSkillDepthLevel(depthScore) {
  if (depthScore >= 2.5) return "Advanced";
  if (depthScore >= 1.75) return "Proficient";
  if (depthScore >= 1.1) return "Developing";
  return "Foundation";
}

function getSkillGrowthLabel({
  previousWeight,
  currentWeight,
  appearanceCount,
  projectCount,
  previousComplexity,
  currentComplexity,
}) {
  if (appearanceCount <= 1) return "Baseline established";

  const weightDelta = currentWeight - previousWeight;
  const complexityDelta = currentComplexity - previousComplexity;

  if (weightDelta >= 0.08 && (projectCount >= 2 || complexityDelta >= 0.75)) {
    return "Depth increasing";
  }
  if (complexityDelta >= 1.2 || projectCount >= 3) {
    return "Expanding across projects";
  }
  if (weightDelta <= -0.08 && complexityDelta <= -0.75) {
    return "Applying in lighter scope";
  }
  return "Depth sustained";
}

function buildTimelineEntries(timeline) {
  const seenCounts = new Map();
  const previousWeights = new Map();
  const cumulativeWeights = new Map();
  const projectSets = new Map();
  const previousComplexities = new Map();

  return timeline.map((entry) => {
    const rawSkills = Array.isArray(entry.skills) ? entry.skills : [];
    const aggregatedSkills = new Map();
    const projectId = String(entry?.project_id || "").trim();
    const projectMetrics =
      entry?.project_metrics && typeof entry.project_metrics === "object" ? entry.project_metrics : {};
    const currentComplexity = Number(projectMetrics?.complexity_score || 0);

    rawSkills.forEach((skill) => {
      const name = getTimelineSkillName(skill);
      const weight = getTimelineSkillWeight(skill);
      const current = aggregatedSkills.get(name) || { name, weight: 0 };
      current.weight += weight;
      aggregatedSkills.set(name, current);
    });

    const normalizedSkills = [...aggregatedSkills.values()].sort((a, b) => {
      if (b.weight !== a.weight) return b.weight - a.weight;
      return a.name.localeCompare(b.name);
    });

    let recurringCount = 0;
    let newCount = 0;
    let growthCount = 0;

    const decoratedSkills = normalizedSkills.map(({ name, weight }) => {
      const previousCount = seenCounts.get(name) || 0;
      const nextCount = previousCount + 1;
      const previousWeight = previousWeights.get(name) || 0;
      const cumulativeWeight = (cumulativeWeights.get(name) || 0) + weight;
      const projectSet = new Set(projectSets.get(name) || []);
      if (projectId) {
        projectSet.add(projectId);
      }
      const projectCount = projectSet.size;
      const previousComplexity = Number(previousComplexities.get(name) || 0);
      const depthScore = cumulativeWeight + nextCount * 0.35;
      const growthLabel = getSkillGrowthLabel({
        previousWeight,
        currentWeight: weight,
        appearanceCount: nextCount,
        projectCount,
        previousComplexity,
        currentComplexity,
      });

      seenCounts.set(name, nextCount);
      previousWeights.set(name, weight);
      cumulativeWeights.set(name, cumulativeWeight);
      projectSets.set(name, projectSet);
      previousComplexities.set(name, currentComplexity);

      if (previousCount > 0) recurringCount += 1;
      else newCount += 1;
      if (
        previousCount > 0 &&
        (
          weight > previousWeight + 0.08 ||
          projectCount >= 2 ||
          currentComplexity > previousComplexity + 0.75
        )
      ) {
        growthCount += 1;
      }

      return {
        name,
        appearanceCount: nextCount,
        projectCount,
        weight,
        previousWeight,
        cumulativeWeight,
        currentComplexity,
        depthScore,
        level: getSkillDepthLevel(depthScore),
        growthLabel,
        status: previousCount > 0 ? "Recurring" : "First seen",
      };
    });

    return {
      ...entry,
      skills: decoratedSkills,
      meta: {
        totalSkills: normalizedSkills.length,
        recurringCount,
        newCount,
        growthCount,
      },
    };
  });
}

function buildTopProjectsMarkup({
  projects,
  summaryData,
  isPrivateMode,
  getProjectThumbnailUrl,
  portfolioEntryMap,
  getPortfolioImageAuthPath,
}) {
  if (!projects.length) {
    return `
      <div class="empty-state">
        Upload a project to populate your top project showcase.
      </div>
    `;
  }

  const projectDetailsMap = getProjectDetailsMap(summaryData);
  const topProjects = getTopProjects(projects);

  return topProjects
    .map((project, index) => {
      const details = projectDetailsMap.get(project.project_id);
      const portfolioEntry = portfolioEntryMap?.get(String(project.project_id)) || null;
      const display = getPortfolioProjectDisplay(project, details, portfolioEntry);

      const technologies = dedupeStrings(details?.technologies).slice(0, 4);
      const highlights = dedupeStrings(details?.highlights).slice(0, 2);
      const processSteps = isPrivateMode ? buildProjectProcess(project, details, index) : [];
      const evolutionSummary = isPrivateMode ? buildProjectEvolution(project, details) : "";
      const contributionSummary = buildContributionSummary(project, details, portfolioEntry);
      const impactSummary = buildImpactSummary(project, details, portfolioEntry);

      const imageMedia = getProjectCardImageMedia(
        project.project_id,
        portfolioEntry,
        getPortfolioImageAuthPath,
        getProjectThumbnailUrl
      );

      const mediaMarkup =
        imageMedia?.kind === "portfolio"
          ? `
          <img
            class="top-project-thumbnail"
            data-portfolio-auth-src="${escapeHtml(imageMedia.path)}"
            alt="${escapeHtml(display.title)} thumbnail"
            loading="lazy"
            onerror="this.style.display='none'; this.nextElementSibling.classList.remove('hidden');"
          />
          <div class="top-project-thumbnail-fallback hidden" aria-hidden="true">
            <div class="thumbnail-placeholder-art">
              <span class="thumbnail-placeholder-sun"></span>
              <span class="thumbnail-placeholder-mountain thumbnail-placeholder-mountain-back"></span>
              <span class="thumbnail-placeholder-mountain thumbnail-placeholder-mountain-front"></span>
            </div>
          </div>
        `
          : imageMedia?.kind === "thumbnail"
            ? `
          <img
            class="top-project-thumbnail"
            src="${escapeHtml(imageMedia.url)}"
            alt="${escapeHtml(display.title)} thumbnail"
            loading="lazy"
            onerror="this.style.display='none'; this.nextElementSibling.classList.remove('hidden');"
          />
          <div class="top-project-thumbnail-fallback hidden" aria-hidden="true">
            <div class="thumbnail-placeholder-art">
              <span class="thumbnail-placeholder-sun"></span>
              <span class="thumbnail-placeholder-mountain thumbnail-placeholder-mountain-back"></span>
              <span class="thumbnail-placeholder-mountain thumbnail-placeholder-mountain-front"></span>
            </div>
          </div>
        `
            : `
          <div class="top-project-thumbnail-fallback" aria-hidden="true">
            <div class="thumbnail-placeholder-art">
              <span class="thumbnail-placeholder-sun"></span>
              <span class="thumbnail-placeholder-mountain thumbnail-placeholder-mountain-back"></span>
              <span class="thumbnail-placeholder-mountain thumbnail-placeholder-mountain-front"></span>
            </div>
          </div>
        `;

      return `
        <div class="top-project-card">
          <button
            class="top-project-media top-project-thumbnail-button"
            type="button"
            data-project-thumbnail-trigger="${escapeHtml(project.project_id)}"
            aria-label="Upload thumbnail for ${escapeHtml(display.title)}"
          >
            <div class="top-project-rank">#${index + 1}</div>
            ${mediaMarkup}
            <span class="top-project-thumbnail-overlay">Upload thumbnail</span>
          </button>

          <div class="top-project-body">
            <h3>${escapeHtml(display.title)}</h3>
            <p>${escapeHtml(display.summary)}</p>

            ${
              highlights.length
                ? `
                  <ul class="resume-awards-list">
                    ${highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
                  </ul>
                `
                : ""
            }

            <div class="portfolio-detail-block">
              <span class="portfolio-detail-label">Contribution</span>
              <p>${escapeHtml(contributionSummary)}</p>
            </div>

            <div class="project-details">
              <button
                class="project-details-toggle"
                type="button"
                data-evidence-details="${escapeHtml(project.project_id)}"
              >
                View Details
              </button>
              <div
                class="project-details-panel hidden"
                data-evidence-details-panel="${escapeHtml(project.project_id)}"
              >
                <div class="project-story-block">
                  <span class="project-story-label">Evidence of Success</span>
                  <p class="project-evolution-text">${escapeHtml(impactSummary)}</p>
                </div>
              </div>
            </div>

            ${
              isPrivateMode
                ? `
                  <div class="project-details">
                    <button class="project-details-toggle" type="button" data-project-details="${escapeHtml(project.project_id)}">
                      View Details
                    </button>
                    <div class="project-details-panel hidden" data-project-details-panel="${escapeHtml(project.project_id)}">
                      <div class="project-story-grid">
                        <div class="project-story-block">
                          <span class="project-story-label">Process</span>
                          <ol class="project-process-list">
                            ${processSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
                          </ol>
                        </div>
                        <div class="project-story-block">
                          <span class="project-story-label">Evolution</span>
                          <p class="project-evolution-text">${escapeHtml(evolutionSummary)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                `
                : ""
            }

            <div class="project-stack">
              <span class="stack-pill">${project.is_github ? "GitHub Import" : "ZIP Upload"}</span>
              <span class="stack-pill">${project.total_files} Files</span>
              <span class="stack-pill">${project.total_skills} Skills</span>
              <span class="stack-pill">${escapeHtml(toTitleCase(String(display.templateId || "classic").replaceAll("_", " ")))}</span>
              ${technologies.map((tech) => `<span class="stack-pill">${escapeHtml(tech)}</span>`).join("")}
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function buildSkillsTimelineMarkup(timeline) {
  const visibleTimeline = timeline.filter((entry) => {
    const skills = Array.isArray(entry?.skills) ? entry.skills : [];
    const metrics = entry?.project_metrics && typeof entry.project_metrics === "object"
      ? entry.project_metrics
      : {};
    return skills.length > 0 || Number(metrics.file_count || 0) > 0 || Number(metrics.active_days || 0) > 0;
  });

  if (!visibleTimeline.length) {
    return `
      <div class="skills-group-card">
        <h3>No timeline data yet</h3>
        <p class="muted-text">
          Upload projects with detected skills to generate a skills timeline.
        </p>
      </div>
    `;
  }

  return buildTimelineEntries(visibleTimeline)
    .map((entry) => {
      const skills = Array.isArray(entry.skills) ? entry.skills : [];

      return `
        <div class="timeline-year-row">
          <div class="timeline-year">
            <span class="timeline-dot" aria-hidden="true"></span>
            <div class="timeline-time-block">
              <span class="timeline-time-label">${escapeHtml(formatTimelineTimestamp(entry.timestamp || entry.year))}</span>
              ${
                entry.project_id
                  ? `<span class="timeline-project-label">${escapeHtml(entry.project_id)}</span>`
                  : ""
              }
            </div>
          </div>
          <div class="timeline-track">
            <div class="timeline-meta-row">
              <span class="timeline-meta-pill">${entry.meta.totalSkills} skill${entry.meta.totalSkills === 1 ? "" : "s"}</span>
              ${
                entry.meta.newCount
                  ? `<span class="timeline-meta-pill">${entry.meta.newCount} first seen</span>`
                  : ""
              }
              ${
                entry.meta.recurringCount
                  ? `<span class="timeline-meta-pill">${entry.meta.recurringCount} recurring</span>`
                  : ""
              }
              ${
                entry.meta.growthCount
                  ? `<span class="timeline-meta-pill">${entry.meta.growthCount} growing in depth</span>`
                  : ""
              }
            </div>
            <div class="timeline-skill-pills">
              ${
                skills.length
                  ? skills
                      .map((skill) => {
                        const metaParts = [
                          `${skill.status} · ${skill.appearanceCount} snapshot${skill.appearanceCount === 1 ? "" : "s"}`,
                          `${skill.projectCount} project${skill.projectCount === 1 ? "" : "s"}`,
                        ];
                        return `
                            <span class="timeline-skill-pill">
                            <span class="timeline-skill-name">${escapeHtml(skill.name)}</span>
                            <span class="timeline-skill-meta">${escapeHtml(skill.level)} · ${escapeHtml(skill.growthLabel)}</span>
                            <span class="timeline-skill-meta">${escapeHtml(metaParts.join(" · "))}</span>
                          </span>
                        `;
                      })
                      .join("")
                  : `<span class="timeline-empty">No skills recorded</span>`
              }
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

export {
  buildPortfolioEntryMap,
  buildSkillsTimelineMarkup,
  buildTopProjectsMarkup,
  formatTimelineTimestamp,
  getTopProjects,
  sortProjectsByRankedIds,
};
