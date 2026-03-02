const toggle = document.querySelector(".theme-toggle")
const cpuFill = document.getElementById("cpu-fill");
const memoryFill = document.getElementById("memory-fill");
const gpuFill = document.getElementById("gpu-fill");

const cpuValue = document.getElementById("cpu-value");
const memoryValue = document.getElementById("memory-value");
const gpuValue = document.getElementById("gpu-value");
const gpuLabel = document.getElementById("gpu-label");
const fakeProjects = [
{ name: "Loom Analyzer", skills: ["Python", "Flask", "SQLite"] },
{ name: "Portfolio Builder", skills: ["React", "Node", "SQLite"] },
{ name: "Job Matcher", skills: ["Python", "FastAPI", "Docker"] },
{ name: "Dashboard UI", skills: ["React", "CSS", "Electron"] }
];
const ctx = document.getElementById("cpu-chart").getContext("2d");
let cpuHistory = [];
let memoryHistory = [];
let gpuHistory = [];
function createMiniChart(ctx, color) {
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: color,
        borderWidth: 2, // 🔥 thicker stroke
        tension: 0.4,
        fill: false,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { display: false, min: 0, max: 100 }
      }
    }
  });
}

const cpuChart = createMiniChart(
  document.getElementById("cpu-chart").getContext("2d"),
  "#4da6ff"
);

const memoryChart = createMiniChart(
  document.getElementById("memory-chart").getContext("2d"),
  "#00ff88"
);

const gpuChart = createMiniChart(
  document.getElementById("gpu-chart").getContext("2d"),
  "#ffcc00"
);

toggle.addEventListener("click", () => {
  document.body.classList.toggle("light")
  document.body.classList.toggle("dark")
})

document.getElementById("close").addEventListener("click", () => window.api.close())
document.getElementById("minimize").addEventListener("click", () => window.api.minimize())
document.getElementById("maximize").addEventListener("click", () => window.api.maximize())

function updateArc(element, value) {
  const circumference = 126;
  const offset = circumference - (value / 100) * circumference;

  element.style.strokeDashoffset = offset;

  // 🔥 dynamic color
  element.style.stroke = getUsageColor(value);
}

function getUsageColor(value) {
  const clamp = Math.max(0, Math.min(100, value));

  let r, g;

  if (clamp <= 50) {
    // Green → Yellow
    const ratio = clamp / 50;
    r = Math.floor(0 + ratio * 255);
    g = 255;
  } else {
    // Yellow → Red
    const ratio = (clamp - 50) / 50;
    r = 255;
    g = Math.floor(255 - ratio * 255);
  }

  return `rgb(${r}, ${g}, 0)`;
}

async function fetchMetrics() {
  const metricsRes = await fetch("http://127.0.0.1:8002/system/system-metrics");
  const metrics = await metricsRes.json();

  const healthRes = await fetch("http://127.0.0.1:8002/health");
  const health = await healthRes.json();

  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("system-status");

  if (health.status === "ok") {
    statusDot.className = "status-dot active";
    statusText.innerText = "System Running";
  } else {
    statusDot.className = "status-dot inactive";
    statusText.innerText = "System Offline";
  }

  updateArc(document.getElementById("cpu-arc"), metrics.cpu.usage);
  updateArc(document.getElementById("memory-arc"), metrics.memory.usage);

  if (metrics.gpu.detected) {
  const gpuUsage = metrics.gpu.usage || 0;

  updateArc(document.getElementById("gpu-arc"), gpuUsage);

  document.getElementById("gpu-label").innerText = "GPU";

  // 🔥 ADD THIS
  document.getElementById("gpu-value").innerText =
    Math.round(gpuUsage) + "%";

  document.getElementById("gpu-temp").innerText =
    metrics.gpu.temperature ? metrics.gpu.temperature + "°C" : "--°C";

} else {
  const storageUsage = metrics.storage.usage || 0;

  updateArc(document.getElementById("gpu-arc"), storageUsage);

  document.getElementById("gpu-label").innerText = "Storage";

  // 🔥 ALSO ADD THIS
  document.getElementById("gpu-value").innerText =
    Math.round(storageUsage) + "%";

  document.getElementById("gpu-temp").innerText = "";
}

  document.getElementById("cpu-value").innerText =
    Math.round(metrics.cpu.usage) + "%";

  document.getElementById("cpu-temp").innerText =
    metrics.cpu.temperature ? metrics.cpu.temperature + "°C" : "--°C";

  document.getElementById("memory-value").innerText =
    Math.round(metrics.memory.usage) + "%";

  cpuHistory.push(metrics.cpu.usage || 0);
memoryHistory.push(metrics.memory.usage || 0);
gpuHistory.push(
  metrics.gpu && metrics.gpu.detected
    ? metrics.gpu.usage || 0
    : metrics.storage.usage || 0
);

if (cpuHistory.length > 40) {
  cpuHistory.shift();
  memoryHistory.shift();
  gpuHistory.shift();
}

function updateMiniChart(chart, data) {
  chart.data.labels = data.map((_, i) => i);
  chart.data.datasets[0].data = data;
  chart.update();
}

updateMiniChart(cpuChart, cpuHistory);
updateMiniChart(memoryChart, memoryHistory);
updateMiniChart(gpuChart, gpuHistory);
}

setInterval(fetchMetrics, 1000);
fetchMetrics();

// renderer.js

document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("most-used-skills");
  if (!container) return;
  console.log("Loading most used skills...");
  const result = await window.skillsAPI.loadMostUsedSkills();
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
  container.innerHTML = `
  <h3 class="skills-title">Most Used Skills</h3>
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
            ${capitalize(skill.topProject)}
          </div>

        </div>
      `
      )
      .join("")}
  </div>
`;

// FORCE reflow before animating
const bars = document.querySelectorAll(".skill-bar-fill-modern");

// Step 1: ensure width is 0
bars.forEach(bar => {
  bar.style.width = "0%";
});

// Step 2: force browser to commit layout
void document.body.offsetHeight;

// Step 3: animate to final width
bars.forEach(bar => {
  const targetWidth = bar.dataset.width;
  bar.style.width = targetWidth;
});

});
function renderActivity(logs) {
  const container = document.getElementById("recent-activity");

  const isNearBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 50;

  container.innerHTML = logs.map(log => {
    const level = (log.level || "info").toLowerCase();

    return `
      <div class="activity-line level-${level}">
        <span class="activity-timestamp">${log.timestamp}</span>
        <span class="activity-tag">[${log.level}]</span>
        ${log.message}
      </div>
    `;
  }).join("");

  if (isNearBottom) {
    container.scrollTop = container.scrollHeight;
  }
}
async function loadRecentActivity() {
  const container = document.getElementById("recent-activity");
  if (!container) return;

  try {
    const res = await fetch("http://127.0.0.1:8002/activity");
    const result = await res.json();

    const logs = result.logs || [];

    if (logs.length === 0) {
      container.innerHTML = `<div class="activity-line">No recent activity.</div>`;
      return;
    }

    renderActivity(logs);

  } catch (err) {
    console.error("Activity fetch failed:", err);
  }
}

loadRecentActivity();
setInterval(loadRecentActivity, 1000);