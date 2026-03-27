from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from .logging_utils import get_logger
from .storage import (
    fetch_latest_contributor_stats,
    link_user_to_project,
    open_db,
    store_contributor_stats,
    upsert_contributor,
    update_contributor_score,
)

logger = get_logger(__name__)

DEFAULT_WEIGHTS = {
    "commits": 0.30,
    "pull_requests": 0.25,
    "issues": 0.25,
    "reviews": 0.20,
}


def _is_noreply_email(email: str | None) -> bool:
    if not email:
        return False
    lowered = email.strip().lower()
    return (
        lowered == "noreply@github.com"
        or lowered.endswith("@users.noreply.github.com")
        or lowered.endswith("@noreply.github.com")
    )


def _normalize_email_candidate(email: object) -> str | None:
    if not isinstance(email, str):
        return None
    value = email.strip()
    if not value or _is_noreply_email(value):
        return None
    return value


def _is_bot_contributor(login: str | None, account_type: object = None) -> bool:
    if not login:
        return False
    lowered = login.strip().lower()
    if lowered.endswith("[bot]"):
        return True
    if isinstance(account_type, str) and account_type.strip().lower() == "bot":
        return True
    return False


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    if not repo_url:
        raise ValueError("Repository URL must not be empty")
    repo_url = repo_url.strip()
    if repo_url.startswith("git@"):
        _, path = repo_url.split(":", 1)
        path = path.strip("/")
    elif "://" in repo_url:
        parsed = urllib.parse.urlparse(repo_url)
        path = (parsed.path or "").strip("/")
    else:
        path = repo_url.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Unable to parse repository URL: {repo_url}")
    return parts[-2], parts[-1]


