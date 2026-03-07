import { fetchProjects } from "./projects.js";

function getStaticProfile() {
  return {
    name: "Raunak Khanna",
    title: "Computer Science Student",
    education: "UBC Okanagan — BSc Computer Science",
    awards: ["Capstone Team Contributor"],
  };
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
      : "Upload projects to generate a stronger one-page resume summary and portfolio showcase.";

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

  const topProjects = [...projects]
    .sort((a, b) => {
      const skillDiff = (b.total_skills || 0) - (a.total_skills || 0);
      if (skillDiff !== 0) return skillDiff;
      return (b.total_files || 0) - (a.total_files || 0);
    })
    .slice(0, 3);

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

export async function loadPortfolioResume() {
  const profile = getStaticProfile();

  try {
    const projects = await fetchProjects();
    renderResumeSummary(profile, projects);
    renderTopProjects(projects);
    renderPortfolioStats(projects);
  } catch (err) {
    console.error("Failed to load portfolio/resume data:", err);

    renderResumeSummary(profile, []);
    renderTopProjects([]);
    renderPortfolioStats([]);
  }
}

export function initPortfolioResume() {
  loadPortfolioResume();

  const refreshBtn = document.getElementById("refresh-portfolio-btn");
  refreshBtn?.addEventListener("click", loadPortfolioResume);
}