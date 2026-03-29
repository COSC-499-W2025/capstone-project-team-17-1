import {
  isPrivateMode,
  authFetch,
  hasAuthToken,
  captureAuthDataEpoch,
  authDomWriteAllowed,
  getAuthToken,
} from "./auth.js";
import { isPrivateMode } from "./auth.js";

const SKILLS_CHART_MODE_KEY = "loom_dashboard_skills_chart_mode";
const SKILL_CHART_MODES = ["bar", "pie", "donut", "radar"];
const SKILL_COLORS = ["#38bdf8", "#22c55e", "#f59e0b", "#f97316", "#a78bfa"];

let skillsChart = null;

export async function loadMostUsedSkills() {

  const container = document.getElementById("most-used-skills");
  if (!container) return;

  console.log("Loading most used skills...");
  let result = await window.skillsAPI.loadMostUsedSkills();

  if (isPrivateMode() && (!result || result.empty)) {
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

  const topSkills = result.skills.slice(0, 5);

  function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function getLabels() {
    return topSkills.map((skill) => capitalize(skill.skill));
  }

  function getValues() {
    return topSkills.map((skill) =>
      Number((skill.confidence * 100).toFixed(1))
    );
  }

  function getChartMode() {
    const saved = localStorage.getItem(SKILLS_CHART_MODE_KEY);
    return SKILL_CHART_MODES.includes(saved) ? saved : "bar";
  }

  function saveChartMode(mode) {
    localStorage.setItem(
      SKILLS_CHART_MODE_KEY,
      SKILL_CHART_MODES.includes(mode) ? mode : "bar"
    );
  }

  function destroyChart() {
    if (skillsChart) {
      skillsChart.destroy();
      skillsChart = null;
    }
  }

  function renderViewToggle(activeMode) {
    return `
      <div class="skills-view-toggle" role="tablist" aria-label="Most used skills chart type">
        ${SKILL_CHART_MODES.map(
          (mode) => `
          <button
            type="button"
            class="skills-view-btn ${activeMode === mode ? "active" : ""}"
            data-skills-view="${mode}"
          >
            ${capitalize(mode)}
          </button>
        `
        ).join("")}
      </div>
    `;
  }

  function renderLegend() {
    return topSkills
      .map(
        (skill, index) => `
        <div class="skills-pie-legend-row">
          <div class="skills-pie-legend-left">
            <span
              class="skills-pie-legend-swatch"
              style="background: ${SKILL_COLORS[index % SKILL_COLORS.length]};"
            ></span>
            <span class="skills-pie-legend-name">${capitalize(skill.skill)}</span>
          </div>
          <span class="skills-pie-legend-meta">${(
            skill.confidence * 100
          ).toFixed(1)}%</span>
        </div>
      `
      )
      .join("");
  }

  function renderBarView() {
    container.innerHTML = `
      <div class="skills-header-row">
        <h3 class="skills-title">Most Used Skills</h3>
        ${renderViewToggle("bar")}
      </div>
      <div class="skills-wrapper">
        ${topSkills
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
              <div class="skill-right-modern"></div>
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
      bar.style.width = bar.dataset.width;
    });
  }

  function renderCircularView(mode = "pie") {
    container.innerHTML = `
      <div class="skills-header-row">
        <h3 class="skills-title">Most Used Skills</h3>
        ${renderViewToggle(mode)}
      </div>
      <div class="skills-pie-layout">
        <div class="skills-pie-canvas-wrap">
          <canvas id="most-used-skills-chart"></canvas>
        </div>
        <div class="skills-pie-legend">
          ${renderLegend()}
        </div>
      </div>
    `;

    const canvas = container.querySelector("#most-used-skills-chart");
    if (!canvas || !window.Chart) return;

    skillsChart = new window.Chart(canvas, {
      type: mode === "donut" ? "doughnut" : "pie",
      data: {
        labels: getLabels(),
        datasets: [
          {
            data: getValues(),
            backgroundColor: SKILL_COLORS,
            borderColor: "#0f172a",
            borderWidth: 2,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: mode === "donut" ? "58%" : 0,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label(context) {
                return `${context.label}: ${context.parsed.toFixed(1)}%`;
              },
            },
          },
        },
      },
    });
  }

  function renderRadarView() {
    container.innerHTML = `
      <div class="skills-header-row">
        <h3 class="skills-title">Most Used Skills</h3>
        ${renderViewToggle("radar")}
      </div>
      <div class="skills-pie-layout">
        <div class="skills-pie-canvas-wrap">
          <canvas id="most-used-skills-chart"></canvas>
        </div>
        <div class="skills-pie-legend">
          ${renderLegend()}
        </div>
      </div>
    `;

    const canvas = container.querySelector("#most-used-skills-chart");
    if (!canvas || !window.Chart) return;

    const values = getValues();
    const maxValue = Math.max(...values, 20);
    const suggestedMax = Math.ceil(maxValue / 5) * 5;

    skillsChart = new window.Chart(canvas, {
      type: "radar",
      data: {
        labels: getLabels(),
        datasets: [
          {
            label: "Skill share %",
            data: values,
            backgroundColor: "rgba(56, 189, 248, 0.18)",
            borderColor: "#38bdf8",
            borderWidth: 2,
            pointBackgroundColor: SKILL_COLORS,
            pointBorderColor: "#0f172a",
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: true,
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
          tooltip: {
            callbacks: {
              label(context) {
                return `${context.label}: ${context.raw.toFixed(1)}%`;
              },
            },
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            suggestedMax,
            ticks: {
              display: false,
              backdropColor: "transparent",
            },
            angleLines: {
              color: "rgba(255, 255, 255, 0.12)",
            },
            grid: {
              color: "rgba(255, 255, 255, 0.12)",
            },
            pointLabels: {
              color: "rgba(255, 255, 255, 0.9)",
              font: {
                size: 12,
              },
            },
          },
        },
      },
    });
  }

  function bindViewToggle() {
    container.querySelectorAll("[data-skills-view]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextMode = button.dataset.skillsView || "bar";
        if (nextMode === getChartMode()) return;
        saveChartMode(nextMode);
        renderCurrentView();
      });
    });
  }

  function renderCurrentView() {
    destroyChart();

    switch (getChartMode()) {
      case "pie":
        renderCircularView("pie");
        break;
      case "donut":
        renderCircularView("donut");
        break;
      case "radar":
        renderRadarView();
        break;
      case "bar":
      default:
        renderBarView();
        break;
    }

    bindViewToggle();
  }

  renderCurrentView();
}

async function buildPrivateTimelineSkills() {
  try {
    const res = await fetch("http://127.0.0.1:8002/skills/timeline");
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
        const name = String(skill?.skill || skill?.name || "")
          .trim()
          .toLowerCase();
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

    const totalWeight =
      [...totals.values()].reduce((sum, value) => sum + value, 0) || 1;

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