def compute_score(stats: dict, weights: dict | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    return (
        float(stats.get("commits", 0)) * float(w.get("commits", 0))
        + float(stats.get("pull_requests", 0)) * float(w.get("pull_requests", 0))
        + float(stats.get("issues", 0)) * float(w.get("issues", 0))
        + float(stats.get("reviews", 0)) * float(w.get("reviews", 0))
    )


def weights_hash(weights: dict | None = None) -> str:
    w = weights or DEFAULT_WEIGHTS
    payload = json.dumps(w, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ContributorStats:
    contributor: str
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    reviews: int = 0
    score: float = 0.0
    email: str | None = None
    first_commit_at: str | None = None
    last_commit_at: str | None = None


class GitHubClient:
    def __init__(self, token: str | None) -> None:
        self._token = token

    def _request_graphql(self, payload: dict) -> dict:
        url = "https://api.github.com/graphql"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "capstone-analyzer")
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(req) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            logger.warning("GitHub GraphQL error %s: %s", exc.code, body)
            try:
                return json.loads(body)
            except Exception:
                return {"errors": [{"message": body or str(exc)}]}

    def _request_json(self, path: str, params: dict | None = None) -> tuple[object, int]:
        base_url = "https://api.github.com"
        query = urllib.parse.urlencode(params or {})
        url = f"{base_url}{path}"
        if query:
            url = f"{url}?{query}"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "capstone-analyzer")
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(req) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload), response.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            logger.warning("GitHub API error %s for %s: %s", exc.code, url, body)
            try:
                return json.loads(body), exc.code
            except Exception:
                return {"error": body or exc.reason}, exc.code

    def get_contributors(self, owner: str, repo: str) -> list[dict]:
        data, _ = self._request_json(f"/repos/{owner}/{repo}/contributors", {"per_page": 100, "anon": "true"})
        return data if isinstance(data, list) else []

    def get_contributor_stats(self, owner: str, repo: str, retries: int = 3, delay: float = 2.0) -> list[dict]:
        for attempt in range(retries):
            data, status = self._request_json(f"/repos/{owner}/{repo}/stats/contributors")
            if status != 202:
                return data if isinstance(data, list) else []
            time.sleep(delay)
            logger.info("GitHub stats not ready, retrying (%s/%s)", attempt + 1, retries)
        return []

    def get_user_email(self, owner: str, repo: str, login: str) -> str | None:
        if not login:
            return None
        data, _ = self._request_json(f"/users/{login}")
        if not isinstance(data, dict):
            return None
        email = _normalize_email_candidate(data.get("email"))
        if email:
            return email
        # Fallback: walk recent commits by this author and pick first non-noreply email.
        commits, _ = self._request_json(
            f"/repos/{owner}/{repo}/commits",
            {"author": login, "per_page": 30},
        )
        if isinstance(commits, list) and commits:
            for commit in commits:
                if not isinstance(commit, dict):
                    continue
                # Prefer commit payload author email, fallback to committer email.
                candidate = (
                    commit.get("commit", {})
                    .get("author", {})
                    .get("email")
                )
                email = _normalize_email_candidate(candidate)
                if email:
                    return email
                candidate = (
                    commit.get("commit", {})
                    .get("committer", {})
                    .get("email")
                )
                email = _normalize_email_candidate(candidate)
                if email:
                    return email
        return None

    def search_issues_count(self, query: str) -> int:
        payload = self._request_graphql(
            {
                "query": "query($query: String!) { search(type: ISSUE, query: $query) { issueCount } }",
                "variables": {"query": query},
            }
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        search = data.get("search") if isinstance(data, dict) else None
        try:
            return int(search.get("issueCount", 0)) if isinstance(search, dict) else 0
        except (TypeError, ValueError):
            return 0


def collect_contributor_stats(
    owner: str,
    repo: str,
    *,
    client: GitHubClient,
    weights: dict | None = None,
    max_contributors: int = 50,
    include_bots: bool = False,
    progress_cb: Optional[Callable[[str, Optional[int], Optional[int]], None]] = None,
) -> list[ContributorStats]:
    if progress_cb:
        progress_cb("Fetching contributor stats", None, None)
    stats_data = client.get_contributor_stats(owner, repo)
    if progress_cb:
        progress_cb("Fetching contributor list", None, None)
    contributors_data = client.get_contributors(owner, repo)

    bot_logins: set[str] = set()
    for entry in contributors_data:
        if not isinstance(entry, dict):
            continue
        login = entry.get("login")
        if not isinstance(login, str) or not login:
            continue
        if _is_bot_contributor(login, entry.get("type")):
            bot_logins.add(login)

    stats_by_login: dict[str, ContributorStats] = {}
    for entry in stats_data:
        author = entry.get("author") if isinstance(entry, dict) else None
        login = author.get("login") if isinstance(author, dict) else None
        if not login:
            continue
        if not include_bots and (login in bot_logins or _is_bot_contributor(login, author.get("type") if isinstance(author, dict) else None)):
            continue
        stats_by_login[login] = ContributorStats(
            contributor=login,
            commits=int(entry.get("total", 0)),
        )
        weeks = entry.get("weeks") if isinstance(entry, dict) else None
        if isinstance(weeks, list):
            active_weeks = []
            for week in weeks:
                if not isinstance(week, dict):
                    continue
                try:
                    week_commits = int(week.get("c", 0) or 0)
                except Exception:
                    week_commits = 0
                if week_commits <= 0:
                    continue
                try:
                    week_start = int(week.get("w", 0) or 0)
                except Exception:
                    week_start = 0
                if week_start <= 0:
                    continue
                active_weeks.append(week_start)
            if active_weeks:
                first_ts = min(active_weeks)
                last_ts = max(active_weeks)
                stats_by_login[login].first_commit_at = datetime.fromtimestamp(first_ts, tz=UTC).strftime("%Y-%m-%d")
                # Weekly buckets represent week start; use the latest active week start as last-known active point.
                stats_by_login[login].last_commit_at = datetime.fromtimestamp(last_ts, tz=UTC).strftime("%Y-%m-%d")

    for entry in contributors_data:
        if not isinstance(entry, dict):
            continue
        login = entry.get("login")
        if not login:
            continue
        if not include_bots and (login in bot_logins or _is_bot_contributor(login, entry.get("type"))):
            continue
        if login not in stats_by_login:
            stats_by_login[login] = ContributorStats(
                contributor=login,
                commits=int(entry.get("contributions", 0)),
            )
        # Enrich email (profile -> latest commit fallback)
        # Optional helper; some test clients don't implement it.
        email = client.get_user_email(owner, repo, login) if hasattr(client, "get_user_email") else None
        if login in stats_by_login and email:
            stats_by_login[login].email = email

    ranked = sorted(
        stats_by_login.values(),
        key=lambda row: (-row.commits, row.contributor),
    )
    if max_contributors and max_contributors > 0:
        ranked = ranked[:max_contributors]

    total = len(ranked)
    for index, stats in enumerate(ranked, start=1):
        login = stats.contributor
        if progress_cb:
            progress_cb("Fetching contributor stats", index, total)
        stats.pull_requests = client.search_issues_count(
            f"repo:{owner}/{repo} type:pr assignee:{login} is:merged"
        )
        stats.issues = client.search_issues_count(
            f"repo:{owner}/{repo} type:issue assignee:{login} is:closed"
        )
        stats.reviews = client.search_issues_count(
            f"repo:{owner}/{repo} type:pr reviewed-by:{login} is:merged"
        )
        stats.score = compute_score(
            {
                "commits": stats.commits,
                "pull_requests": stats.pull_requests,
                "issues": stats.issues,
                "reviews": stats.reviews,
            },
            weights=weights,
        )

    return ranked


def sync_contributor_stats(
    repo_url: str,
    *,
    token: str | None,
    project_id: str | None = None,
    db_dir: Path | None = None,
    weights: dict | None = None,
    max_contributors: int = 50,
    include_bots: bool = False,
    client: GitHubClient | None = None,
    progress_cb: Optional[Callable[[str, Optional[int], Optional[int]], None]] = None,
) -> list[ContributorStats]:
    owner, repo = parse_repo_url(repo_url)
    resolved_project_id = project_id or f"{owner}/{repo}"
    client = client or GitHubClient(token)
    hash_value = weights_hash(weights)
    stats = collect_contributor_stats(
        owner,
        repo,
        client=client,
        weights=weights,
        max_contributors=max_contributors,
        include_bots=include_bots,
        progress_cb=progress_cb,
    )
    if progress_cb:
        progress_cb("Saving contributor stats", None, None)
    conn = open_db(db_dir)
    for row in stats:
        # upsert contributor first to get stable id
        user_id = upsert_contributor(conn, row.contributor, email=row.email)
        link_user_to_project(
            conn,
            user_id,
            resolved_project_id,
            contributor_name=row.contributor,
            first_commit_at=row.first_commit_at,
            last_commit_at=row.last_commit_at,
        )
        store_contributor_stats(
            conn,
            project_id=resolved_project_id,
            contributor=row.contributor,
            user_id=user_id,
            commits=row.commits,
            pull_requests=row.pull_requests,
            issues=row.issues,
            reviews=row.reviews,
            score=row.score,
            weights_hash=hash_value,
            source="github",
        )
    return stats


def get_contributor_rankings(
    conn,
    project_id: str,
    *,
    sort_by: str = "score",
    weights: dict | None = None,
) -> list[dict]:
    current_hash = weights_hash(weights)
    rows = fetch_latest_contributor_stats(conn, project_id)
    if not rows:
        return []

    updated = False
    for row in rows:
        if row.get("weights_hash") == current_hash:
            continue
        score = compute_score(
            {
                "commits": row.get("commits", 0),
                "pull_requests": row.get("pull_requests", 0),
                "issues": row.get("issues", 0),
                "reviews": row.get("reviews", 0),
            },
            weights=weights,
        )
        update_contributor_score(conn, row["id"], score=score, weights_hash=current_hash)
        row["score"] = score
        row["weights_hash"] = current_hash
        updated = True

    if updated:
        rows = fetch_latest_contributor_stats(conn, project_id)

    allowed = {
        "score": "score",
        "commits": "commits",
        "pull_requests": "pull_requests",
        "issues": "issues",
        "reviews": "reviews",
    }
    sort_key = allowed.get(sort_by, "score")
    return sorted(rows, key=lambda row: (-float(row.get(sort_key, 0)), row.get("contributor", "")))


__all__ = [
    "parse_repo_url",
    "compute_score",
    "weights_hash",
    "collect_contributor_stats",
    "sync_contributor_stats",
    "get_contributor_rankings",
    "GitHubClient",
    "ContributorStats",
    "DEFAULT_WEIGHTS",
]
