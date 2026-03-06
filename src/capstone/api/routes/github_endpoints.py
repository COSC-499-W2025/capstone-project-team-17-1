from __future__ import annotations

import requests
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from capstone.zip_analyzer import ZipAnalyzer
from capstone.config import Preferences
from capstone.modes import ModeResolution
from capstone.storage import open_db, save_github_token, get_github_token


router = APIRouter(prefix="/github", tags=["github"])

GITHUB_API = "https://api.github.com"


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
                conn=conn
            )
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

@router.post("/github/pull")
def pull_repository(project_id: str, owner: str, repo: str, branch: str):

    token = get_github_token()
    headers = {"Authorization": f"Bearer {token}"}

    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"

    response = requests.get(zip_url, headers=headers, stream=True)

    if response.status_code != 200:
        raise HTTPException(400, "Failed to pull repository")

    with tempfile.TemporaryDirectory() as tmpdir:

        zip_path = Path(tmpdir) / f"{repo}.zip"

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)

        analyzer = ZipAnalyzer()

        summary = analyzer.analyze(
            zip_path=zip_path,
            metadata_path=Path("data") / f"{project_id}_metadata.jsonl",
            summary_path=Path("data") / f"{project_id}_summary.json",
            mode=ModeResolution(requested="local", resolved="local", reason="git pull"),
            preferences=Preferences(),
            project_id=project_id
        )

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