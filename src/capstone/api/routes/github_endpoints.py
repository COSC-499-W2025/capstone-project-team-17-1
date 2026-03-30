from __future__ import annotations

import json
import re
import requests
import tempfile
from urllib.parse import quote
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from capstone.zip_analyzer import ZipAnalyzer
from capstone.config import Preferences
from capstone.modes import ModeResolution
from capstone.storage import open_db, save_github_token, get_github_token, fetch_latest_snapshot, store_analysis_snapshot, upsert_project
import capstone.storage as storage_module
from capstone.system.cloud_storage import upload_database, upload_project_zip
from capstone.github_contributors import sync_contributor_stats

router = APIRouter(prefix="/github", tags=["github"])

GITHUB_API = "https://api.github.com"


class GithubTokenUpdate(BaseModel):
    token: str = Field(..., min_length=1)


def mask_github_token_for_display(token: str) -> str:
    """Non-reversible UI hint (never log or return the raw token)."""
    t = (token or "").strip()
    if not t:
        return ""
    suffix = t[-4:] if len(t) >= 4 else t
    return f"{'\N{BULLET}' * 8}{suffix}"


def _verify_github_token_remote(token: str) -> tuple[bool, str | None, dict | None]:
    """Validate token via GitHub API; never log the token."""
    try:
        res = requests.get(
            f"{GITHUB_API}/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            return True, None, data if isinstance(data, dict) else None
        if res.status_code == 401:
            return False, "Invalid or expired GitHub token", None
        return False, "GitHub could not validate this token", None
    except requests.RequestException:
        return False, "Could not reach GitHub to validate the token", None


def _apply_github_token_update(raw_token: str) -> dict:
    token = (raw_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    if len(token) < 8:
        raise HTTPException(status_code=400, detail="Token is too short")

    ok, err, user = _verify_github_token_remote(token)
    if not ok:
        raise HTTPException(status_code=400, detail=err or "Invalid GitHub token")

    save_github_token(token)
    active_user = storage_module.get_current_user()
    if _is_cloud_sync_user(active_user):
        try:
            upload_database(active_user)
        except Exception:
            pass

    login = (user or {}).get("login")
    return {
        "masked_token": mask_github_token_for_display(token),
        "github_login": str(login).strip() if login else None,
    }


def _is_cloud_sync_user(username: str | None) -> bool:
    lowered = (username or "").strip().lower()
    return bool(lowered and lowered not in {"guest", "guestuser"})


def _fetch_latest_commit_sha(owner: str, repo: str, branch: str, headers: dict) -> str | None:
    try:
        commits_url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
        latest_res = requests.get(
            commits_url,
            headers=headers,
            params={"sha": branch, "per_page": 1},
            timeout=10,
        )
        if latest_res.status_code != 200:
            return None
        latest_data = latest_res.json()
        if not latest_data:
            return None
        return str(latest_data[0].get("sha") or "").strip() or None
    except Exception:
        return None


def _github_get(url: str, headers: dict, params: dict | None = None, timeout: int = 15):
    return requests.get(url, headers=headers, params=params, timeout=timeout)


def _list_user_repos(headers: dict) -> tuple[list[dict], dict]:
    """List repos for the authenticated user via GET /user/repos (paginated).

    Do not rely on affiliation-only filtering; org/classroom repos are merged
    separately from GET /orgs/{org}/repos.
    """
    repos: list[dict] = []
    page = 1
    pages = 0
    last_headers = {}
    while True:
        response = _github_get(
            f"{GITHUB_API}/user/repos",
            headers=headers,
            params={
                "per_page": 100,
                "sort": "updated",
                "page": page,
            },
            timeout=15,
        )
        last_headers = dict(response.headers or {})
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="GitHub authentication failed")
        batch = response.json()
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        pages += 1
        page += 1
    return repos, {
        "pages": pages,
        "oauth_scopes": last_headers.get("X-OAuth-Scopes", ""),
        "accepted_scopes": last_headers.get("X-Accepted-OAuth-Scopes", ""),
    }


def _list_user_orgs(headers: dict) -> list[str]:
    orgs: list[str] = []
    page = 1
    while True:
        response = _github_get(
            f"{GITHUB_API}/user/orgs",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=15,
        )
        if response.status_code != 200:
            # Token may not permit org listing; treat as soft failure.
            return orgs
        batch = response.json()
        if not isinstance(batch, list) or not batch:
            break
        for org in batch:
            login = str((org or {}).get("login") or "").strip()
            if login:
                orgs.append(login)
        page += 1
    return orgs


def _list_org_repos(org_login: str, headers: dict) -> tuple[list[dict], str | None]:
    """GET /orgs/{org}/repos?per_page=100&page=... (includes team/classroom access)."""
    repos: list[dict] = []
    page = 1
    last_status_note: str | None = None
    org_quoted = quote(org_login, safe="")
    while True:
        # type=all: for non-owners GitHub defaults to public only; classroom/private org repos need "all".
        response = _github_get(
            f"{GITHUB_API}/orgs/{org_quoted}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "all"},
            timeout=15,
        )
        if response.status_code == 404:
            last_status_note = "org_not_found_or_no_access"
            break
        if response.status_code == 403:
            last_status_note = "org_access_forbidden_check_token_scope_or_sso"
            break
        if response.status_code != 200:
            last_status_note = f"org_repo_fetch_failed_status_{response.status_code}"
            break

        batch = response.json()
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        page += 1
    return repos, last_status_note


def _normalize_repo(repo: dict) -> dict | None:
    if not isinstance(repo, dict):
        return None
    full_name = str(repo.get("full_name") or "").strip()
    name = str(repo.get("name") or "").strip()
    owner_obj = repo.get("owner") if isinstance(repo.get("owner"), dict) else {}
    owner = str(owner_obj.get("login") or "").strip()
    if not full_name and owner and name:
        full_name = f"{owner}/{name}"
    if not name and full_name and "/" in full_name:
        name = full_name.split("/", 1)[1]
    if not owner and full_name and "/" in full_name:
        owner = full_name.split("/", 1)[0]
    if not full_name or not owner or not name:
        return None
    return {
        "id": repo.get("id"),
        "name": name,
        "full_name": full_name,
        "owner": owner,
        "description": repo.get("description"),
        "language": repo.get("language"),
        "stars": repo.get("stargazers_count"),
        "updated_at": repo.get("updated_at"),
        "private": repo.get("private"),
        "owner_type": owner_obj.get("type"),
        "permissions": repo.get("permissions") if isinstance(repo.get("permissions"), dict) else {},
    }


def _permissions_pull_true(repo: dict) -> bool:
    perms = repo.get("permissions")
    return isinstance(perms, dict) and perms.get("pull") is True


def _prefer_repo_duplicate(a: dict, b: dict) -> dict:
    """When two API records share full_name, keep the one with clearer access metadata."""
    if _permissions_pull_true(b) and not _permissions_pull_true(a):
        return b
    if _permissions_pull_true(a) and not _permissions_pull_true(b):
        return a
    ua = str(a.get("updated_at") or "")
    ub = str(b.get("updated_at") or "")
    if ub > ua:
        return b
    return a


def _dedupe_raw_repos_by_full_name(repos: list[dict]) -> list[dict]:
    """Remove duplicates by full_name (GitHub API identity for owner/repo)."""
    by_fn: dict[str, dict] = {}
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        fn = str(repo.get("full_name") or "").strip()
        if not fn:
            continue
        existing = by_fn.get(fn)
        if existing is None:
            by_fn[fn] = repo
        else:
            by_fn[fn] = _prefer_repo_duplicate(existing, repo)
    return list(by_fn.values())


def _filter_repos_with_pull(repos: list[dict]) -> list[dict]:
    """Only repos the token may read (clone/zipball); matches permissions.pull === true."""
    return [r for r in repos if isinstance(r, dict) and _permissions_pull_true(r)]


def _normalize_and_sort_repos(repos: list[dict]) -> list[dict]:
    out: list[dict] = []
    for repo in repos:
        normalized = _normalize_repo(repo)
        if normalized:
            out.append(normalized)
    out.sort(
        key=lambda r: (str(r.get("updated_at") or ""), str(r.get("full_name") or "")),
        reverse=True,
    )
    return out


def _build_collaboration_from_commits_api(owner: str, repo: str, branch: str, headers: dict) -> dict:
    """
    Build a compact collaboration summary using GitHub commits API.
    """
    contributors: dict[str, int] = {}
    first_commit_date: str | None = None
    last_commit_date: str | None = None
    page = 1

    while True:
        commits_url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
        res = requests.get(
            commits_url,
            headers=headers,
            params={"sha": branch, "per_page": 100, "page": page},
            timeout=15,
        )
        if res.status_code != 200:
            break
        rows = res.json()
        if not isinstance(rows, list) or not rows:
            break

        for row in rows:
            if not isinstance(row, dict):
                continue
            author_obj = row.get("author") if isinstance(row.get("author"), dict) else {}
            commit_obj = row.get("commit") if isinstance(row.get("commit"), dict) else {}
            commit_author = commit_obj.get("author") if isinstance(commit_obj.get("author"), dict) else {}

            username = str(author_obj.get("login") or "").strip()
            if not username:
                username = str(commit_author.get("name") or "unknown").strip().lower()
            if not username:
                continue

            contributors[username] = contributors.get(username, 0) + 1

            commit_date = str(commit_author.get("date") or "").strip()
            if commit_date:
                if not first_commit_date or commit_date < first_commit_date:
                    first_commit_date = commit_date
                if not last_commit_date or commit_date > last_commit_date:
                    last_commit_date = commit_date

        page += 1

    primary = max(contributors, key=contributors.get) if contributors else None
    classification = "team" if len(contributors) > 1 else "solo"
    return {
        "contributors": contributors,
        "primary_contributor": primary,
        "classification": classification,
        "first_commit_date": first_commit_date,
        "last_commit_date": last_commit_date,
    }


def _persist_github_snapshot_metadata(
    conn,
    project_id: str,
    owner: str,
    repo: str,
    branch: str,
    headers: dict,
) -> dict:
    """
    Ensure imported/pulled GitHub projects have durable git metadata + collaboration
    inside snapshot for downstream features.
    """
    snapshot = fetch_latest_snapshot(conn, project_id) or {}
    repo_url = f"https://github.com/{owner}/{repo}"
    repo_full_name = f"{owner}/{repo}"
    collab = _build_collaboration_from_commits_api(owner, repo, branch, headers)

    snapshot["source"] = "github"
    snapshot["is_git_project"] = True
    snapshot["repo_url"] = repo_url
    snapshot["repo_full_name"] = repo_full_name
    if collab:
        snapshot["collaboration"] = collab

    store_analysis_snapshot(
        conn,
        project_id=project_id,
        classification=(collab.get("classification") or "unknown"),
        primary_contributor=collab.get("primary_contributor"),
        snapshot=snapshot,
    )
    return snapshot


def _store_commit_sha_in_latest_snapshot(conn, project_id: str, commit_sha: str | None) -> None:
    if not commit_sha:
        return
    current = fetch_latest_snapshot(conn, project_id) or {}
    current["github_latest_commit_sha"] = commit_sha
    classification = ((current.get("collaboration") or {}).get("classification") or "unknown")
    primary_contributor = (current.get("collaboration") or {}).get("primary_contributor")
    store_analysis_snapshot(
        conn,
        project_id=project_id,
        classification=classification,
        primary_contributor=primary_contributor,
        snapshot=current,
    )



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
    Repositories the authenticated token can access: /user/repos plus every
    /orgs/{org}/repos for orgs from /user/orgs, merged and deduped by full_name,
    then filtered to permissions.pull === true.
    """


    token = get_github_token()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    user_repos_raw, diag = _list_user_repos(headers)
    orgs = _list_user_orgs(headers)
    org_repos_raw: list[dict] = []
    org_notes: list[str] = []
    for org_login in orgs:
        batch, note = _list_org_repos(org_login, headers)
        org_repos_raw.extend(batch)
        if note:
            org_notes.append(f"{org_login}:{note}")

    merged_raw = [*user_repos_raw, *org_repos_raw]
    deduped_raw = _dedupe_raw_repos_by_full_name(merged_raw)
    pull_filtered_raw = _filter_repos_with_pull(deduped_raw)
    combined = _normalize_and_sort_repos(pull_filtered_raw)
    owners = sorted({str(r.get("owner") or "") for r in combined if r.get("owner")})
    print(
        "[github/repos] "
        f"user_raw={len(user_repos_raw)} "
        f"user_pages={diag.get('pages')} "
        f"org_count={len(orgs)} "
        f"org_raw={len(org_repos_raw)} "
        f"merged={len(merged_raw)} "
        f"deduped_full_name={len(deduped_raw)} "
        f"after_pull_filter={len(pull_filtered_raw)} "
        f"final={len(combined)} "
        f"oauth_scopes='{diag.get('oauth_scopes')}' "
        f"accepted_scopes='{diag.get('accepted_scopes')}' "
        f"org_notes={org_notes} "
        f"owners_sample={owners[:20]} "
        f"repos_sample={[r.get('full_name') for r in combined[:30]]}",
        flush=True,
    )
    return combined


# ------------------------------------------------
# 2. Import repository from GitHub
# ------------------------------------------------

@router.post("/import")
def import_repository(
    owner: str,
    repo: str,
    project_id: str,
    branch: str = "main",
    refresh: bool = False,
):
    """
    Downloads a GitHub repository as a zip archive and runs the ZipAnalyzer.
    """
    token = get_github_token()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    conn = open_db()
    try:
        existing_snapshot = fetch_latest_snapshot(conn, project_id) or {}
        existing_github = conn.execute(
            "SELECT 1 FROM projects WHERE project_id = ? AND source = 'github' LIMIT 1",
            (project_id,),
        ).fetchone()
        if existing_snapshot and existing_github and not refresh:
            return {
                "status": "cached",
                "project_id": project_id,
                "repository": f"https://github.com/{owner}/{repo}",
                "summary": existing_snapshot,
                "reason": "snapshot_exists",
            }
    finally:
        conn.close()
    latest_commit_sha = _fetch_latest_commit_sha(owner, repo, branch, headers)

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
            # Patch snapshot with real commit dates from GitHub API.
            # GitHub zipballs have no .git directory, so ZipAnalyzer cannot
            # extract timestamps from git log — we fetch them here instead.
            _patch_github_commit_dates(conn, project_id, owner, repo, branch, headers, summary)
            persisted_snapshot = _persist_github_snapshot_metadata(conn, project_id, owner, repo, branch, headers)
            _store_commit_sha_in_latest_snapshot(conn, project_id, latest_commit_sha)
            if isinstance(persisted_snapshot, dict):
                summary["collaboration"] = persisted_snapshot.get("collaboration") or summary.get("collaboration")

            # Sync source, github_url, github_branch and commit dates into the projects table.
            _github_url = f"https://github.com/{owner}/{repo}"
            _collab = (summary.get("collaboration") or {})
            upsert_project(
                conn, project_id,
                source="github",
                github_url=_github_url,
                github_branch=branch,
                first_commit_at=_collab.get("first_commit_date"),
                last_commit_at=_collab.get("last_commit_date"),
            )

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
            active_user = storage_module.get_current_user()
            if _is_cloud_sync_user(active_user):
                upload_project_zip(
                    active_user,
                    project_id,
                    zip_path,
                    zip_path.name,
                )
                upload_database(active_user)
        finally:
            conn.close()

        repo_url = f"https://github.com/{owner}/{repo}"
        summary["source"] = "github"
        summary["is_git_project"] = True
        summary["repo_url"] = repo_url
        summary["repo_full_name"] = f"{owner}/{repo}"

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
def pull_repository(project_id: str, refresh: bool = False):

    token = get_github_token()
    if not token:
        raise HTTPException(401, "GitHub token not configured")

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    conn = open_db()

    proj_row = conn.execute(
        "SELECT github_url, github_branch FROM projects WHERE project_id=? AND source='github'",
        (project_id,)
    ).fetchone()

    if not proj_row:
        conn.close()
        raise HTTPException(404, "Project is not a GitHub project")

    existing_snapshot = fetch_latest_snapshot(conn, project_id) or {}
    if existing_snapshot and not refresh:
        conn.close()
        return {
            "status": "cached",
            "project_id": project_id,
            "summary": existing_snapshot,
            "reason": "snapshot_exists",
        }

    _github_url, branch = proj_row
    branch = branch or "main"
    # Parse owner/repo from stored github_url (e.g. https://github.com/owner/repo)
    _url_parts = (_github_url or "").rstrip("/").split("/")
    owner = _url_parts[-2] if len(_url_parts) >= 2 else ""
    repo = _url_parts[-1] if _url_parts else ""
    if not owner or not repo:
        conn.close()
        raise HTTPException(400, "Stored GitHub URL is malformed")
    latest_commit_sha = _fetch_latest_commit_sha(owner, repo, branch, headers)
    cached_sha = str(existing_snapshot.get("github_latest_commit_sha") or "").strip() or None

    if latest_commit_sha and cached_sha and latest_commit_sha == cached_sha:
        conn.close()
        return {
            "status": "cached",
            "project_id": project_id,
            "summary": existing_snapshot,
            "reason": "no_remote_changes",
            "commit_sha": latest_commit_sha,
        }

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
            conn=conn,
            skip_contributor_storage=True,
        )
        persisted_snapshot = _persist_github_snapshot_metadata(conn, project_id, owner, repo, branch, headers)
        _store_commit_sha_in_latest_snapshot(conn, project_id, latest_commit_sha)
        if isinstance(persisted_snapshot, dict):
            summary["collaboration"] = persisted_snapshot.get("collaboration") or summary.get("collaboration")

        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            sync_contributor_stats(
                repo_url=repo_url,
                token=token,
                project_id=project_id,
            )
        except Exception:
            pass  # non-fatal

        active_user = storage_module.get_current_user()
        if _is_cloud_sync_user(active_user):
            upload_project_zip(
                active_user,
                project_id,
                zip_path,
                zip_path.name,
            )
            upload_database(active_user)

    conn.close()

    summary["source"] = "github"
    summary["is_git_project"] = True
    summary["repo_url"] = f"https://github.com/{owner}/{repo}"
    summary["repo_full_name"] = f"{owner}/{repo}"
    return {"status": "updated", "summary": summary}


# ------------------------------------------------
# 3. check login state
# ------------------------------------------------


@router.get("/token/status")
def github_token_status():
    """Return whether a token is stored and a masked hint only (never the secret)."""
    token = get_github_token()
    if not token:
        return {"configured": False, "masked_token": None}
    return {"configured": True, "masked_token": mask_github_token_for_display(token)}


@router.put("/token")
def put_github_token(payload: GithubTokenUpdate):
    """Replace stored GitHub token after remote validation; does not return the raw token."""
    return _apply_github_token_update(payload.token)


@router.get("/auth-status")
def github_auth_status():
    token = get_github_token()

    if not token:
        return {"authenticated": False}

    return {"authenticated": True}

@router.post("/login")
def github_login(token: str):
    save_github_token(token)

    active_user = storage_module.get_current_user()
    if _is_cloud_sync_user(active_user):
        upload_database(active_user)

    return {
        "status": "authenticated"
    }

# ------------------------------------------------
# 3. fetch branch
# ------------------------------------------------


@router.get("/branches")
def get_branches(owner: str, repo: str):
    token = get_github_token()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

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