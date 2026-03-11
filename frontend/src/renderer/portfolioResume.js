import { fetchProjects } from "./projects.js";
import { applyDisplayPreferences } from "./displayPreferences.js";
import { isPrivateMode } from "./auth.js";

const API_BASE = "http://127.0.0.1:8002"; // change to 8003 only if you keep backend on 8003

function getStaticProfile() {
  return {
    name: "Raunak Khanna",
    title: "Computer Science Student",
    education: "UBC Okanagan — BSc Computer Science",
    awards: ["Capstone Team Contributor"],
  };
}

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

async function fetchSkillsTimeline() {
  const res = await fetch(`${API_BASE}/skills/timeline`);
  if (!res.ok) {
    throw new Error(`Failed to fetch skills timeline: ${res.status}`);
  }
  const payload = await res.json();
  return Array.isArray(payload.timeline) ? payload.timeline : [];
}

async function fetchPortfolioResumeSummary() {
  const res = await fetch(`${API_BASE}/portfolio/latest/summary`);
  if (!res.ok) {
    throw new Error(`Failed to fetch portfolio summary: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || null;
}

async function fetchActivityHeatmap() {
  const res = await fetch(`${API_BASE}/portfolio/activity-heatmap`);
  if (!res.ok) {
    throw new Error(`Failed to fetch activity heatmap: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || { cells: [], maxCount: 0, projectCount: 0 };
}

function buildProfile(summaryData) {
  const fallback = getStaticProfile();
  return {
    name: summaryData?.owner || fallback.name,
    title: fallback.title,
    education: summaryData?.education || fallback.education,
    awards: dedupeStrings(summaryData?.awards).length
      ? dedupeStrings(summaryData.awards)
      : fallback.awards,
  };
}

function getPortfolioProjects(summaryData) {
  return asArray(summaryData?.projects).map((project) => ({
    project_id: String(project.project_id || "").trim(),
    title: String(project.title || project.project_id || "").trim(),
    summary: String(project.summary || "").trim(),
    technologies: dedupeStrings(project.technologies),
    highlights: dedupeStrings(project.highlights),
  }));
}

function getProjectDetailsMap(summaryData) {
  const map = new Map();
  getPortfolioProjects(summaryData).forEach((project) => {
    if (project.project_id) map.set(project.project_id, project);
  });
  return map;
}

function formatPeriodLabel(period) {
  const raw = String(period || "").trim();

  if (/^\d{4}-\d{2}$/.test(raw)) {
    const [year, month] = raw.split("-");
    const monthIndex = Number(month) - 1;
    const date = new Date(Number(year), monthIndex, 1);

    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleString("en-US", { month: "short", year: "numeric" });
    }
  }

  return raw || "Unknown";
}

function getHeatmapBucket(intensity) {
  if (intensity >= 0.8) return 4;
  if (intensity >= 0.6) return 3;
  if (intensity >= 0.35) return 2;
  if (intensity > 0) return 1;
  return 0;
}

function getProjectThumbnailUrl(projectId) {
  const safeId = encodeURIComponent(String(projectId || "").trim());
  return `${API_BASE}/projects/${safeId}/thumbnail`;
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

function renderResumeSummary(profile, projects, summaryData) {
  const container = document.getElementById("resume-summary-container");
  if (!container) return;

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);

  const backendSkills = dedupeStrings(summaryData?.skills);
  const highlights = dedupeStrings(summaryData?.highlights).slice(0, 4);
  const featuredProjects = getTopProjects(projects).slice(0, 3);

  const summary =
    totalProjects > 0
      ? `Built a portfolio with ${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"}, covering ${totalFiles} analyzed file${totalFiles === 1 ? "" : "s"} and ${totalSkills} detected skill signal${totalSkills === 1 ? "" : "s"}.`
      : "Upload projects to generate a one-page resume summary and portfolio showcase.";

  container.innerHTML = `
    <div class="resume-summary-card">
      <div class="resume-hero-shell">
        <div class="resume-summary-top">
          <h3>${escapeHtml(profile.name)}</h3>
          <p class="resume-role">${escapeHtml(profile.title)}</p>
          <p class="resume-summary-text">${escapeHtml(summary)}</p>
          <div class="resume-hero-actions">
            <span class="hero-stat-chip">${totalProjects} Project${totalProjects === 1 ? "" : "s"}</span>
            <span class="hero-stat-chip">${totalSkills} Skill Signal${totalSkills === 1 ? "" : "s"}</span>
            <span class="hero-stat-chip">${totalFiles} Files Analyzed</span>
          </div>
        </div>
        <div class="resume-hero-spotlight">
          <span class="resume-meta-label">Featured Build Set</span>
          <div class="hero-project-list">
            ${
              featuredProjects.length
                ? featuredProjects
                    .map(
                      (project) => `
                        <div class="hero-project-item">
                          <span class="hero-project-name">${escapeHtml(project.project_id)}</span>
                          <span class="hero-project-meta">${project.total_files || 0} files • ${project.total_skills || 0} skills</span>
                        </div>
                      `
                    )
                    .join("")
                : `<div class="hero-project-item"><span class="hero-project-name">No featured projects yet</span></div>`
            }
          </div>
        </div>
      </div>

      <div class="resume-meta-grid">
        <div class="resume-meta-box">
          <span class="resume-meta-label">Education</span>
          <span class="resume-meta-value">${escapeHtml(profile.education)}</span>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Awards</span>
          <ul class="resume-awards-list">
            ${profile.awards.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Projects Uploaded</span>
          <span class="resume-meta-value">${totalProjects}</span>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Portfolio Coverage</span>
          <span class="resume-meta-value">${totalFiles} files • ${totalSkills} skill signals</span>
        </div>
      </div>

      ${
        backendSkills.length
          ? `
            <div class="resume-meta-box">
              <span class="resume-meta-label">Core Skills</span>
              <div class="skills-pill-row">
                ${backendSkills
                  .slice(0, 10)
                  .map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`)
                  .join("")}
              </div>
            </div>
          `
          : ""
      }

      ${
        highlights.length
          ? `
            <div class="resume-meta-box">
              <span class="resume-meta-label">Portfolio Highlights</span>
              <ul class="resume-awards-list">
                ${highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
              </ul>
            </div>
          `
          : ""
      }
    </div>
  `;
}

function renderTopProjects(projects, summaryData) {
  const container = document.getElementById("top-projects-container");
  if (!container) return;

  if (!projects.length) {
    container.innerHTML = `
      <div class="empty-state">
        Upload a project to populate your top project showcase.
      </div>
    `;
    return;
  }

  const projectDetailsMap = getProjectDetailsMap(summaryData);
  const topProjects = getTopProjects(projects);

  container.innerHTML = topProjects
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
      const privateMode = isPrivateMode();

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
              privateMode
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

  container.querySelectorAll(".project-details-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const projectId = button.getAttribute("data-project-details");
      const panel = container.querySelector(`[data-project-details-panel="${projectId}"]`);
      const isHidden = panel?.classList.contains("hidden");
      panel?.classList.toggle("hidden", !isHidden);
      button.textContent = isHidden ? "Hide Details" : "View Details";
    });
  });
}

function renderPortfolioStats(projects, summaryData) {
  const container = document.getElementById("skills-expertise-container");
  if (!container) return;

  if (!projects.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No portfolio data yet</h3>
        <p class="resume-summary-text">
          Upload projects to generate skills, highlights, and portfolio statistics.
        </p>
      </div>
    `;
    return;
  }

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);
  const githubCount = projects.filter((p) => p.is_github).length;

  const backendSkills = dedupeStrings(summaryData?.skills);
  const backendHighlights = dedupeStrings(summaryData?.highlights);

  container.innerHTML = `
    <div class="skills-group-card">
      <h3>Portfolio Stats</h3>
      <div class="skills-pill-row">
        <span class="skills-pill">${totalProjects} Projects</span>
        <span class="skills-pill">${totalFiles} Files</span>
        <span class="skills-pill">${totalSkills} Skill Signals</span>
        <span class="skills-pill">${githubCount} GitHub Imports</span>
        <span class="skills-pill">${backendSkills.length} Core Skills</span>
        <span class="skills-pill">${backendHighlights.length} Highlights</span>
      </div>
    </div>

    ${
      backendSkills.length
        ? `
          <div class="skills-group-card">
            <h3>Detected Skills</h3>
            <div class="skills-pill-row">
              ${backendSkills.map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`).join("")}
            </div>
          </div>
        `
        : `
          <div class="skills-group-card">
            <h3>Next backend improvement</h3>
            <p class="resume-summary-text">
              Replace aggregate counts with real extracted skills grouped by expertise once the API exposes skill levels.
            </p>
          </div>
        `
    }
  `;
}

function renderSkillsTimeline(timeline) {
  const container = document.getElementById("skills-timeline-container");
  if (!container) return;

  if (!timeline.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No timeline data yet</h3>
        <p class="resume-summary-text">
          Upload projects with detected skills to generate a year-by-year skills timeline.
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = timeline
    .map((entry) => {
      const skills = Array.isArray(entry.skills) ? entry.skills : [];

      return `
        <div class="timeline-year-row">
          <div class="timeline-year">${escapeHtml(entry.year)}</div>
          <div class="timeline-track">
            <div class="timeline-skill-pills">
              ${
                skills.length
                  ? skills
                      .map((skill) => {
                        const name = skill.name || skill.skill || "unknown";
                        const weight =
                          skill.weight !== undefined && skill.weight !== null
                            ? `<span class="timeline-weight">${Number(skill.weight).toFixed(1)}</span>`
                            : "";

                        return `
                          <span class="timeline-skill-pill">
                            ${escapeHtml(name)} ${weight}
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

function renderActivityHeatmap(heatmapData) {
  const container = document.getElementById("activity-heatmap-container");
  if (!container) return;

  const cells = Array.isArray(heatmapData?.cells) ? heatmapData.cells : [];
  const projectCount = Number(heatmapData?.projectCount || 0);

  if (!cells.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No activity data yet</h3>
        <p class="resume-summary-text">
          Upload projects with timeline or file activity data to generate a project activity heatmap.
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="heatmap-summary">
      <p class="resume-summary-text">
        Aggregated activity across ${projectCount} project${projectCount === 1 ? "" : "s"}.
      </p>
    </div>

    <div class="heatmap-grid">
      ${cells
        .map((cell) => {
          const period = formatPeriodLabel(cell.period);
          const count = Number(cell.count || 0);
          const bucket = getHeatmapBucket(Number(cell.intensity || 0));

          return `
            <div class="heatmap-cell bucket-${bucket}" title="${escapeHtml(period)} · ${count} activity event${count === 1 ? "" : "s"}">
              <span class="heatmap-period">${escapeHtml(period)}</span>
              <span class="heatmap-count">${count}</span>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function buildResumePreviewHtml(profile, projects, summaryData) {
  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);
  const topProjects = getTopProjects(projects);
  const projectDetailsMap = getProjectDetailsMap(summaryData);
  const backendSkills = dedupeStrings(summaryData?.skills);

  return `
    <div class="resume-preview-sheet">
      <div class="resume-preview-hero">
        <h1>${escapeHtml(profile.name)}</h1>
        <p class="resume-preview-role">${escapeHtml(profile.title)}</p>
      </div>

      <div class="resume-preview-section">
        <h3>Professional Summary</h3>
        <p>
          Computer Science student with hands-on experience building portfolio-focused software,
          working across frontend, backend, systems programming, and project analysis workflows.
          Current portfolio includes ${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"},
          ${totalFiles} analyzed file${totalFiles === 1 ? "" : "s"}, and ${totalSkills} detected skill signal${totalSkills === 1 ? "" : "s"}.
        </p>
      </div>

      <div class="resume-preview-grid">
        <div class="resume-preview-section">
          <h3>Education</h3>
          <p>${escapeHtml(profile.education)}</p>
        </div>

        <div class="resume-preview-section">
          <h3>Awards</h3>
          <ul>
            ${profile.awards.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </div>
      </div>

      ${
        backendSkills.length
          ? `
            <div class="resume-preview-section">
              <h3>Core Skills</h3>
              <p>${escapeHtml(backendSkills.join(", "))}</p>
            </div>
          `
          : ""
      }

      <div class="resume-preview-section">
        <h3>Selected Projects</h3>
        ${
          topProjects.length
            ? topProjects
                .map((project) => {
                  const details = projectDetailsMap.get(project.project_id);
                  const title = details?.title || project.project_id;
                  const summary =
                    details?.summary ||
                    `${project.total_files} files analyzed • ${project.total_skills} skill signals • ${project.is_github ? "GitHub import" : "ZIP upload"}`;

                  return `
                    <div class="resume-preview-project">
                      <div class="resume-preview-project-title">${escapeHtml(title)}</div>
                      <div class="resume-preview-project-meta">${escapeHtml(summary)}</div>
                    </div>
                  `;
                })
                .join("")
            : `<p>No projects uploaded yet.</p>`
        }
      </div>

      <div class="resume-preview-section">
        <h3>Portfolio Highlights</h3>
        <ul>
          <li>${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"} tracked in the desktop app</li>
          <li>${totalFiles} total analyzed file${totalFiles === 1 ? "" : "s"} across portfolio entries</li>
          <li>${totalSkills} total detected skill signal${totalSkills === 1 ? "" : "s"} from project analysis</li>
        </ul>
      </div>
    </div>
  `;
}

async function openResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  const body = document.getElementById("resume-preview-body");
  if (!modal || !body) return;

  body.innerHTML = `<p class="resume-summary-text">Loading resume preview...</p>`;
  modal.classList.remove("hidden");

  try {
    const [projects, summaryData] = await Promise.all([
      fetchProjects(),
      fetchPortfolioResumeSummary(),
    ]);

    const profile = buildProfile(summaryData);
    body.innerHTML = buildResumePreviewHtml(profile, projects, summaryData);
  } catch (err) {
    console.error("Failed to open resume preview:", err);
    body.innerHTML = `
      <div class="skills-group-card">
        <h3>Preview unavailable</h3>
        <p class="resume-summary-text">Unable to load live portfolio/resume data for the preview.</p>
      </div>
    `;
  }
}

function closeResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  modal?.classList.add("hidden");
}

