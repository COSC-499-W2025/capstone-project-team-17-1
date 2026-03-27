import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { openProjectViewer } from "./projectViewer.js";
import { notifyPortfolioDataUpdated } from "./portfolioState.js";
import { authFetch, hasAuthToken } from "./auth.js";

export async function fetchProjects() {
  const res = await fetch("http://127.0.0.1:8002/dashboard/recent-projects");

  if (!res.ok) {
    throw new Error(`Failed to fetch projects: ${res.status}`);
  }

  const projects = await res.json();
  return Array.isArray(projects) ? projects : [];
}

export async function loadProjects() {
  try {
    const projects = await fetchProjects();
    const container = document.getElementById("projects-list");

    if (!container) return;

    container.innerHTML = "";

    if (!projects.length) {
      container.innerHTML = "<p>No projects uploaded yet.</p>";
      return;
    }

    projects.forEach((project) => {
      const card = document.createElement("div");
      card.className = "project-card";

      let pullButton = "";

      if (project.is_github) {
        pullButton = `
          <button class="pull-btn" data-project="${project.project_id}">
            Pull
          </button>
        `;
      }

      const isCollaborative = (project.contributor_count || 0) > 1;
      const classLabel = isCollaborative ? "Collaborative" : "Individual";
      const classClass = isCollaborative ? "badge-collaborative" : "badge-individual";

      card.innerHTML = `
        <div class="project-delete" data-id="${project.project_id}">
          <svg viewBox="0 0 24 24" width="18" height="18">
            <path
              fill="currentColor"
              d="M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9z"
            />
          </svg>
        </div>

        <h3>${project.project_id}</h3>
        <p>Files: ${project.total_files} · Skills: ${project.total_skills}</p>
        <span class="project-classification-badge ${classClass}">${classLabel}</span>

        <div class="project-actions">
          <button class="view-btn">View Project</button>
          ${pullButton}
        </div>
      `;

      const deleteBtn = card.querySelector(".project-delete");
      const pullBtn = card.querySelector(".pull-btn");

      deleteBtn?.addEventListener("click", async (e) => {
        e.stopPropagation();

        const projectId = deleteBtn.dataset.id;
        if (!projectId) return;

        if (!confirm(`Delete project "${projectId}"?`)) return;

        try {
          const res = await fetch(`http://127.0.0.1:8002/projects/${encodeURIComponent(projectId)}`, {
            method: "DELETE",
          });

          if (!res.ok && res.status !== 404) {
            throw new Error(`Delete failed: ${res.status}`);
          }

          card.classList.add("removing");
          notifyPortfolioDataUpdated();

          await Promise.all([
            loadProjects(),
            typeof loadRecentProjects === "function" ? loadRecentProjects() : Promise.resolve(),
            typeof loadProjectHealth === "function" ? loadProjectHealth() : Promise.resolve(),
            typeof loadErrorAnalysis === "function" ? loadErrorAnalysis() : Promise.resolve(),
          ]);
        } catch (err) {
          console.error("Delete failed:", err);
          alert("Failed to delete project.");
        }
      });

      pullBtn?.addEventListener("click", async (e) => {
        e.stopPropagation();

        const projectId = pullBtn.dataset.project;

        try {
          pullBtn.innerText = "Pulling...";
          pullBtn.disabled = true;

          const res = await fetch(
            `http://127.0.0.1:8002/github/pull?project_id=${encodeURIComponent(projectId)}`,
            { method: "POST" }
          );

          if (!res.ok) {
            throw new Error("Pull failed");
          }

          if (hasAuthToken()) {
            await authFetch("/cloud/db/upload", { method: "POST" });
          }

          pullBtn.innerText = "Updated ✓";

          await loadProjects();

          if (typeof loadRecentProjects === "function") await loadRecentProjects();
          if (typeof loadProjectHealth === "function") await loadProjectHealth();
          if (typeof loadErrorAnalysis === "function") await loadErrorAnalysis();
          notifyPortfolioDataUpdated();
        } catch (err) {
          console.error("Pull failed:", err);
          pullBtn.innerText = "Pull";
          pullBtn.disabled = false;
        }
      });

      const viewBtn = card.querySelector(".view-btn");
      viewBtn?.addEventListener("click", (e) => {
        e.stopPropagation();
        openProjectViewer(project.project_id);
      });

      container.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load projects:", err);

    const container = document.getElementById("projects-list");
    if (container) {
      container.innerHTML = "<p>Failed to load projects.</p>";
    }
  }
}
