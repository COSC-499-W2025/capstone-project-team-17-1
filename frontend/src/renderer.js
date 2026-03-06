const toggle = document.querySelector(".theme-toggle")
const cpuFill = document.getElementById("cpu-fill");
const memoryFill = document.getElementById("memory-fill");
const gpuFill = document.getElementById("gpu-fill");
const uploadBtn = document.getElementById("upload-project-btn");
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
uploadBtn?.addEventListener("click", openUploadModal);
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

async function loadRecentProjects() {
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

async function loadErrorAnalysis() {
  const container = document.getElementById("error-analysis-container");
  if (!container) return;

  container.innerHTML = `
    <div class="error-loading">
      Loading analysis...
    </div>
  `;

  try {
    const res = await fetch("http://127.0.0.1:8002/errors");
    const data = await res.json();

    container.innerHTML = "";

    // -----------------------------
    // CONSENT REQUIRED
    // -----------------------------
    if (data.status === "consent_required") {
      container.innerHTML = `
        <div class="error-empty-state">
          <p>AI analysis is disabled.</p>
          <button id="enable-ai-btn" class="ai-consent-btn">
            Enable AI Analysis
          </button>
        </div>
      `;

      document.getElementById("enable-ai-btn")?.addEventListener("click", async () => {
        await fetch("http://127.0.0.1:8002/privacy-consent/external", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ consent: true })
        });

        loadErrorAnalysis();
      });

      return;
    }

    // -----------------------------
    // NO PROJECTS
    // -----------------------------
    if (data.status === "no_projects") {
      container.innerHTML = `
        <div class="error-empty-state">
          <h3>No projects found 📁</h3>
          <p>Upload a project to enable AI error analysis.</p>
        </div>
      `;
      return;
    }

    // -----------------------------
    // NEVER ANALYZED
    // -----------------------------
    if (data.status === "not_analyzed") {
      container.innerHTML = `
        <div class="error-healthy-state">
          <p>No AI analysis has been run yet.</p>
          <button id="run-analysis-btn" class="ai-consent-btn">
            Run AI Analysis
          </button>
        </div>
      `;

      document.getElementById("run-analysis-btn")?.addEventListener("click", async () => {
        container.innerHTML = `
          <div class="error-loading">
            Running AI analysis...
          </div>
        `;

        await fetch("http://127.0.0.1:8002/errors/analyze", {
          method: "POST"
        });

        // Wait briefly to avoid race condition
        setTimeout(loadErrorAnalysis, 500);
      });

      return;
    }

    // -----------------------------
// ANALYZED (CLEAN OR WITH ERRORS)
// -----------------------------
if (data.status === "ok") {

  // Header bar with re-run button
  const headerBar = document.createElement("div");
  headerBar.className = "error-header-bar";
  headerBar.innerHTML = `
    <button id="rerun-analysis-btn" class="ai-consent-btn small">
      Re-run
    </button>
  `;
  container.appendChild(headerBar);

  document.getElementById("rerun-analysis-btn")?.addEventListener("click", async () => {
    container.innerHTML = `
      <div class="error-loading">
        Running AI analysis...
      </div>
    `;

    await fetch("http://127.0.0.1:8002/errors/analyze", { method: "POST" });

    setTimeout(loadErrorAnalysis, 500);
  });

  // No issues found
  if (!data.errors || data.errors.length === 0) {
    const healthyBox = document.createElement("div");
    healthyBox.className = "error-healthy-state";
    healthyBox.innerHTML = `
      ✓ No issues found. Projects look healthy.
    `;
    container.appendChild(healthyBox);
    return;
  }

  // Render actual errors
  data.errors.forEach(error => {
    const box = document.createElement("div");
    box.className = "error-item";

    box.innerHTML = `
      <div class="error-header">
        <div class="severity-circle ${error.severity}"></div>
        <div class="error-title">${error.title}</div>
      </div>

      <div class="error-project">Project: ${error.project_id}</div>
      <div class="error-detail">${error.detail}</div>

      <div class="error-actions">
        <button class="fix-btn">Fix Issue</button>
      </div>
    `;

    // Fake fix button behavior (future hook)
    box.querySelector(".fix-btn")?.addEventListener("click", () => {
      alert(`Opening fix flow for "${error.title}" 🚀`);
    });

    container.appendChild(box);
  });

  return;
}

    // -----------------------------
    // FALLBACK
    // -----------------------------
    container.innerHTML = `
      <div class="error-empty-state">
        Unexpected response from server.
      </div>
    `;

  } catch (err) {
    container.innerHTML = `
      <div class="error-empty-state">
        Failed to load error analysis.
      </div>
    `;
    console.error("Error loading analysis:", err);
  }
}

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