export async function loadPortfolioResume() {
  const [projectsResult, timelineResult, summaryResult, heatmapResult] = await Promise.allSettled([
    fetchProjects(),
    fetchSkillsTimeline(),
    fetchPortfolioResumeSummary(),
    fetchActivityHeatmap(),
  ]);

  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  const timeline = timelineResult.status === "fulfilled" ? timelineResult.value : [];
  const summaryData = summaryResult.status === "fulfilled" ? summaryResult.value : null;
  const heatmapData =
    heatmapResult.status === "fulfilled"
      ? heatmapResult.value
      : { cells: [], maxCount: 0, projectCount: 0 };

  const profile = buildProfile(summaryData);

  if (projectsResult.status === "rejected") {
    console.error("Failed to load portfolio/resume project data:", projectsResult.reason);
  }

  if (timelineResult.status === "rejected") {
    console.error("Failed to load skills timeline:", timelineResult.reason);
  }

  if (summaryResult.status === "rejected") {
    console.error("Failed to load portfolio summary data:", summaryResult.reason);
  }

  if (heatmapResult.status === "rejected") {
    console.error("Failed to load activity heatmap:", heatmapResult.reason);
  }

  renderResumeSummary(profile, projects, summaryData);
  renderTopProjects(projects, summaryData);
  renderPortfolioStats(projects, summaryData);
  renderSkillsTimeline(timeline);
  renderActivityHeatmap(heatmapData);
  applyDisplayPreferences();
}

export function initPortfolioResume() {
  loadPortfolioResume();

  const refreshBtn = document.getElementById("refresh-portfolio-btn");
  refreshBtn?.addEventListener("click", loadPortfolioResume);

  const previewBtn = document.getElementById("preview-resume-btn");
  previewBtn?.addEventListener("click", openResumePreview);

  const closeBtn = document.getElementById("resume-preview-close");
  closeBtn?.addEventListener("click", closeResumePreview);

  const modal = document.getElementById("resume-preview-modal");
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeResumePreview();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeResumePreview();
    }
  });
}
