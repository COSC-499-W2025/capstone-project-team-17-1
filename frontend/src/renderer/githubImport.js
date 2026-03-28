import { openProgressModal, setProgress, closeProgressModal } from "./progressModal.js";
import { renderRepoCards, renderGithubLogin } from "./uploadModal.js";
import { loadProjects } from "./projects.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { notifyPortfolioDataUpdated } from "./portfolioState.js";
import { authFetch, hasAuthToken } from "./auth.js";
async function checkGithubAuth() {
    const res = await authFetch("/github/auth-status")
    const data = await res.json()
    return data.authenticated
}

export async function loadGithubRepos() {
    const res = await authFetch("/github/repos")
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || `Failed to fetch GitHub repos (${res.status})`);
    }
    const repos = await res.json()
    console.log("Fetched repos:", Array.isArray(repos) ? repos.length : 0);
    console.log("Repo names:", Array.isArray(repos) ? repos.map((r) => r.full_name) : []);

    renderRepoCards(repos)
}

async function startGithubImport(owner, repo, projectId, branch) {
  const url =
  `/github/import?owner=${owner}&repo=${repo}&project_id=${projectId}&branch=${branch}`;

  const res = await authFetch(url, {
    method: "POST"
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "GitHub import failed");
  }

  return res.json();
}

async function runGitAnalysis(projectId, repoFullName) {
  if (!projectId) return null;
  if (repoFullName) {
    console.log("Running git analysis for:", repoFullName);
  }
  try {
    const res = await authFetch(`/github/pull?project_id=${encodeURIComponent(projectId)}&refresh=true`, {
      method: "POST",
    });
    if (!res.ok) return null;
    return res.json();
  } catch (_) {
    return null;
  }
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
    const res = await authFetch("/github/repos");
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || `Failed to fetch GitHub repos (${res.status})`);
    }
    const repos = await res.json();
    console.log("Fetched repos:", Array.isArray(repos) ? repos.length : 0);
    console.log("Repo names:", Array.isArray(repos) ? repos.map((r) => r.full_name) : []);
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

    const payload = await startGithubImport(owner, name, projectId, branch);
    const project = payload?.summary || {};
    console.log("Git project flag:", Boolean(project?.is_git_project));
    console.log("Collaboration snapshot:", project?.collaboration || null);
    if (project?.is_git_project) {
      await runGitAnalysis(projectId, project?.repo_full_name);
    }

    // Cloud sync is a follow-up step. If it fails, keep the import successful locally.
    try {
      if (hasAuthToken()) {
        await authFetch("/cloud/db/upload", { method: "POST" });
      }
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
