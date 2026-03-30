import { fetchProjects } from "./projects.js";
import { API_BASE } from "./config.js";
function getStaticProfile() {
  return {
    name: "Raunak Khanna",
    title: "Computer Science Student",
    education: "UBC Okanagan — BSc Computer Science",
    awards: ["Capstone Team Contributor"],
  };
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

function isDisplayableTimelineSkill(skill) {
  const rawName = String(skill?.name || skill?.skill || "").trim().toLowerCase();
  return Boolean(rawName) && rawName !== "0";
}

function renderResumeSummary(profile, projects) {
  const container = document.getElementById("resume-summary-container");
  if (!container) return;

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);

  const summary =
    totalProjects > 0
      ? `Built a portfolio with ${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"}, covering ${totalFiles} analyzed file${totalFiles === 1 ? "" : "s"} and ${totalSkills} detected skill signal${totalSkills === 1 ? "" : "s"}.`
      : "Upload projects to generate a one-page resume summary and portfolio showcase.";

  container.innerHTML = `
    <div class="resume-summary-card">
      <div class="resume-summary-top">
        <div>
          <h3>${profile.name}</h3>
          <p class="resume-role">${profile.title}</p>
        </div>
      </div>

      <p class="resume-summary-text">${summary}</p>

      <div class="resume-meta-grid">
        <div class="resume-meta-box">
          <span class="resume-meta-label">Education</span>
          <span class="resume-meta-value">${profile.education}</span>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Awards</span>
          <ul class="resume-awards-list">
            ${profile.awards.map(item => `<li>${item}</li>`).join("")}
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
    </div>
  `;
}

function renderTopProjects(projects) {
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

  const topProjects = getTopProjects(projects);

  container.innerHTML = topProjects
    .map(
      (project, index) => `
        <div class="top-project-card">
          <div class="top-project-rank">#${index + 1}</div>
          <div class="top-project-body">
            <h3>${project.project_id}</h3>
            <p>
              ${project.total_files} file${project.total_files === 1 ? "" : "s"} analyzed •
              ${project.total_skills} detected skill signal${project.total_skills === 1 ? "" : "s"}
            </p>
            <div class="project-stack">
              <span class="stack-pill">${project.is_github ? "GitHub Import" : "ZIP Upload"}</span>
              <span class="stack-pill">${project.total_files} Files</span>
              <span class="stack-pill">${project.total_skills} Skills</span>
            </div>
          </div>
        </div>
      `
    )
    .join("");
}

function renderPortfolioStats(projects) {
  const container = document.getElementById("skills-expertise-container");
  if (!container) return;

  if (!projects.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No skill breakdown yet</h3>
        <p class="resume-summary-text">
          The current API only returns total skill counts, not skill names or expertise levels.
          This section can be upgraded once a skill-detail endpoint is available.
        </p>
      </div>
    `;
    return;
  }

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);
  const githubCount = projects.filter(p => p.is_github).length;

  container.innerHTML = `
    <div class="skills-group-card">
      <h3>Portfolio Stats</h3>
      <div class="skills-pill-row">
        <span class="skills-pill">${totalProjects} Projects</span>
        <span class="skills-pill">${totalFiles} Files</span>
        <span class="skills-pill">${totalSkills} Skill Signals</span>
        <span class="skills-pill">${githubCount} GitHub Imports</span>
      </div>
    </div>

    <div class="skills-group-card">
      <h3>Next backend improvement</h3>
      <p class="resume-summary-text">
        Replace aggregate counts with real extracted skills grouped by expertise once the API exposes skill names.
      </p>
    </div>
  `;
}

function renderSkillsTimeline(timeline) {
  const container = document.getElementById("skills-timeline-container");
  if (!container) return;

  const visibleTimeline = timeline.filter((entry) => {
    const skills = Array.isArray(entry?.skills) ? entry.skills.filter(isDisplayableTimelineSkill) : [];
    const metrics = entry?.project_metrics && typeof entry.project_metrics === "object"
      ? entry.project_metrics
      : {};
    return skills.length > 0 || Number(metrics.file_count || 0) > 0 || Number(metrics.active_days || 0) > 0;
  });

  if (!visibleTimeline.length) {
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

  container.innerHTML = visibleTimeline
    .map((entry) => {
      const skills = Array.isArray(entry.skills) ? entry.skills.filter(isDisplayableTimelineSkill) : [];

      return `
        <div class="timeline-year-row">
          <div class="timeline-year">${entry.year}</div>
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
                            ${name} ${weight}
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

function buildResumePreviewHtml(profile, projects) {
  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);
  const topProjects = getTopProjects(projects);

  return `
    <div class="resume-preview-sheet">
      <div class="resume-preview-hero">
        <h1>${profile.name}</h1>
        <p class="resume-preview-role">${profile.title}</p>
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
          <p>${profile.education}</p>
        </div>

        <div class="resume-preview-section">
          <h3>Awards</h3>
          <ul>
            ${profile.awards.map(item => `<li>${item}</li>`).join("")}
          </ul>
        </div>
      </div>

      <div class="resume-preview-section">
        <h3>Selected Projects</h3>
        ${
          topProjects.length
            ? topProjects
                .map(
                  project => `
                    <div class="resume-preview-project">
                      <div class="resume-preview-project-title">${project.project_id}</div>
                      <div class="resume-preview-project-meta">
                        ${project.total_files} files analyzed • ${project.total_skills} skill signals • ${project.is_github ? "GitHub import" : "ZIP upload"}
                      </div>
                    </div>
                  `
                )
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

  const profile = getStaticProfile();

  body.innerHTML = `<p class="resume-summary-text">Loading resume preview...</p>`;
  modal.classList.remove("hidden");

  try {
    const projects = await fetchProjects();
    body.innerHTML = buildResumePreviewHtml(profile, projects);
  } catch (err) {
    console.error("Failed to open resume preview:", err);
    body.innerHTML = `
      <div class="skills-group-card">
        <h3>Preview unavailable</h3>
        <p class="resume-summary-text">Unable to load live project data for the resume preview.</p>
      </div>
    `;
  }
}

function closeResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  modal?.classList.add("hidden");
}

export async function loadPortfolioResume() {
  const profile = getStaticProfile();

  const [projectsResult, timelineResult] = await Promise.allSettled([
    fetchProjects(),
    fetchSkillsTimeline(),
  ]);

  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  const timeline = timelineResult.status === "fulfilled" ? timelineResult.value : [];

  if (projectsResult.status === "rejected") {
    console.error("Failed to load portfolio/resume project data:", projectsResult.reason);
  }

  if (timelineResult.status === "rejected") {
    console.error("Failed to load skills timeline:", timelineResult.reason);
  }

  renderResumeSummary(profile, projects);
  renderTopProjects(projects);
  renderPortfolioStats(projects);
  renderSkillsTimeline(timeline);
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
