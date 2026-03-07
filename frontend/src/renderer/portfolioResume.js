function getMockPortfolioData() {
    return {
      profile: {
        name: "Raunak Khanna",
        title: "Computer Science Student",
        summary:
          "Focused on software engineering, systems programming, and data-driven applications with strong interest in portfolio-quality project work.",
        education: "UBC Okanagan — BSc Computer Science",
        awards: ["Dean's List Candidate", "Capstone Team Contributor"],
      },
      topProjects: [
        {
          name: "Capstone Desktop App",
          impact: "Built user-facing frontend features for dashboard and project workflows.",
          stack: ["Electron", "JavaScript", "Python"],
        },
        {
          name: "Operating Systems Labs",
          impact: "Implemented multithreading, synchronization, and systems-level debugging tasks.",
          stack: ["C", "POSIX Threads", "Linux"],
        },
        {
          name: "Portfolio / Resume Generator",
          impact: "Designed experience summaries, skills grouping, and project showcase UI.",
          stack: ["Electron", "HTML", "CSS", "JavaScript"],
        },
      ],
      skills: {
        Advanced: ["Python", "JavaScript", "Git", "HTML/CSS"],
        Intermediate: ["FastAPI", "Electron", "SQL", "C"],
        Familiar: ["Docker", "Chart.js", "Linux Systems"],
      },
    };
  }
  
  function renderResumeSummary(profile) {
    const container = document.getElementById("resume-summary-container");
    if (!container) return;
  
    container.innerHTML = `
      <div class="resume-summary-card">
        <div class="resume-summary-top">
          <div>
            <h3>${profile.name}</h3>
            <p class="resume-role">${profile.title}</p>
          </div>
        </div>
  
        <p class="resume-summary-text">${profile.summary}</p>
  
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
        </div>
      </div>
    `;
  }
  
  function renderTopProjects(projects) {
    const container = document.getElementById("top-projects-container");
    if (!container) return;
  
    container.innerHTML = projects
      .map(
        (project, index) => `
          <div class="top-project-card">
            <div class="top-project-rank">#${index + 1}</div>
            <div class="top-project-body">
              <h3>${project.name}</h3>
              <p>${project.impact}</p>
              <div class="project-stack">
                ${project.stack.map(skill => `<span class="stack-pill">${skill}</span>`).join("")}
              </div>
            </div>
          </div>
        `
      )
      .join("");
  }
  
  function renderSkillsByExpertise(skills) {
    const container = document.getElementById("skills-expertise-container");
    if (!container) return;
  
    container.innerHTML = Object.entries(skills)
      .map(
        ([level, items]) => `
          <div class="skills-group-card">
            <h3>${level}</h3>
            <div class="skills-pill-row">
              ${items.map(item => `<span class="skills-pill">${item}</span>`).join("")}
            </div>
          </div>
        `
      )
      .join("");
  }
  
  export function loadPortfolioResume() {
    const data = getMockPortfolioData();
  
    renderResumeSummary(data.profile);
    renderTopProjects(data.topProjects);
    renderSkillsByExpertise(data.skills);
  }
  
  export function initPortfolioResume() {
    loadPortfolioResume();
  
    const refreshBtn = document.getElementById("refresh-portfolio-btn");
    refreshBtn?.addEventListener("click", loadPortfolioResume);
  }