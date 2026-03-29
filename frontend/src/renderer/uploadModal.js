import {setUploadTab, startImport} from "./githubImport.js";
import { openProjectViewer } from "./projectViewer.js";
import { notifyPortfolioDataUpdated } from "./portfolioState.js";
import { loadProjects } from "./projects.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { loadMostUsedSkills } from "./skills.js";
import { authFetch } from "./auth.js";

export function openUploadModal() {
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

  if (!file) {
    alert("Please choose a ZIP file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  const url = `/projects/upload${query}`;

  console.log("Sending project_id:", projectId, "URL:", url);

  try {
    const res = await authFetch(url, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed: ${res.status}`);
    }

    document.getElementById("upload-modal")?.remove();
    await Promise.all([
      loadProjects(),
      loadRecentProjects(),
      loadProjectHealth(),
      loadErrorAnalysis(),
      loadMostUsedSkills(),
    ]);
    notifyPortfolioDataUpdated();
  } catch (err) {
    console.error("ZIP upload failed:", err);
    alert(err.message || "Upload failed.");
  }
}

export function renderGithubLogin(container) {
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

  const res = await authFetch(`/github/login?token=${encodeURIComponent(token)}`, {
    method: "POST"
  });

  if (!res.ok) {
    alert("Login failed.");
    return;
  }

  setUploadTab("github");
});
}

export function renderRepoCards(repos) {
  const githubContainer = document.getElementById("github-section-body");
  if (!githubContainer) return;
  console.log("Processed repos:", Array.isArray(repos) ? repos.length : 0);
  if (Array.isArray(repos)) {
    console.log("Processed repo names:", repos.map((r) => r.full_name || r.name));
  }

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

  function draw(filtered) {
    const list = githubContainer.querySelector("#github-repo-list");
    if (!list) return;
    list.innerHTML = "";
    console.log("Final rendered repos:", Array.isArray(filtered) ? filtered.length : 0);

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

        const customProjectId = document
          .getElementById("github-project-id-input")
          ?.value
          ?.trim();

        // -------------------------
        // FETCH BRANCHES
        // -------------------------
        let branches = [];

        try {
          const ownerQ = encodeURIComponent(owner);
          const repoQ = encodeURIComponent(name);
          const res = await authFetch(
            `/github/branches?owner=${ownerQ}&repo=${repoQ}`
          );

          const data = await res.json();
          branches = data.branches || [];
          console.log("Branches received:", branches);

        } catch (err) {
          alert("Failed to fetch branches");
          return;
        }

        let selectedBranch = branches[0] || "main";
        const buildProjectId = (branchName) => {
          if (customProjectId) return customProjectId;
          const safeBranch = String(branchName || "main")
            .trim()
            .replace(/[^a-zA-Z0-9._-]+/g, "-");
          return `${name}-${safeBranch}`;
        };

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

    startImport(owner, name, buildProjectId(selectedBranch), selectedBranch);

  };

  document.getElementById("branch-cancel").onclick = () => {
    modal.remove();
  };

  return;
}

startImport(owner, name, buildProjectId(selectedBranch), selectedBranch);


      });

      list.appendChild(card);
    });
  }

  draw(repos);

  githubContainer.querySelector("#github-repo-search")?.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();

    const filtered = repos.filter(r => {
      const name = (r.full_name || r.name || "").toLowerCase();
      const desc = (r.description || "").toLowerCase();
      return name.includes(q) || desc.includes(q);
    });

    draw(filtered);
  });
}
