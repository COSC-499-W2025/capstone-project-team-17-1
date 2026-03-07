export async function loadRecentProjects() {
  try {
    const res = await fetch("http://127.0.0.1:8002/dashboard/recent-projects");
    const projects = await res.json();

    const container = document.getElementById("recent-projects-container");
    container.innerHTML = "";

    projects.slice(0, 5).forEach(project => {
      const card = document.createElement("div");
      card.className = "recent-project-item";

      card.innerHTML = `
        <div class="project-header">
          <span class="project-id">${project.project_id}</span>
          <span class="project-date">${new Date(project.created_at).toLocaleString()}</span>
        </div>

        <div class="project-meta">
          <span>Files: ${project.total_files}</span>
          <span>Skills: ${project.total_skills}</span>
          <span>Type: ${project.classification}</span>
        </div>

        <button class="project-button">View Project</button>
      `;

      container.appendChild(card);
    });

  } catch (err) {
    console.error("Failed to load recent projects:", err);
  }
}