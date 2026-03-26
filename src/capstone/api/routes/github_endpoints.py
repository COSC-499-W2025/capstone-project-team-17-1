from __future__ import annotations

import json
import re
import requests
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from capstone.zip_analyzer import ZipAnalyzer
from capstone.config import Preferences
from capstone.modes import ModeResolution
from capstone.storage import open_db, save_github_token, get_github_token
import capstone.storage as storage_module
from capstone.system.cloud_storage import upload_database, upload_project_zip
from capstone.github_contributors import sync_contributor_stats

router = APIRouter(prefix="/github", tags=["github"])

GITHUB_API = "https://api.github.com"


def _patch_github_commit_dates(
    conn,
    project_id: str,
    owner: str,
    repo: str,
    branch: str,
    headers: dict,
    summary: dict,
) -> None:
    """Fetch first/last commit dates from GitHub API and update the stored snapshot.

    GitHub zipballs contain only the working tree (no .git directory), so
    ZipAnalyzer cannot extract commit timestamps.  This function patches the
    project_analysis row that was just written by the analyzer.
    """
    try:
        commits_url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"

        # Newest commit (first item, per_page=1)
        latest_res = requests.get(
            commits_url,
            headers=headers,
            params={"sha": branch, "per_page": 1},
            timeout=10,
        )
        if latest_res.status_code != 200:
            return

        latest_data = latest_res.json()
        last_commit_date: str | None = None
        first_commit_date: str | None = None

        if latest_data:
            last_commit_date = latest_data[0]["commit"]["author"]["date"]

        # Oldest commit: follow Link header rel="last" to the final page
        link_header = latest_res.headers.get("Link", "")
        last_page_url: str | None = None
        for part in link_header.split(","):
            if 'rel="last"' in part:
                m = re.search(r"<([^>]+)>", part)
                if m:
                    last_page_url = m.group(1)
                break

        if last_page_url:
            oldest_res = requests.get(last_page_url, headers=headers, timeout=10)
            if oldest_res.status_code == 200:
                oldest_data = oldest_res.json()
                if oldest_data:
                    first_commit_date = oldest_data[-1]["commit"]["author"]["date"]
        elif last_commit_date:
            # Only one page — first commit == last commit
            first_commit_date = last_commit_date

        if not first_commit_date and not last_commit_date:
            return

        # Update the snapshot row that was just inserted by ZipAnalyzer
        row = conn.execute(
            "SELECT id, snapshot FROM project_analysis WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if not row:
            return

        snap = json.loads(row[1])
        collab = snap.get("collaboration", {})
        if first_commit_date:
            collab["first_commit_date"] = first_commit_date
        if last_commit_date:
            collab["last_commit_date"] = last_commit_date
        snap["collaboration"] = collab

        # Also update the in-memory summary so the API response is consistent
        if isinstance(summary.get("collaboration"), dict):
            if first_commit_date:
                summary["collaboration"]["first_commit_date"] = first_commit_date
            if last_commit_date:
                summary["collaboration"]["last_commit_date"] = last_commit_date

        conn.execute(
            "UPDATE project_analysis SET snapshot = ? WHERE id = ?",
            (json.dumps(snap), row[0]),
        )
        conn.commit()

    except Exception:
        # Non-fatal — import succeeds even if commit-date patching fails
        pass


# ------------------------------------------------
# 1. Fetch repositories from user account
# ------------------------------------------------

@router.get("/repos")
def list_repositories():
    """
    Fetch repositories belonging to the authenticated GitHub user.
    """


    token = get_github_token()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    headers = {"Authorization": f"Bearer {token}"}

    url = f"{GITHUB_API}/user/repos"

    params = {
        "per_page": 100,
        "sort": "updated"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="GitHub authentication failed")

    repos = []

    for repo in response.json():
        repos.append({
            "name": repo["name"],
            "full_name": repo["full_name"],
            "owner": repo["owner"]["login"],
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count"),
            "updated_at": repo.get("updated_at"),
            "private": repo.get("private")
        })

    return repos


# ------------------------------------------------
# 2. Import repository from GitHub
# ------------------------------------------------

@router.post("/import")
def import_repository(
    owner: str,
    repo: str,
    project_id: str,
    branch: str = "main"
):
    """
    Downloads a GitHub repository as a zip archive and runs the ZipAnalyzer.
    """
    token = get_github_token()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    headers = {"Authorization": f"Bearer {token}"}

    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"

    response = requests.get(zip_url, headers=headers, stream=True)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to download repository")

    with tempfile.TemporaryDirectory() as tmpdir:

        zip_path = Path(tmpdir) / f"{repo}.zip"

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        analyzer = ZipAnalyzer()

        # Default preferences
        preferences = Preferences()

        # Default mode resolution
        mode = ModeResolution(
            requested="local",
            resolved="local",
            reason="GitHub import"
        )

        metadata_path = Path("data") / f"{project_id}_metadata.jsonl"
        summary_path = Path("data") / f"{project_id}_summary.json"
        conn = open_db()

        try:
            summary = analyzer.analyze(
                zip_path=zip_path,
                metadata_path=metadata_path,
                summary_path=summary_path,
                mode=mode,
                preferences=preferences,
                project_id=project_id,
                conn=conn,
                skip_contributor_storage=True,
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO github_projects
                (project_id, owner, repo, branch)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, owner, repo, branch)
            )
            conn.commit()

            # Patch snapshot with real commit dates from GitHub API.
            # GitHub zipballs have no .git directory, so ZipAnalyzer cannot
            # extract timestamps from git log — we fetch them here instead.
            _patch_github_commit_dates(conn, project_id, owner, repo, branch, headers, summary)

            # Sync full contributor stats (commits, PRs, issues, reviews) via GitHub API.
            # This enriches the contributor_stats table so resume generation can show
            # PR/issue/review breakdowns instead of git-log-only commit counts.
            try:
                repo_url = f"https://github.com/{owner}/{repo}"
                sync_contributor_stats(
                    repo_url=repo_url,
                    token=token,
                    project_id=project_id,
                )
            except Exception:
                pass  # non-fatal — resume will fall back to git-log commit data
            if storage_module.CURRENT_USER:
                upload_project_zip(
                    storage_module.CURRENT_USER,
                    project_id,
                    zip_path,
                    zip_path.name,
                )
                upload_database(storage_module.CURRENT_USER)
        finally:
            conn.close()

        repo_url = f"https://github.com/{owner}/{repo}"

        return {
            "status": "imported",
            "project_id": project_id,
            "repository": repo_url,
            "summary": summary
        }


