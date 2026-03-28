import { authFetch } from "./auth.js";

function getHealthColor(score) {
  const clamp = Math.max(0, Math.min(100, score));

  let r, g;

  if (clamp <= 50) {
    const ratio = clamp / 50;
    r = Math.floor(255);
    g = Math.floor(ratio * 255);
  } else {
    const ratio = (clamp - 50) / 50;
    r = Math.floor(255 - ratio * 255);
    g = 255;
  }

  return `rgb(${r}, ${g}, 0)`;
}

function getHealthEmoji(score) {
  if (score >= 70) return "😌";
  if (score >= 40) return "😐";
  return "😞";
}

export async function loadProjectHealth() {
  const container = document.getElementById("project-health-container");
  if (!container) return;

  container.innerHTML = `
    <div class="error-loading">
      Loading project health...
    </div>
  `;

  try {
    const res = await authFetch("/analytics/project-health");
    const projects = await res.json();

    container.innerHTML = "";

    if (!projects || projects.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          No project health data available.
        </div>
      `;
      return;
    }

    projects.forEach(project => {
      const card = document.createElement("div");
      card.className = "health-mini-card";

      const color = getHealthColor(project.score);
      const emoji = getHealthEmoji(project.score);

      card.innerHTML = `
        <div class="health-score" style="color: ${color}">
          ${project.score}%
        </div>

        <div class="health-emoji">
          ${emoji}
        </div>

        <div class="health-project">
          ${project.project_id}
        </div>

        <div class="health-stats">
          <span>Errors: ${project.errors}</span>
          <span>Warnings: ${project.warnings}</span>
        </div>
      `;

      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = `
      <div class="error-empty-state">
        Failed to load project health.
      </div>
    `;
    console.error("Health fetch failed:", err);
  }
}