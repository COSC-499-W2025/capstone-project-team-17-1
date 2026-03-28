import { isPrivateMode } from "./auth.js";
import { authFetch } from "./auth.js";

const SKILLS_CHART_MODE_KEY = "loom_dashboard_skills_chart_mode";
let skillsChart = null;

export async function loadMostUsedSkills() {

  const container = document.getElementById("most-used-skills");
  if (!container) return;

  console.log("Loading most used skills...");
  let result = await window.skillsAPI.loadMostUsedSkills();

  const hasToken = Boolean(localStorage.getItem("loom_auth_token"));
  if ((isPrivateMode() || hasToken) && (!result || result.empty)) {
    result = await buildPrivateTimelineSkills();
  }

  console.log("Skills result:", result);

  if (!result || result.empty) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>Hmm... 🤔</h3>
        <p>Looks like there are no projects to show yet.</p>
        <p>It's a little quiet in here... maybe upload something awesome? 😌</p>
      </div>
    `;
    return;
  }

  function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function getChartMode() {
    const saved = localStorage.getItem(SKILLS_CHART_MODE_KEY);
    return saved === "pie" ? "pie" : "bar";
  }

  function saveChartMode(mode) {
    localStorage.setItem(SKILLS_CHART_MODE_KEY, mode === "pie" ? "pie" : "bar");
  }

  function destroyChart() {
    if (skillsChart) {
      skillsChart.destroy();
      skillsChart = null;
    }
  }

  function renderBarView() {
    container.innerHTML = `
      <div class="skills-header-row">
        <h3 class="skills-title">Most Used Skills</h3>
        <div class="skills-view-toggle" role="tablist" aria-label="Most used skills chart type">
          <button type="button" class="skills-view-btn active" data-skills-view="bar">Bar</button>
          <button type="button" class="skills-view-btn" data-skills-view="pie">Pie</button>
        </div>
      </div>
      <div class="skills-wrapper">
        ${result.skills
          .slice(0, 5)
          .map(
            (skill) => `
            <div class="skill-row-modern">
              <div class="skill-left-modern">
                ${capitalize(skill.skill)}
              </div>
              <div class="skill-middle-modern">
                <div class="skill-bar-modern">
                  <div 
                    class="skill-bar-fill-modern"
                    data-width="${(skill.confidence * 100).toFixed(1)}%"
                    style="width: 0%"
                  ></div>
                </div>
                <span class="skill-percentage-modern">
                  ${(skill.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div class="skill-right-modern">
                
              </div>
            </div>
          `
          )
          .join("")}
      </div>
    `;

    const bars = container.querySelectorAll(".skill-bar-fill-modern");
    bars.forEach((bar) => {
      bar.style.width = "0%";
    });

    void document.body.offsetHeight;

    bars.forEach((bar) => {
      const targetWidth = bar.dataset.width;
      bar.style.width = targetWidth;
    });
  }

  function renderPieView() {
    container.innerHTML = `
      <div class="skills-header-row">
        <h3 class="skills-title">Most Used Skills</h3>
        <div class="skills-view-toggle" role="tablist" aria-label="Most used skills chart type">
          <button type="button" class="skills-view-btn" data-skills-view="bar">Bar</button>
          <button type="button" class="skills-view-btn active" data-skills-view="pie">Pie</button>
        </div>
      </div>
      <div class="skills-pie-layout">
        <div class="skills-pie-canvas-wrap">
          <canvas id="most-used-skills-pie"></canvas>
        </div>
        <div class="skills-pie-legend">
          ${result.skills.slice(0, 5).map((skill) => `
            <div class="skills-pie-legend-row">
              <span class="skills-pie-legend-name">${capitalize(skill.skill)}</span>
              <span class="skills-pie-legend-meta">${(skill.confidence * 100).toFixed(1)}%</span>
            </div>
          `).join("")}
        </div>
      </div>
    `;

    const canvas = container.querySelector("#most-used-skills-pie");
    if (canvas && window.Chart) {
      skillsChart = new window.Chart(canvas, {
        type: "pie",
        data: {
          labels: result.skills.slice(0, 5).map((skill) => capitalize(skill.skill)),
          datasets: [
            {
              data: result.skills.slice(0, 5).map((skill) => Number((skill.confidence * 100).toFixed(1))),
              backgroundColor: ["#38bdf8", "#22c55e", "#f59e0b", "#f97316", "#a78bfa"],
              borderColor: "#0f172a",
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false,
            },
          },
        },
      });
    }
  }

  function bindViewToggle() {
    container.querySelectorAll("[data-skills-view]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextMode = button.dataset.skillsView === "pie" ? "pie" : "bar";
        if (nextMode === getChartMode()) return;
        saveChartMode(nextMode);
        renderCurrentView();
      });
    });
  }

  function renderCurrentView() {
    destroyChart();
    if (getChartMode() === "pie") {
      renderPieView();
    } else {
      renderBarView();
    }
    bindViewToggle();
  }

  renderCurrentView();

}

async function buildPrivateTimelineSkills() {
  try {
    const res = await authFetch("/skills/timeline");
    if (!res.ok) {
      return { empty: true };
    }

    const payload = await res.json();
    const timeline = Array.isArray(payload.timeline) ? payload.timeline : [];
    if (!timeline.length) {
      return { empty: true };
    }

    const totals = new Map();
    const topProjects = new Map();

    timeline.forEach((entry) => {
      const projectId = entry?.project_id || "-";
      const skills = Array.isArray(entry?.skills) ? entry.skills : [];

      skills.forEach((skill) => {
        const name = String(skill?.skill || skill?.name || "").trim().toLowerCase();
        if (!name) return;

        const weight = Number(skill?.weight ?? skill?.score ?? 1) || 1;
        totals.set(name, (totals.get(name) || 0) + weight);

        const currentTop = topProjects.get(name);
        if (!currentTop || weight > currentTop.weight) {
          topProjects.set(name, { projectId, weight });
        }
      });
    });

    if (!totals.size) {
      return { empty: true };
    }

    const totalWeight = [...totals.values()].reduce((sum, value) => sum + value, 0) || 1;
    const skills = [...totals.entries()]
      .map(([skill, weight]) => ({
        skill,
        confidence: weight / totalWeight,
        topProject: topProjects.get(skill)?.projectId || "-",
      }))
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5);

    return skills.length ? { empty: false, skills } : { empty: true };
  } catch (err) {
    console.error("Failed to build private timeline skills:", err);
    return { empty: true };
  }
}
