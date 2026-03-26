import { openProgressModal, setProgress, closeProgressModal } from "./progressModal.js";
import { renderRepoCards, renderGithubLogin } from "./uploadModal.js";
import { loadProjects } from "./projects.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { notifyPortfolioDataUpdated } from "./portfolioState.js";
async function checkGithubAuth() {
    const res = await fetch("http://127.0.0.1:8002/github/auth-status")
    const data = await res.json()
    return data.authenticated
}

export async function loadGithubRepos() {
    const res = await fetch("http://127.0.0.1:8002/github/repos")
    const repos = await res.json()

    renderRepoCards(repos)
}

async function startGithubImport(owner, repo, projectId, branch) {

  const url =
  `http://127.0.0.1:8002/github/import?owner=${owner}&repo=${repo}&project_id=${projectId}&branch=${branch}`;

  const res = await fetch(url, {
    method: "POST"
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "GitHub import failed");
  }

  return res.json();
}


export function setUploadTab(tabName) {
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

 export async function startImport(owner, name, projectId, branch) {

  document.getElementById("upload-modal")?.remove();

  openProgressModal(`Importing ${owner}/${name} (${branch})...`);

  try {

    await startGithubImport(owner, name, projectId, branch);

    // Cloud sync is a follow-up step. If it fails, keep the import successful locally.
    try {
      await fetch("http://127.0.0.1:8002/cloud/db/upload", {
        method: "POST"
      });
    } catch (syncError) {
      console.warn("Cloud sync after GitHub import failed:", syncError);
    }

    setProgress(100, "Done. Refreshing projects...");

    setTimeout(() => {

  closeProgressModal();

  loadProjects();
  loadRecentProjects();
  loadProjectHealth();
  loadErrorAnalysis();
  notifyPortfolioDataUpdated();

}, 600);

  } catch (e) {
    console.error("GitHub import failed:", e);
    closeProgressModal();
    alert(`GitHub import failed: ${e.message || e}`);
  }

}
