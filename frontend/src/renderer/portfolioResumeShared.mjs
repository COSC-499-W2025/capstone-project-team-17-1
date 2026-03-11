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

function dedupeStrings(values) {
  return [...new Set(asArray(values).map((v) => String(v).trim()).filter(Boolean))];
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

function buildTopProjectsMarkup({ projects, summaryData, isPrivateMode, getProjectThumbnailUrl }) {
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
      const title = details?.title || project.project_id;
      const summary =
        details?.summary ||
        `${project.total_files} file${project.total_files === 1 ? "" : "s"} analyzed • ${project.total_skills} detected skill signal${project.total_skills === 1 ? "" : "s"}`;

      const technologies = dedupeStrings(details?.technologies).slice(0, 4);
      const highlights = dedupeStrings(details?.highlights).slice(0, 2);
      const processSteps = buildProjectProcess(project, details, index);
      const evolutionSummary = buildProjectEvolution(project, details);

      return `
        <div class="top-project-card">
          <div class="top-project-media">
            <div class="top-project-rank">#${index + 1}</div>
            <img
              class="top-project-thumbnail"
              src="${escapeHtml(getProjectThumbnailUrl(project.project_id))}"
              alt="${escapeHtml(title)} thumbnail"
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
          </div>
          <div class="top-project-body">
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(summary)}</p>

            ${
              highlights.length
                ? `
                  <ul class="resume-awards-list">
                    ${highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
                  </ul>
                `
                : ""
            }

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
              ${technologies.map((tech) => `<span class="stack-pill">${escapeHtml(tech)}</span>`).join("")}
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function buildSkillsTimelineMarkup(timeline) {
  if (!timeline.length) {
    return `
      <div class="skills-group-card">
        <h3>No timeline data yet</h3>
        <p class="resume-summary-text">
          Upload projects with detected skills to generate a skills timeline.
        </p>
      </div>
    `;
  }

  return timeline
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
            <div class="timeline-skill-pills">
              ${
                skills.length
                  ? skills
                      .map((skill) => {
                        const name = skill.name || skill.skill || "unknown";

                        return `
                          <span class="timeline-skill-pill">
                            ${escapeHtml(name)}
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
  buildSkillsTimelineMarkup,
  buildTopProjectsMarkup,
  formatTimelineTimestamp,
  getTopProjects,
};
