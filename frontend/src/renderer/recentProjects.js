import { openProjectViewer } from "./projectViewer.js";
import { authFetch, captureAuthDataEpoch, authDomWriteAllowed } from "./auth.js";

export async function loadRecentProjects() {
  const epoch = captureAuthDataEpoch();
  try {
    const res = await authFetch("/dashboard/recent-projects");
    if (!res.ok) {
      throw new Error(`Failed to load recent projects: ${res.status}`);
    }
    const projects = await res.json();

    const container = document.getElementById("recent-projects-container");
    if (!container) return;

    if (!authDomWriteAllowed(epoch)) return;

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

      const viewBtn = card.querySelector(".project-button");
      viewBtn?.addEventListener("click", (e) => {
        e.stopPropagation();
        openProjectViewer(project.project_id);
      });

      container.appendChild(card);
    });

  } catch (err) {
    console.error("Failed to load recent projects:", err);
  }
}