async function loadProjectHealth() {
  const container = document.getElementById("project-health-container");
  if (!container) return;

  container.innerHTML = `
    <div class="error-loading">
      Loading project health...
    </div>
  `;

  try {
    const res = await fetch("http://127.0.0.1:8002/analytics/project-health");
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

function switchPage(targetId) {
  const pages = document.querySelectorAll(".page");

  pages.forEach(page => {
    page.classList.remove("active");
  });

  const target = document.getElementById(targetId);
  if (target) {
    target.classList.add("active");
  }

  
}

function renderProjects(projects) {
  const container = document.getElementById("projects-list");
  container.innerHTML = "";

  if (!projects.length) {
    container.innerHTML = "<p>No projects uploaded yet.</p>";
    return;
  }

  projects.forEach(project => {
    const card = document.createElement("div");
    card.className = "project-card";

    card.innerHTML = `
      <h3>${project.name}</h3>
      <p>Files: ${project.files}</p>
      <button class="view-btn">View</button>
    `;

    container.appendChild(card);
  });
}

// -----------------------------
// GitHub upload modal helpers
// -----------------------------

function setUploadTab(tabName) {
  const tabs = document.querySelectorAll(".upload-tab");
  const sections = document.querySelectorAll(".upload-section");

  tabs.forEach(t => t.classList.remove("active"));
  sections.forEach(s => s.classList.remove("active"));

  document.querySelector(`.upload-tab[data-tab="${tabName}"]`)?.classList.add("active");
  document.querySelector(`.upload-section[data-section="${tabName}"]`)?.classList.add("active");

  if (tabName === "github") {
    initGithubSection();
  }
}

async function initGithubSection() {
  const githubContainer = document.getElementById("github-section-body");
  if (!githubContainer) return;

  githubContainer.innerHTML = `
    <div class="github-loading">Checking GitHub login...</div>
  `;

  let authed = false;
  try {
    authed = await checkGithubAuth();
  } catch (e) {
    githubContainer.innerHTML = `
      <div class="github-empty">
        Failed to reach backend.
      </div>
    `;
    return;
  }

  if (!authed) {
    renderGithubLogin(githubContainer);
    return;
  }

  githubContainer.innerHTML = `
    <div class="github-loading">Loading repositories...</div>
  `;

  try {
    const res = await fetch("http://127.0.0.1:8002/github/repos");
    const repos = await res.json();
    renderRepoCards(repos);
  } catch (e) {
    githubContainer.innerHTML = `
      <div class="github-empty">
        Failed to load repositories.
      </div>
    `;
  }
}

function renderGithubLogin(container) {
  container.innerHTML = `
    <div class="github-login">
      <div class="github-login-title">GitHub sign in</div>
      <div class="github-login-sub">
        Paste your GitHub token once and we will remember it.
      </div>

      <button id="github-open-token" class="primary-btn github-login-btn">
        Get Token
      </button>

      <input id="github-token-input" class="github-token-input" placeholder="Paste GitHub token here" />

      <button id="github-save-token" class="primary-btn github-login-btn">
        Save Token
      </button>

      <div class="github-login-hint">
        Tip: This is a classic personal access token.
      </div>
    </div>
  `;

  document.getElementById("github-open-token")?.addEventListener("click", () => {
    window.open("https://github.com/settings/tokens", "_blank");
  });

  document.getElementById("github-save-token")?.addEventListener("click", async () => {
    const token = document.getElementById("github-token-input")?.value?.trim();

    if (!token) {
      alert("Please paste a token.");
      return;
    }

    const res = await fetch(`http://127.0.0.1:8002/github/login?token=${encodeURIComponent(token)}`, {
  method: "POST"
});

    if (!res.ok) {
      alert("Login failed.");
      return;
    }

    initGithubSection();
  });
}

async function startImport(owner, name, projectId, branch) {

  document.getElementById("upload-modal")?.remove();

  openProgressModal(`Importing ${owner}/${name} (${branch})...`);

  try {

    await startGithubImport(owner, name, projectId, branch);

    setProgress(100, "Done. Refreshing projects...");

    setTimeout(() => {
      closeProgressModal();
      loadProjects();
    }, 600);

  } catch (e) {
    closeProgressModal();
    alert("GitHub import failed.");
  }

}

function renderRepoCards(repos) {
  const githubContainer = document.getElementById("github-section-body");
  if (!githubContainer) return;

  if (!repos || repos.length === 0) {
    githubContainer.innerHTML = `
      <div class="github-empty">
        No repositories found.
      </div>
    `;
    return;
  }

  githubContainer.innerHTML = `
    <div class="github-repo-toolbar">
      <input id="github-repo-search" class="github-search" placeholder="Search repos..." />
    </div>
    <div id="github-repo-list" class="github-repo-list"></div>
  `;

  const list = document.getElementById("github-repo-list");

  function draw(filtered) {
    list.innerHTML = "";

    filtered.forEach(repo => {
      const card = document.createElement("div");
      card.className = "github-repo-card";

      const updated = repo.updated_at
        ? new Date(repo.updated_at).toLocaleString()
        : "Unknown";

      card.innerHTML = `
        <div class="github-repo-top">
          <div class="github-repo-name">${repo.full_name || repo.name}</div>
          <div class="github-repo-updated">${updated}</div>
        </div>

        <div class="github-repo-desc">
          ${repo.description ? repo.description : "No description"}
        </div>

        <div class="github-repo-bottom">
          <div class="github-repo-meta">
            <span>${repo.language || "Unknown"}</span>
            <span>★ ${repo.stars ?? 0}</span>
          </div>

          <button class="github-upload-btn">
            Upload
          </button>
        </div>
      `;

      const uploadBtn = card.querySelector(".github-upload-btn");

      uploadBtn?.addEventListener("click", async () => {

        const owner = repo.owner || (repo.full_name ? repo.full_name.split("/")[0] : "");
        const name = repo.name || (repo.full_name ? repo.full_name.split("/")[1] : "");

        if (!owner || !name) {
          alert("Could not determine repo owner and name.");
          return;
        }

        let projectId = document
          .getElementById("github-project-id-input")
          ?.value
          ?.trim();

        if (!projectId) {
          projectId = name;
        }

        // -------------------------
        // FETCH BRANCHES
        // -------------------------
        let branches = [];

        try {
          const res = await fetch(
            `http://127.0.0.1:8002/github/branches?owner=${owner}&repo=${name}`
          );

          const data = await res.json();
          branches = data.branches || [];
          console.log("Branches received:", branches);

        } catch (err) {
          alert("Failed to fetch branches");
          return;
        }

        let selectedBranch = branches[0] || "main";

if (branches.length > 1) {

  const branchList = branches
    .map(b => `<option value="${b}">${b}</option>`)
    .join("");

  const modal = document.createElement("div");
  modal.className = "branch-modal";

  modal.innerHTML = `
    <div class="branch-modal-box">
      <h3>Select Branch</h3>

      <select id="branch-select">
        ${branchList}
      </select>

      <div class="branch-modal-buttons">
        <button id="branch-confirm">Import</button>
        <button id="branch-cancel">Cancel</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  document.getElementById("branch-confirm").onclick = async () => {

    selectedBranch =
      document.getElementById("branch-select").value || branches[0];

    modal.remove();

    startImport(owner, name, projectId, selectedBranch);

  };

  document.getElementById("branch-cancel").onclick = () => {
    modal.remove();
  };

  return;
}

startImport(owner, name, projectId, selectedBranch);


      });

      list.appendChild(card);
    });
  }

  draw(repos);

  document.getElementById("github-repo-search")?.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();

    const filtered = repos.filter(r => {
      const name = (r.full_name || r.name || "").toLowerCase();
      const desc = (r.description || "").toLowerCase();
      return name.includes(q) || desc.includes(q);
    });

    draw(filtered);
  });
}


// -----------------------------
// Progress modal
// -----------------------------

let progressTimer = null;

function openProgressModal(initialText) {
  const existing = document.getElementById("progress-modal");
  if (existing) return;

  const modal = document.createElement("div");
  modal.id = "progress-modal";
  modal.innerHTML = `
    <div class="upload-overlay">
      <div class="progress-window">
        <div class="progress-title">Importing Project</div>
        <div id="progress-text" class="progress-text">${initialText || "Working..."}</div>

        <div class="progress-bar">
          <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
        </div>

        <div id="progress-percent" class="progress-percent">0%</div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  let p = 0;
  progressTimer = setInterval(() => {
    p = Math.min(90, p + 3);
    setProgress(p, document.getElementById("progress-text")?.textContent || "Working...");
  }, 250);
}

function setProgress(percent, text) {
  const fill = document.getElementById("progress-fill");
  const label = document.getElementById("progress-percent");
  const t = document.getElementById("progress-text");

  if (fill) fill.style.width = `${percent}%`;
  if (label) label.textContent = `${percent}%`;
  if (t && text) t.textContent = text;
}

function closeProgressModal() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  document.getElementById("progress-modal")?.remove();
}

function openUploadModal() {
  const existing = document.getElementById("upload-modal");
  if (existing) return;

  const modal = document.createElement("div");
  modal.id = "upload-modal";
  modal.innerHTML = `
    <div class="upload-overlay">
      <div class="upload-window">

        <div class="upload-header">
          <h2>Upload Project</h2>
          <button id="close-upload">✕</button>
        </div>

        <div class="upload-tabs">
          <button class="upload-tab active" data-tab="manual">Manual ZIP</button>
          <button class="upload-tab" data-tab="github">GitHub</button>
        </div>

        <div class="upload-content">

          <div class="upload-section active" data-section="manual">
            <input type="text" id="project-id-input" placeholder="Project ID (optional)" />

            <label class="file-upload-wrapper">
              <input type="file" id="zip-input" accept=".zip" />
              <span class="file-upload-btn">Choose ZIP File</span>
              <span class="file-upload-name">No file chosen</span>
            </label>

            <button id="submit-upload" class="primary-btn">
              Upload ZIP
            </button>
          </div>

          <div class="upload-section" data-section="github">
            <input type="text" id="github-project-id-input" placeholder="Project ID" />
            <div id="github-section-body" class="github-section-body"></div>
          </div>

        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  document.getElementById("close-upload").onclick = () => modal.remove();

  document.querySelectorAll(".upload-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      setUploadTab(btn.dataset.tab);
    });
  });

  const zipInput = document.getElementById("zip-input");
  const fileNameDisplay = document.querySelector(".file-upload-name");

  zipInput?.addEventListener("change", () => {
    if (zipInput.files && zipInput.files.length > 0) {
      fileNameDisplay.textContent = zipInput.files[0].name;
    } else {
      fileNameDisplay.textContent = "No file chosen";
    }
  });

  document.getElementById("submit-upload").onclick = submitZipUpload;
}

async function submitZipUpload() {
  const projectId = document.getElementById("project-id-input").value.trim();
  const fileInput = document.getElementById("zip-input");
  const file = fileInput.files[0];

  if (!projectId || !file) {
    alert("Please provide project ID and ZIP file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const url = `http://127.0.0.1:8002/projects/upload?project_id=${encodeURIComponent(projectId)}`;

  console.log("Sending project_id:", projectId, "URL:", url);

  const res = await fetch(url, {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "Upload failed.");
    return;
  }

  document.getElementById("upload-modal")?.remove();
  loadProjects();
}

async function loadProjects() {
  try {
    const res = await fetch("http://127.0.0.1:8002/dashboard/recent-projects");
    const projects = await res.json();

    const container = document.getElementById("projects-list");
    container.innerHTML = "";

    if (!projects.length) {
      container.innerHTML = "<p>No projects uploaded yet.</p>";
      return;
    }

    projects.forEach(project => {
      const card = document.createElement("div");
      card.className = "project-card";
let pullButton = "";

if (project.is_github) {
  pullButton = `<button class="pull-btn" data-project="${project.project_id}">Pull</button>`;
}
      card.innerHTML = `
  <div class="project-delete" data-id="${project.project_id}">
    <svg viewBox="0 0 24 24" width="18" height="18">
      <path fill="currentColor"
      d="M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9z"/>
    </svg>
  </div>

  <h3>${project.project_id}</h3>
  <p>Files: ${project.total_files}</p>
  <p>Skills: ${project.total_skills}</p>
  <div class="project-actions">
    <button class="view-btn">View Project</button>
     ${pullButton}
  </div>
`;

const deleteBtn = card.querySelector(".project-delete");

deleteBtn?.addEventListener("click", async (e) => {

  e.stopPropagation();

  const projectId = deleteBtn.dataset.id;

  if (!confirm(`Delete project "${projectId}"?`)) return;

  try {

    await fetch(`http://127.0.0.1:8002/projects/${projectId}`, {
      method: "DELETE"
    });

    loadProjects();
    loadRecentProjects(); // also refresh dashboard widget if it is visible

  } catch (err) {
    alert("Failed to delete project.");
  }
  card.classList.add("removing");
setTimeout(() => loadProjects(), 200);
});

const pullBtn = card.querySelector(".pull-btn");

pullBtn?.addEventListener("click", async (e) => {
  e.stopPropagation();

  const projectId = pullBtn.dataset.project;

  try {
    pullBtn.innerText = "Pulling...";

    const res = await fetch(`http://127.0.0.1:8002/github/pull?project_id=${encodeURIComponent(projectId)}`, {
      method: "POST"
    });

    if (!res.ok) throw new Error("Pull failed");

    pullBtn.innerText = "Updated ✓";
    loadProjects();
    loadRecentProjects();

  } catch (err) {
    console.error("Pull failed:", err);
    pullBtn.innerText = "Failed";
  }

  setTimeout(() => {
    pullBtn.innerText = "Pull";
  }, 2000);
});



      container.appendChild(card);
    });

  } catch (err) {
    console.error("Failed to load projects:", err);
  }
}



document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.dataset.page;
      if (target) switchPage(target);
    });
  });
});

document.addEventListener("DOMContentLoaded", loadErrorAnalysis);
document.addEventListener("DOMContentLoaded", loadRecentProjects);
document.addEventListener("DOMContentLoaded", loadProjectHealth);

loadProjects();
loadRecentActivity();
setInterval(loadRecentActivity, 1000);
//setInterval(loadProjectHealth, 1000);
//setInterval(loadRecentProjects, 1000);
//setInterval(loadErrorAnalysis, 1000);