# ------------------------------------------------
# 3. Pull latest version of repository
# ------------------------------------------------

@router.post("/pull")
def pull_repository(project_id: str):

    token = get_github_token()
    if not token:
        raise HTTPException(401, "GitHub token not configured")

    headers = {"Authorization": f"Bearer {token}"}

    conn = open_db()

    row = conn.execute(
        "SELECT owner, repo, branch FROM github_projects WHERE project_id=?",
        (project_id,)
    ).fetchone()

    if not row:
        raise HTTPException(404, "Project is not a GitHub project")

    owner, repo, branch = row

    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"

    response = requests.get(zip_url, headers=headers, stream=True)

    if response.status_code != 200:
        raise HTTPException(400, "Failed to pull repository")

    with tempfile.TemporaryDirectory() as tmpdir:

        zip_path = Path(tmpdir) / f"{repo}.zip"

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)

        analyzer = ZipAnalyzer()

        summary = analyzer.analyze(
            zip_path=zip_path,
            metadata_path=Path("data") / f"{project_id}_metadata.jsonl",
            summary_path=Path("data") / f"{project_id}_summary.json",
            mode=ModeResolution(requested="local", resolved="local", reason="git pull"),
            preferences=Preferences(),
            project_id=project_id,
            skip_contributor_storage=True,
        )

        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            sync_contributor_stats(
                repo_url=repo_url,
                token=token,
                project_id=project_id,
            )
        except Exception:
            pass  # non-fatal

        if storage_module.CURRENT_USER:
            upload_project_zip(
                storage_module.CURRENT_USER,
                project_id,
                zip_path,
                zip_path.name,
            )
            upload_database(storage_module.CURRENT_USER)

    conn.close()

    return {"status": "updated", "summary": summary}


# ------------------------------------------------
# 3. check login state
# ------------------------------------------------


@router.get("/auth-status")
def github_auth_status():
    token = get_github_token()

    if not token:
        return {"authenticated": False}

    return {"authenticated": True}

@router.post("/login")
def github_login(token: str):
    save_github_token(token)

    if storage_module.CURRENT_USER:
        upload_database(storage_module.CURRENT_USER)

    return {
        "status": "authenticated"
    }

# ------------------------------------------------
# 3. fetch branch
# ------------------------------------------------


@router.get("/branches")
def get_branches(owner: str, repo: str):
    token = get_github_token()

    headers = {"Authorization": f"Bearer {token}"}

    branches = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100&page={page}"
        response = requests.get(url, headers=headers)

        data = response.json()

        if not data:
            break

        branches.extend([b["name"] for b in data])
        page += 1

    if response.status_code != 200:
        raise HTTPException(400, "Failed to fetch branches")


    return {"branches": branches}