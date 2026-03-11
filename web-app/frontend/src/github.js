async function checkGithubAuth() {
    const res = await fetch("http://127.0.0.1:8002/github/auth-status")
    const data = await res.json()
    return data.authenticated
}

async function loadGithubRepos() {
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