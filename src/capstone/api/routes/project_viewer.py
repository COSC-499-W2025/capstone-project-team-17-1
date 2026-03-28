"""API routes for the Project Viewer feature.

Provides endpoints to browse project zip contents (file tree + file content),
retrieve analysis snapshots, update files, and fetch collaboration data.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from capstone import file_store, storage
from capstone.git_analysis import _parse_git_log_lines, run_git_log
from capstone.logging_utils import get_logger
from capstone.system.cloud_storage import (
    upload_project_zip as cloud_upload_zip,
    upload_database as cloud_upload_db,
)
import capstone.storage as storage_module

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["project-viewer"])

_TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
    ".hpp", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".html", ".htm", ".css", ".scss", ".less", ".sass",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".svg", ".md", ".mdx", ".txt", ".rst", ".log",
    ".sql", ".graphql", ".gql",
    ".env", ".gitignore", ".dockerignore", ".editorconfig",
    ".lock", ".csv", ".tsv",
    "Dockerfile", "Makefile", "Pipfile", "Procfile",
}

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp"}

_MAX_TEXT_SIZE = 2 * 1024 * 1024  # 2 MB


# ── Project lookup (multi-source) ──────────────────────────────────

def _get_file_id_for_project(project_id: str) -> str:
    """Locate a project's zip file_id by checking uploads, then project_analysis."""
    conn = storage.open_db()

    row = conn.execute(
        "SELECT u.file_id FROM uploads u WHERE u.upload_id = ? "
        "ORDER BY datetime(u.created_at) DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if row:
        logger.info("Project %s found in uploads table", project_id)
        return row[0] if isinstance(row, tuple) else row["file_id"]

    pa_row = conn.execute(
        "SELECT snapshot, zip_path FROM project_analysis "
        "WHERE project_id = ? ORDER BY datetime(created_at) DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if pa_row:
        snap_raw = pa_row[0] if isinstance(pa_row, tuple) else pa_row["snapshot"]
        zip_p = pa_row[1] if isinstance(pa_row, tuple) else pa_row["zip_path"]
        try:
            snap = json.loads(snap_raw) if isinstance(snap_raw, str) else snap_raw
        except Exception:
            snap = {}

        archive_file_id = snap.get("archive_file_id")
        if archive_file_id:
            file_row = conn.execute(
                "SELECT file_id FROM files WHERE file_id = ?", (archive_file_id,)
            ).fetchone()
            if file_row:
                logger.info("Project %s found via archive_file_id in snapshot", project_id)
                return archive_file_id

        if zip_p and Path(zip_p).exists():
            stored = file_store.ensure_file(
                conn, Path(zip_p),
                original_name=Path(zip_p).name,
                source="project_viewer_recovery",
                upload_id=project_id,
            )
            conn.commit()
            logger.info("Project %s recovered from zip_path on disk", project_id)
            return stored["file_id"]

        all_files = conn.execute("SELECT file_id, path FROM files").fetchall()
        for fr in all_files:
            fid = fr[0] if isinstance(fr, tuple) else fr["file_id"]
            fpath = fr[1] if isinstance(fr, tuple) else fr["path"]
            if fpath and project_id.lower() in Path(fpath).name.lower():
                logger.info("Project %s found via filename match in files table", project_id)
                return fid

    raise HTTPException(status_code=404, detail="Project not found")


def _get_zip_path_for_project(project_id: str) -> Path:
    """Return the local filesystem path to the project's zip."""
    conn = storage.open_db()
    file_id = _get_file_id_for_project(project_id)
    row = conn.execute("SELECT path FROM files WHERE file_id = ?", (file_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Zip file not found in storage")
    p = row[0] if isinstance(row, tuple) else row["path"]
    path = Path(p)
    if not path.exists():
        from capstone.file_store import DEFAULT_FILES_ROOT
        candidates = list(DEFAULT_FILES_ROOT.glob(f"{file_id}*"))
        if candidates:
            path = candidates[0]
        else:
            raise HTTPException(status_code=404, detail="Zip file missing from disk")
    return path


def _open_project_zip(file_id: str) -> zipfile.ZipFile:
    conn = storage.open_db()
    fh = file_store.open_file(conn, file_id)
    try:
        return zipfile.ZipFile(fh)
    except zipfile.BadZipFile:
        fh.close()
        raise HTTPException(status_code=400, detail="Stored file is not a valid zip")


def _strip_root(path: str, root: str | None) -> str:
    if root and path.startswith(root + "/"):
        return path[len(root) + 1:]
    return path


def _detect_root(zf: zipfile.ZipFile) -> str | None:
    roots = set()
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = [p for p in info.filename.strip("/").split("/") if p]
        if parts:
            roots.add(parts[0])
    return roots.pop() if len(roots) == 1 else None


# ── File tree ──────────────────────────────────────────────────────

@router.get("/{project_id}/tree")
def get_project_file_tree(project_id: str):
    """Return the file tree structure for a project zip."""
    file_id = _get_file_id_for_project(project_id)
    zf = _open_project_zip(file_id)

    try:
        root = _detect_root(zf)
        tree: dict = {}

        for info in zf.infolist():
            if info.is_dir():
                continue
            raw_path = info.filename.strip("/")
            if not raw_path:
                continue
            rel_path = _strip_root(raw_path, root)
            if not rel_path:
                continue

            parts = rel_path.split("/")
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = {
                "__file__": True,
                "size": info.file_size,
                "path": rel_path,
            }
    finally:
        zf.close()

    def build_nodes(subtree: dict, prefix: str = "") -> list:
        items = []
        for name, value in sorted(subtree.items()):
            if isinstance(value, dict) and "__file__" in value:
                items.append({
                    "name": name,
                    "type": "file",
                    "path": value["path"],
                    "size": value["size"],
                })
            elif isinstance(value, dict):
                child_path = f"{prefix}{name}/" if prefix else f"{name}/"
                items.append({
                    "name": name,
                    "type": "directory",
                    "path": child_path.rstrip("/"),
                    "children": build_nodes(value, child_path),
                })
        dirs = [i for i in items if i["type"] == "directory"]
        files = [i for i in items if i["type"] == "file"]
        return dirs + files

    return {"project_id": project_id, "tree": build_nodes(tree)}


# ── File content ───────────────────────────────────────────────────

@router.get("/{project_id}/file")
def get_project_file_content(
    project_id: str,
    path: str = Query(..., description="Relative file path within the project"),
):
    """Return the content of a specific file from the project zip."""
    file_id = _get_file_id_for_project(project_id)
    zf = _open_project_zip(file_id)

    try:
        root = _detect_root(zf)
        lookup_path = f"{root}/{path}" if root else path

        try:
            info = zf.getinfo(lookup_path)
        except KeyError:
            for zi in zf.infolist():
                stripped = _strip_root(zi.filename.strip("/"), root)
                if stripped == path:
                    info = zi
                    break
            else:
                raise HTTPException(status_code=404, detail=f"File not found: {path}")

        suffix = PurePosixPath(path).suffix.lower()
        name_lower = PurePosixPath(path).name.lower()
        is_image = suffix in _IMAGE_EXTENSIONS
        is_text = (
            suffix in _TEXT_EXTENSIONS
            or name_lower in _TEXT_EXTENSIONS
            or name_lower.startswith(".")
        )

        if is_image:
            raw = zf.read(info)
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
            return {
                "path": path, "type": "image", "mime": mime,
                "content": base64.b64encode(raw).decode("ascii"),
                "size": info.file_size,
            }

        if is_text or info.file_size < _MAX_TEXT_SIZE:
            raw = zf.read(info)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = raw.decode("latin-1")
                except Exception:
                    return {"path": path, "type": "binary", "content": None, "size": info.file_size}
            lang = _detect_language(path)
            return {"path": path, "type": "text", "language": lang, "content": text, "size": info.file_size}

        return {"path": path, "type": "binary", "content": None, "size": info.file_size}
    finally:
        zf.close()


# ── Update file (save edits) ──────────────────────────────────────

class UpdateFilePayload(BaseModel):
    project_id: str
    file_path: str
    updated_code: str


@router.post("/update-file")
def update_project_file(payload: UpdateFilePayload):
    """Update a file inside the project zip and optionally sync to cloud."""
    project_id = payload.project_id
    file_path = payload.file_path
    updated_code = payload.updated_code

    zip_path = _get_zip_path_for_project(project_id)

    with zipfile.ZipFile(zip_path, "r") as zf:
        root = _detect_root(zf)
        internal_path = f"{root}/{file_path}" if root else file_path

        found = False
        for zi in zf.infolist():
            stripped = _strip_root(zi.filename.strip("/"), root)
            if stripped == file_path:
                internal_path = zi.filename
                found = True
                break
        if not found:
            try:
                zf.getinfo(internal_path)
                found = True
            except KeyError:
                pass
        if not found:
            raise HTTPException(status_code=404, detail=f"File not found in archive: {file_path}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf_in:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
                for item in zf_in.infolist():
                    if item.filename == internal_path:
                        zf_out.writestr(item, updated_code.encode("utf-8"))
                    else:
                        zf_out.writestr(item, zf_in.read(item))

        shutil.move(str(tmp_path), str(zip_path))
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to update file: {exc}")

    if storage_module.CURRENT_USER:
        try:
            cloud_upload_zip(
                storage_module.CURRENT_USER,
                project_id,
                zip_path,
                zip_path.name,
            )
            cloud_upload_db(storage_module.CURRENT_USER)
        except Exception:
            logger.warning("Cloud sync failed after file update for %s", project_id)

    logger.info("File updated: %s in project %s", file_path, project_id)
    return {"status": "success", "project_id": project_id, "file_path": file_path}


# ── Analysis ───────────────────────────────────────────────────────

@router.get("/{project_id}/analysis")
def get_project_analysis(project_id: str):
    """Return the analysis snapshot for a project."""
    conn = storage.open_db()
    snapshot = storage.fetch_latest_snapshot(conn, project_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No analysis data found for this project")
    return {"project_id": project_id, "analysis": snapshot}


# ── Collaboration data ─────────────────────────────────────────────

_BOT_TOKENS = {"bot", "ci", "automation", "github-classroom", "dependabot"}

# In-memory cache for GitHub PR/review stats: (owner, repo) -> (prs_by_login, reviews_by_login, cached_at)
_github_pr_cache: dict[tuple[str, str], tuple[dict[str, int], dict[str, int], float]] = {}
_GITHUB_CACHE_TTL_SEC = 300  # 5 minutes


def _normalize_contributor_key(name: str) -> tuple[list[str], list[str], str | None, str | None]:
    """
    Generate candidate keys for matching a contributor name to GitHub login.
    Returns (strong_keys, partial_keys, first_name, last_name).
    - strong_keys: exact normalized, no-space, first+last join (safe for direct match)
    - partial_keys: first name, last name (for containment match only when no strong match)
    """
    if not name:
        return ([], [], None, None)
    s = (name or "").strip().lower()
    if not s:
        return ([], [], None, None)

    no_punct = re.sub(r"[^\w\s]", "", s)
    no_spaces = "".join(s.split())
    no_punct_no_spaces = "".join(no_punct.split())

    parts = [p for p in no_punct.split() if p]
    first = "".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else None)
    last = parts[-1] if parts else None
    if first and last and first != last:
        first_last_join = first + last
    else:
        first_last_join = first or last or ""

    strong_keys = []
    seen_strong = set()
    for k in [s, no_spaces, no_punct_no_spaces, first_last_join]:
        if k and k not in seen_strong:
            strong_keys.append(k)
            seen_strong.add(k)

    partial_keys = []
    if first and first not in seen_strong:
        partial_keys.append(first)
    if last and last not in seen_strong and last != first:
        partial_keys.append(last)

    return (strong_keys, partial_keys, first, last)


def _github_request(url: str, *, token: str | None) -> object:
    """Fetch JSON from GitHub API. Returns parsed object or empty list on failure."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "capstone-cli/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, headers=headers), timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError, OSError) as exc:
        logger.debug("GitHub API request failed %s: %s", url[:80], exc)
        return []


def _fetch_github_pr_review_stats(owner: str, repo: str, token: str | None) -> tuple[dict[str, int], dict[str, int]]:
    """
    Fetch PR creation and review counts from GitHub API.
    Returns (prs_by_login, reviews_by_login). On failure returns ({}, {}).
    """
    cache_key = (owner, repo)
    now = time.time()
    if cache_key in _github_pr_cache:
        prs_map, reviews_map, cached_at = _github_pr_cache[cache_key]
        if now - cached_at < _GITHUB_CACHE_TTL_SEC:
            return prs_map, reviews_map

    prs_by_login: dict[str, int] = {}
    reviews_by_login: dict[str, int] = {}

    if not token:
        return prs_by_login, reviews_by_login

    page = 1
    total_fetched = 0
    max_prs = 1000
    max_review_fetches = 100  # Limit review API calls to avoid rate limits

    while total_fetched < max_prs:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=100&page={page}"
        pulls = _github_request(url, token=token)
        if not isinstance(pulls, list) or len(pulls) == 0:
            break

        for pr in pulls:
            if total_fetched >= max_prs:
                break
            user = pr.get("user") if isinstance(pr, dict) else None
            login = (user.get("login") or "").strip() if isinstance(user, dict) else ""
            if not login or _is_bot_contributor(login):
                total_fetched += 1
                continue

            key = login.lower().strip()
            prs_by_login[key] = prs_by_login.get(key, 0) + 1

            if total_fetched < max_review_fetches:
                pull_number = pr.get("number")
                if pull_number is not None:
                    reviews_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
                    reviews_data = _github_request(reviews_url, token=token)
                    if isinstance(reviews_data, list):
                        for r in reviews_data:
                            reviewer = r.get("user") if isinstance(r, dict) else None
                            rev_login = (reviewer.get("login") or "").strip() if isinstance(reviewer, dict) else ""
                            if rev_login and not _is_bot_contributor(rev_login):
                                rk = rev_login.lower().strip()
                                reviews_by_login[rk] = reviews_by_login.get(rk, 0) + 1

            total_fetched += 1

        if len(pulls) < 100:
            break
        page += 1

    _github_pr_cache[cache_key] = (prs_by_login, reviews_by_login, now)
    logger.info(
        "GitHub PR stats: %s/%s prs=%d contributors, reviews=%d contributors",
        owner, repo, len(prs_by_login), len(reviews_by_login),
    )
    return prs_by_login, reviews_by_login


def _find_matching_login(
    strong_keys: list[str],
    first: str | None,
    last: str | None,
    data_by_login: dict[str, int],
    used_logins: set[str],
) -> tuple[str | None, int]:
    """
    Find a login in data_by_login that matches the contributor.
    Returns (matched_login, value) or (None, 0).
    Strong match preferred; partial only if no strong match exists.
    """
    strong_matches: list[tuple[str, int]] = []
    partial_matches: list[tuple[str, int]] = []

    for login, val in data_by_login.items():
        if not val or login in used_logins:
            continue
        login_norm = login.lower().strip()

        is_strong = False
        for k in strong_keys:
            if k == login_norm:
                strong_matches.append((login, val))
                is_strong = True
                break

        if is_strong:
            continue
        if (first and len(first) >= 2 and first in login_norm) or (
            last and len(last) >= 2 and last in login_norm
        ):
            partial_matches.append((login, val))

    if strong_matches:
        best = max(strong_matches, key=lambda x: x[1])
        return (best[0], best[1])
    if partial_matches:
        best = max(partial_matches, key=lambda x: x[1])
        return (best[0], best[1])
    return (None, 0)


def _merge_github_stats_into_contributors(
    contributors: list[dict],
    prs_by_login: dict[str, int],
    reviews_by_login: dict[str, int],
) -> None:
    """Mutate contributors in place, adding prs_created and pr_reviews from GitHub, recomputing score."""
    used_pr_logins: set[str] = set()
    used_rev_logins: set[str] = set()

    for c in contributors:
        name = c.get("name") or ""
        strong_keys, partial_keys, first, last = _normalize_contributor_key(name)
        prs = 0
        revs = 0
        pr_login: str | None = None
        rev_login: str | None = None

        pr_login, prs = _find_matching_login(
            strong_keys, first, last, prs_by_login, used_pr_logins
        )
        rev_login, revs = _find_matching_login(
            strong_keys, first, last, reviews_by_login, used_rev_logins
        )

        if pr_login:
            used_pr_logins.add(pr_login)
            logger.info("Matched GitHub login %s → contributor %s (PRs)", pr_login, name)
        if rev_login and rev_login != pr_login:
            used_rev_logins.add(rev_login)
            logger.info("Matched GitHub login %s → contributor %s (reviews)", rev_login, name)

        c["prs_created"] = prs
        c["pr_reviews"] = revs
        c["score"] = c.get("commits", 0) + (3 * prs) + (2 * revs)
    contributors.sort(key=lambda x: x["score"], reverse=True)


def _is_bot_contributor(name: str) -> bool:
    lowered = (name or "").strip().lower()
    return any(t in lowered for t in _BOT_TOKENS)


def _read_git_log_from_zip(zf: zipfile.ZipFile) -> str | None:
    """Find and read git log content from zip (git_log.txt or .git/logs/git_log)."""
    candidates = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        path_lower = info.filename.lower().replace("\\", "/")
        if path_lower.endswith("git_log.txt") or path_lower.endswith("/git_log"):
            depth = path_lower.count("/")
            candidates.append((depth, info))
    candidates.sort(key=lambda x: x[0])
    for _, info in candidates:
        try:
            raw = zf.read(info)
            text = raw.decode("utf-8", errors="ignore")
            if "commit:" in text and "|" in text:
                return text
        except Exception:
            continue
    return None


def _zip_has_git_dir(zf: zipfile.ZipFile) -> bool:
    """Check if zip contains a .git directory."""
    for info in zf.infolist():
        parts = info.filename.replace("\\", "/").strip("/").split("/")
        if ".git" in parts:
            return True
    return False


def _extract_git_root(zf: zipfile.ZipFile, dest: Path) -> Path | None:
    """Extract zip to dest and return path to directory containing .git, or None."""
    root_dirs = set()
    for info in zf.infolist():
        parts = info.filename.replace("\\", "/").strip("/").split("/")
        if not parts or parts[0] == "":
            continue
        root_dirs.add(parts[0])
    zf.extractall(dest)
    for d in root_dirs:
        candidate = dest / d
        if candidate.is_dir():
            git_dir = candidate / ".git"
            if git_dir.exists():
                return candidate
    if (dest / ".git").exists():
        return dest
    return None


def _compute_collaboration_from_git(
    project_id: str,
    zip_path: Path,
    conn,
    snapshot: dict,
) -> dict | None:
    """
    Extract contributor stats from git history (git_log in zip or live git).
    Returns dict with contributors, project_timeline, bot_contributors; or None if no git data.
    """
    collab = snapshot.get("collaboration") or {}
    pr_snapshot = collab.get("contributors (commits, PRs, issues, reviews)") or {}
    if not isinstance(pr_snapshot, dict):
        pr_snapshot = {}

    git_log_text: str | None = None
    repo_path: Path | None = None

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            git_log_text = _read_git_log_from_zip(zf)
            if git_log_text:
                pass
            elif _zip_has_git_dir(zf):
                with tempfile.TemporaryDirectory(prefix="capstone-collab-") as tmp:
                    repo_path = _extract_git_root(zf, Path(tmp))
                    if repo_path:
                        try:
                            git_log_text = run_git_log(repo_path)
                        except subprocess.CalledProcessError as exc:
                            logger.warning("git log failed for %s: %s", project_id, exc)
                        except FileNotFoundError:
                            logger.warning("git executable not found for %s", project_id)
    except Exception as exc:
        logger.warning("Failed to read zip for collaboration %s: %s", project_id, exc)
        return None

    if not git_log_text:
        return None

    commits_by_author: dict[str, int] = {}
    reviews_by_author: dict[str, int] = {}
    lines_by_author: dict[str, int] = {}
    last_commit_by_author: dict[str, int] = {}
    all_timestamps: list[int] = []
    bot_names: set[str] = set()

    for rec in _parse_git_log_lines(git_log_text.splitlines()):
        author = (rec.author or "Unknown").strip()
        if not author:
            continue
        if _is_bot_contributor(author):
            bot_names.add(author)
            continue
        commits_by_author[author] = commits_by_author.get(author, 0) + 1
        reviews = 1 if rec.is_review else 0
        reviews_by_author[author] = reviews_by_author.get(author, 0) + reviews
        lines = rec.lines_added + rec.lines_deleted
        lines_by_author[author] = lines_by_author.get(author, 0) + lines
        ts = rec.timestamp
        all_timestamps.append(ts)
        prev = last_commit_by_author.get(author, 0)
        if ts > prev:
            last_commit_by_author[author] = ts

    logger.info(
        "Collaboration git parse: project=%s commits=%d contributors=%d",
        project_id, len(all_timestamps), len(commits_by_author),
    )

    authors = set(commits_by_author.keys())
    first_ts = min(all_timestamps) if all_timestamps else None
    last_ts = max(all_timestamps) if all_timestamps else None

    if first_ts:
        first_date = datetime.utcfromtimestamp(first_ts).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        first_date = None
    if last_ts:
        last_date = datetime.utcfromtimestamp(last_ts).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        last_date = None
    duration_days = (last_ts - first_ts) // 86400 if first_ts and last_ts else 0

    contributors = []
    for author in authors:
        commits = commits_by_author.get(author, 0)
        reviews = reviews_by_author.get(author, 0)
        prs = 0
        if isinstance(pr_snapshot.get(author), dict):
            prs = int(pr_snapshot[author].get("prs", pr_snapshot[author].get("pull_requests", 0)) or 0)
        lines = lines_by_author.get(author, 0)
        score = commits + (3 * prs) + (2 * reviews)
        last_ts_a = last_commit_by_author.get(author)
        last_commit_time = datetime.utcfromtimestamp(last_ts_a).strftime("%Y-%m-%dT%H:%M:%SZ") if last_ts_a else None
        contributors.append({
            "name": author,
            "commits": commits,
            "prs_created": prs,
            "pr_reviews": reviews,
            "lines_changed": lines,
            "score": score,
            "last_commit_time": last_commit_time,
        })

    contributors.sort(key=lambda c: c["score"], reverse=True)
    primary = contributors[0]["name"] if contributors else None

    return {
        "contributors": contributors,
        "bot_contributors": sorted(bot_names),
        "first_commit_date": first_date,
        "last_commit_date": last_date,
        "project_duration_days": duration_days,
        "primary_contributor": primary,
        "classification": "individual" if len(authors) <= 1 else "collaborative",
        "project_timeline": {
            "first_commit_date": first_date,
            "last_commit_date": last_date,
            "duration_days": duration_days,
        },
    }


@router.get("/collaboration/{project_id}")
def get_project_collaboration(project_id: str):
    """Return detailed collaboration data for a project."""
    conn = storage.open_db()
    snapshot = storage.fetch_latest_snapshot(conn, project_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No analysis data found for this project")

    collab = snapshot.get("collaboration") or {}
    is_github = bool(conn.execute(
        "SELECT 1 FROM github_projects WHERE project_id = ? LIMIT 1",
        (project_id,),
    ).fetchone())

    cached = snapshot.get("collaboration_cached")
    if isinstance(cached, dict) and isinstance(cached.get("contributors"), list):
        return {
            "project_id": project_id,
            "is_github": is_github,
            "classification": cached.get("classification") or collab.get("classification") or "unknown",
            "primary_contributor": cached.get("primary_contributor") or collab.get("primary_contributor"),
            "total_contributors": int(cached.get("total_contributors") or len(cached.get("contributors") or [])),
            "contributors": cached.get("contributors") or [],
            "bot_contributors": cached.get("bot_contributors") or [],
            "first_commit_date": cached.get("first_commit_date"),
            "last_commit_date": cached.get("last_commit_date"),
            "project_duration_days": int(cached.get("project_duration_days") or 0),
            "project_timeline": cached.get("project_timeline") or {},
            "scores": cached.get("scores") or {},
            "review_totals": cached.get("review_totals") or {},
        }

    git_result = None
    try:
        zip_path = _get_zip_path_for_project(project_id)
        git_result = _compute_collaboration_from_git(project_id, zip_path, conn, snapshot)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Git collaboration extraction failed for %s: %s", project_id, exc)

    if git_result:
        contributors = git_result["contributors"]
        bot_contributors = git_result["bot_contributors"]
        first_date = git_result["first_commit_date"]
        last_date = git_result["last_commit_date"]
        duration_days = git_result["project_duration_days"]
        primary = git_result["primary_contributor"]
        classification = git_result["classification"]
        project_timeline = git_result["project_timeline"]

        if is_github:
            try:
                row = conn.execute(
                    "SELECT owner, repo FROM github_projects WHERE project_id = ? LIMIT 1",
                    (project_id,),
                ).fetchone()
                if row:
                    owner = (row[0] if isinstance(row, tuple) else row["owner"] or "").strip()
                    repo = (row[1] if isinstance(row, tuple) else row["repo"] or "").strip()
                    token = storage.get_github_token()
                    if owner and repo:
                        prs_by_login, reviews_by_login = _fetch_github_pr_review_stats(owner, repo, token)
                        if prs_by_login or reviews_by_login:
                            _merge_github_stats_into_contributors(contributors, prs_by_login, reviews_by_login)
                            primary = contributors[0]["name"] if contributors else primary
            except Exception as exc:
                logger.warning("Failed to merge GitHub PR stats for %s: %s", project_id, exc)
    else:
        contributors_raw = (
            collab.get("contributors (commits, PRs, issues, reviews)")
            or collab.get("contributors (commits, line changes, reviews)")
            or collab.get("contributors")
            or {}
        )
        contributors = []

        def _parse_contrib_val(val):
            if isinstance(val, dict):
                return (
                    int(val.get("commits", 0)),
                    int(val.get("reviews", 0)),
                    int(val.get("prs", val.get("pull_requests", 0))),
                    int(val.get("lines", 0)),
                )
            if isinstance(val, (list, tuple)) and len(val) >= 3:
                return int(val[0]), int(val[2]), 0, int(val[1])
            if isinstance(val, str):
                try:
                    parts = [int(x.strip()) for x in val.strip("[]").split(",") if x.strip()]
                    commits = parts[0] if len(parts) > 0 else 0
                    lines = parts[1] if len(parts) > 1 else 0
                    reviews = parts[2] if len(parts) > 2 else 0
                    return commits, reviews, 0, lines
                except (ValueError, AttributeError):
                    pass
            if isinstance(val, (int, float)):
                return int(val), 0, 0, 0
            return 0, 0, 0, 0

        if isinstance(contributors_raw, dict):
            for name, val in contributors_raw.items():
                if _is_bot_contributor(name):
                    continue
                commits, reviews, prs, lines = _parse_contrib_val(val)
                score = commits + (3 * prs) + (2 * reviews)
                contributors.append({
                    "name": name, "commits": commits, "prs_created": prs,
                    "pr_reviews": reviews, "lines_changed": lines, "score": score,
                    "last_commit_time": None,
                })
        elif isinstance(contributors_raw, list):
            for item in contributors_raw:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("author") or "Unknown"
                    if _is_bot_contributor(name):
                        continue
                    commits = item.get("commits", 0)
                    reviews = item.get("reviews", 0)
                    prs = item.get("prs", item.get("pull_requests", 0))
                    lines = item.get("lines", 0)
                    score = commits + (3 * prs) + (2 * reviews)
                    contributors.append({
                        "name": name, "commits": commits, "prs_created": prs,
                        "pr_reviews": reviews, "lines_changed": lines, "score": score,
                        "last_commit_time": item.get("last_commit_time"),
                    })
        contributors.sort(key=lambda c: c["score"], reverse=True)
        bot_contributors = [k for k in (collab.get("bot_contributors") or []) if isinstance(k, str)]
        if isinstance(collab.get("bot_contributors"), dict):
            bot_contributors = list(collab["bot_contributors"].keys())
        file_summary = snapshot.get("file_summary") or {}
        first_date = file_summary.get("earliest_modification")
        last_date = file_summary.get("latest_modification")
        duration_days = file_summary.get("duration_days", 0)
        primary = collab.get("primary_contributor") or (contributors[0]["name"] if contributors else None)
        classification = collab.get("classification", "unknown")
        project_timeline = {
            "first_commit_date": first_date,
            "last_commit_date": last_date,
            "duration_days": duration_days,
        }

        if is_github and contributors:
            try:
                row = conn.execute(
                    "SELECT owner, repo FROM github_projects WHERE project_id = ? LIMIT 1",
                    (project_id,),
                ).fetchone()
                if row:
                    owner = (row[0] if isinstance(row, tuple) else row["owner"] or "").strip()
                    repo = (row[1] if isinstance(row, tuple) else row["repo"] or "").strip()
                    token = storage.get_github_token()
                    if owner and repo:
                        prs_by_login, reviews_by_login = _fetch_github_pr_review_stats(owner, repo, token)
                        if prs_by_login or reviews_by_login:
                            _merge_github_stats_into_contributors(contributors, prs_by_login, reviews_by_login)
                            primary = contributors[0]["name"] if contributors else primary
            except Exception as exc:
                logger.warning("Failed to merge GitHub PR stats for %s: %s", project_id, exc)

    response_payload = {
        "project_id": project_id,
        "is_github": is_github,
        "classification": classification,
        "primary_contributor": primary,
        "total_contributors": len(contributors),
        "contributors": contributors,
        "bot_contributors": bot_contributors,
        "first_commit_date": first_date,
        "last_commit_date": last_date,
        "project_duration_days": duration_days,
        "project_timeline": project_timeline,
        "scores": collab.get("scores") or {},
        "review_totals": collab.get("review_totals") or {},
    }

    # Persist computed collaboration so future loads (including after restart)
    # can return instantly from DB without recomputing git history.
    try:
        snapshot_copy = dict(snapshot or {})
        snapshot_copy["collaboration_cached"] = {
            "classification": response_payload["classification"],
            "primary_contributor": response_payload["primary_contributor"],
            "total_contributors": response_payload["total_contributors"],
            "contributors": response_payload["contributors"],
            "bot_contributors": response_payload["bot_contributors"],
            "first_commit_date": response_payload["first_commit_date"],
            "last_commit_date": response_payload["last_commit_date"],
            "project_duration_days": response_payload["project_duration_days"],
            "project_timeline": response_payload["project_timeline"],
            "scores": response_payload["scores"],
            "review_totals": response_payload["review_totals"],
        }
        if isinstance(snapshot_copy.get("collaboration"), dict):
            snapshot_copy["collaboration"]["classification"] = response_payload["classification"]
            snapshot_copy["collaboration"]["primary_contributor"] = response_payload["primary_contributor"]
            snapshot_copy["collaboration"]["bot_contributors"] = response_payload["bot_contributors"]
        storage.store_analysis_snapshot(
            conn,
            project_id=project_id,
            classification=response_payload["classification"] or "unknown",
            primary_contributor=response_payload["primary_contributor"],
            snapshot=snapshot_copy,
        )
    except Exception as exc:
        logger.warning("Failed to persist collaboration cache for %s: %s", project_id, exc)

    return response_payload


# ── Language detection ─────────────────────────────────────────────

def _detect_language(path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "jsx", ".tsx": "tsx",
        ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
        ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".swift": "swift", ".kt": "kotlin", ".scala": "scala",
        ".sh": "bash", ".bash": "bash", ".zsh": "bash",
        ".ps1": "powershell", ".bat": "batch", ".cmd": "batch",
        ".html": "html", ".htm": "html",
        ".css": "css", ".scss": "scss", ".less": "less", ".sass": "sass",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".toml": "toml", ".ini": "ini", ".xml": "xml", ".svg": "xml",
        ".md": "markdown", ".mdx": "markdown", ".txt": "plaintext",
        ".sql": "sql", ".graphql": "graphql",
        ".dockerfile": "dockerfile", ".makefile": "makefile",
        ".csv": "csv", ".tsv": "csv",
        ".log": "plaintext", ".rst": "plaintext",
        ".gitignore": "plaintext", ".env": "plaintext",
    }
    suffix = PurePosixPath(path).suffix.lower()
    name = PurePosixPath(path).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    return ext_map.get(suffix, "plaintext")
