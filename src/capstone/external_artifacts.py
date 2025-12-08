"""Helpers for discovering git remotes and fetching external PR/issue artifacts."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .logging_utils import get_logger

logger = get_logger(__name__)

_DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class RepositoryDescriptor:
    provider: str
    owner: str
    name: str
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"provider": self.provider, "owner": self.owner, "name": self.name, "url": self.url}


def repository_from_mapping(data: Mapping[str, object] | None) -> RepositoryDescriptor | None:
    if not data:
        return None
    provider = str(data.get("provider", "")).lower()
    owner = data.get("owner")
    name = data.get("name")
    url = data.get("url")
    if provider and owner and name and url:
        return RepositoryDescriptor(provider=provider, owner=str(owner), name=str(name), url=str(url))
    return None


def discover_repository(repo_path: Path, remote: str = "origin") -> RepositoryDescriptor | None:
    """Inspect git remotes to infer the backing repository metadata."""

    try:
        # rely on git itself so we don't duplicate remote parsing logic
        result = subprocess.run(
            ["git", "remote", "get-url", remote],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.debug("Unable to read git remote %s: %s", remote, exc)
        return None

    remote_url = result.stdout.strip()
    provider, slug = _parse_remote(remote_url)
    if not provider or not slug:
        return None
    owner, name = slug
    normalized_url = _normalise_remote_url(provider, owner, name)
    return RepositoryDescriptor(provider=provider, owner=owner, name=name, url=normalized_url)


def fetch_snapshot_artifacts(
    snapshot: Mapping[str, object],
    *,
    limit: int = _DEFAULT_LIMIT,
    token: str | None = None,
) -> Dict[str, List[Dict[str, object]]]:
    """Fetch artifacts given a snapshot that already stores repository metadata."""

    descriptor = repository_from_mapping(snapshot.get("repository")) if isinstance(snapshot, Mapping) else None
    if not descriptor:
        return {}
    return fetch_repository_artifacts(descriptor, limit=limit, token=token)


def fetch_repository_artifacts(
    repository: RepositoryDescriptor,
    *,
    limit: int = _DEFAULT_LIMIT,
    token: str | None = None,
) -> Dict[str, List[Dict[str, object]]]:
    """Fetch pull-request and issue artifacts for the given repository descriptor."""

    if repository.provider != "github":
        # leave hooks for other providers later, but don't crash today
        logger.debug("Repository %s uses unsupported provider %s", repository.url, repository.provider)
        return {}

    token = token or os.getenv("GITHUB_TOKEN")
    return _fetch_github_artifacts(repository.owner, repository.name, limit=limit, token=token)


def _parse_remote(remote_url: str) -> Tuple[str | None, Tuple[str, str] | None]:
    if remote_url.startswith("git@github.com:"):
        path = remote_url.split(":", 1)[1]
        slug = _split_owner_repo(path)
        return ("github", slug) if slug else (None, None)
    if remote_url.startswith("https://github.com/") or remote_url.startswith("http://github.com/"):
        path = remote_url.split("github.com/", 1)[1]
        slug = _split_owner_repo(path)
        return ("github", slug) if slug else (None, None)
    return None, None


def _split_owner_repo(path: str) -> Tuple[str, str] | None:
    trimmed = path.rstrip("/").removesuffix(".git")
    if "/" not in trimmed:
        return None
    owner, name = trimmed.split("/", 1)
    return owner, name


def _normalise_remote_url(provider: str, owner: str, name: str) -> str:
    if provider == "github":
        return f"https://github.com/{owner}/{name}"
    return f"{provider}://{owner}/{name}"


def _fetch_github_artifacts(owner: str, repo: str, *, limit: int, token: str | None) -> Dict[str, List[Dict[str, object]]]:
    pulls = _github_request(
        f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page={max(limit, 1)}",
        token=token,
    )
    issues = _github_request(
        f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&per_page={max(limit * 2, 1)}",
        token=token,
    )

    normalized_pulls = [_normalise_pull_request(entry) for entry in pulls][:limit] if isinstance(pulls, list) else []
    normalized_issues: List[Dict[str, object]] = []
    if isinstance(issues, list):
        for entry in issues:
            if "pull_request" in entry:
                continue
            normalized_issues.append(_normalise_issue(entry))
            if len(normalized_issues) >= limit:
                break

    return {
        "pull_requests": normalized_pulls,
        "issues": normalized_issues,
    }


def _github_request(url: str, *, token: str | None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "capstone-cli/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        logger.warning("Unable to fetch GitHub data from %s: %s", url, exc)
        return []


def _normalise_pull_request(entry: Mapping[str, object]) -> Dict[str, object]:
    return {
        "id": entry.get("id"),
        "number": entry.get("number"),
        "title": entry.get("title"),
        "state": entry.get("state"),
        "url": entry.get("html_url"),
        "created_at": entry.get("created_at"),
        "merged_at": entry.get("merged_at"),
        "closed_at": entry.get("closed_at"),
        "user": _extract_login(entry.get("user")),
        "merged_by": _extract_login(entry.get("merged_by")),
        "comments": entry.get("comments"),
    }


def _normalise_issue(entry: Mapping[str, object]) -> Dict[str, object]:
    return {
        "id": entry.get("id"),
        "number": entry.get("number"),
        "title": entry.get("title"),
        "state": entry.get("state"),
        "url": entry.get("html_url"),
        "created_at": entry.get("created_at"),
        "closed_at": entry.get("closed_at"),
        "user": _extract_login(entry.get("user")),
        "comments": entry.get("comments"),
    }


def _extract_login(user_info: object) -> Optional[str]:
    if isinstance(user_info, Mapping):
        login = user_info.get("login")
        return str(login) if login else None
    return None


__all__ = [
    "RepositoryDescriptor",
    "discover_repository",
    "fetch_repository_artifacts",
    "fetch_snapshot_artifacts",
    "repository_from_mapping",
]
