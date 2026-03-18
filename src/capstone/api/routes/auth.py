from __future__ import annotations

import os
import secrets
import sqlite3
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import json
from pathlib import Path
import capstone.storage as storage

router = APIRouter(prefix="/auth", tags=["auth"])

# server.py still calls configure(), so keep it
_AUTH_BASE_URL: Optional[str] = None

# local in memory sessions for the desktop app
_SESSIONS: dict[str, dict] = {}

_SESSION_FILE = Path(__file__).resolve().parent / "auth_sessions.json"


def _load_sessions() -> None:
    global _SESSIONS
    if not _SESSION_FILE.exists():
        _SESSIONS = {}
        return

    try:
        with open(_SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _SESSIONS = data if isinstance(data, dict) else {}
    except Exception:
        _SESSIONS = {}


def _save_sessions() -> None:
    try:
        with open(_SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(_SESSIONS, f, indent=2)
    except Exception:
        pass


def _migrate_guest_data_into_user_db_if_needed(username: str) -> None:
    guest_db = storage.BASE_DIR / "data" / "guest" / "capstone.db"
    if not guest_db.exists():
        return

    previous_user = storage.CURRENT_USER
    try:
        storage.CURRENT_USER = username
        user_db = storage.get_database_path()
    finally:
        storage.CURRENT_USER = previous_user

    user_db.parent.mkdir(parents=True, exist_ok=True)

    try:
        user_conn = sqlite3.connect(user_db)
        row = user_conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='project_analysis'"
        ).fetchone()
        has_project_table = bool(row and row[0])
        existing_projects = 0
        if has_project_table:
            existing_projects = user_conn.execute("SELECT COUNT(*) FROM project_analysis").fetchone()[0]
        user_conn.close()
    except Exception:
        existing_projects = 0

    if existing_projects:
        return

    try:
        source = sqlite3.connect(guest_db)
        target = sqlite3.connect(user_db)
        source.backup(target)
        target.close()
        source.close()
    except Exception:
        pass

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    github_url: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateProfileRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state_region: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def configure(db_dir: Optional[str] = None):
    # server.py passes db_dir here, but auth no longer uses SQLite locally.
    global _AUTH_BASE_URL
    _AUTH_BASE_URL = "https://loom-auth.amirparsaaminian1383.workers.dev"
    _load_sessions()


def _resolve_contributor_id(auth_user: dict) -> Optional[int]:
    """After login, find the matching git contributor in the local users table.
    Tries github handle first, then falls back to auth username.
    Creates a placeholder record if no match found so the user can generate resumes.
    """
    from capstone.portfolio_retrieval import _db_session

    github_url = (auth_user.get("github_url") or "").strip()
    github_handle = github_url.rstrip("/").split("/")[-1].lower() if github_url else ""
    auth_username = (auth_user.get("username") or "").strip()

    candidates = [h for h in [github_handle, auth_username.lower()] if h]
    if not candidates:
        return None

    try:
        with _db_session(None) as conn:
            for handle in candidates:
                row = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username) = ?", (handle,)
                ).fetchone()
                if row:
                    return row[0]

            # No match — create a placeholder so the user can start generating resumes
            email = (auth_user.get("email") or "").strip()
            identity = github_handle or auth_username
            conn.execute(
                "INSERT OR IGNORE INTO users (username, email) VALUES (?, ?)",
                (identity, email),
            )
            row = conn.execute(
                "SELECT id FROM users WHERE LOWER(username) = ?", (identity.lower(),)
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None

def _get_auth_base_url() -> str:
    base = _AUTH_BASE_URL or "https://loom-auth.amirparsaaminian1383.workers.dev"
    if not base:
        raise HTTPException(
            status_code=500,
            detail="CAPSTONE_AUTH_WORKER_URL is not configured",
        )
    return base.rstrip("/")


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _extract_bearer(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None


def _require_session(request: Request) -> dict:
    token = _extract_bearer(request)
    if not token or token not in _SESSIONS:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return _SESSIONS[token]


def _post_to_auth(path: str, payload: dict) -> dict:
    url = f"{_get_auth_base_url()}{path}"

    try:
        response = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"auth service unavailable: {exc}")

    try:
        data = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="auth service returned invalid JSON")

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=data.get("error") or data.get("detail") or "auth request failed",
        )

    return data

def _put_to_auth(path: str, payload: dict) -> dict:
    url = f"{_get_auth_base_url()}{path}"

    try:
        response = requests.put(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"auth service unavailable: {exc}")

    try:
        data = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="auth service returned invalid JSON")

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=data.get("error") or data.get("detail") or "auth request failed",
        )

    return data


def _session_user(request: Request) -> dict:
    session = _require_session(request)
    user = session.get("user")
    if not user or not user.get("username"):
        raise HTTPException(status_code=401, detail="invalid session user")
    return user


def get_authenticated_username(request: Request) -> Optional[str]:
    token = _extract_bearer(request)
    session = _SESSIONS.get(token) if token else None
    user = session.get("user") if session else None
    username = (user or {}).get("username")
    return str(username).strip() if username else None

@router.get("/bootstrap")
def bootstrap(request: Request):
    token = _extract_bearer(request)
    session = _SESSIONS.get(token) if token else None

    return {
        "has_users": True,
        "authenticated": session is not None,
        "user": session["user"] if session else None,
    }


@router.post("/register")
def register(payload: RegisterRequest):
    if not payload.username.strip():
        raise HTTPException(status_code=400, detail="username is required")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")

    data = _post_to_auth(
        "/auth/register",
        {
            "username": payload.username.strip(),
            "password": payload.password,
            "email": payload.email,
            "github_url": payload.github_url,
        },
    )

    user = data.get("user")
    if not user:
        user = {
            "username": payload.username.strip(),
            "email": payload.email,
            "github_url": payload.github_url,
        }
    # Ensure github_url is in user dict for contributor resolution
    if payload.github_url and not user.get("github_url"):
        user["github_url"] = payload.github_url

    storage.CURRENT_USER = user["username"]
    _migrate_guest_data_into_user_db_if_needed(user["username"])
    contributor_id = _resolve_contributor_id(user)

    token = _new_token()
    _SESSIONS[token] = {"user": user, "contributor_id": contributor_id}
    _save_sessions()

    return {
        "token": token,
        "user": user,
    }


@router.post("/login")
def login(payload: LoginRequest):
    data = _post_to_auth(
        "/auth/login",
        {
            "username": payload.username.strip(),
            "password": payload.password,
        },
    )

    user = data.get("user")
    if not user:
        raise HTTPException(status_code=502, detail="auth service did not return user")

    storage.CURRENT_USER = user["username"]
    _migrate_guest_data_into_user_db_if_needed(user["username"])
    contributor_id = _resolve_contributor_id(user)

    token = _new_token()
    _SESSIONS[token] = {"user": user, "contributor_id": contributor_id}
    _save_sessions()

    return {
        "token": token,
        "user": user,
    }

@router.get("/me")
def me(request: Request):
    session = _require_session(request)
    user = session["user"]
    # Always restore CURRENT_USER from the session — critical after server restart
    storage.CURRENT_USER = user["username"]
    # Re-resolve contributor_id if missing (sessions persisted before this change)
    if "contributor_id" not in session:
        contributor_id = _resolve_contributor_id(user)
        session["contributor_id"] = contributor_id
        _save_sessions()
    return {"user": user}

@router.put("/me")
def update_me(payload: UpdateProfileRequest, request: Request):
    user = _session_user(request)

    data = _put_to_auth(
        "/auth/me",
        {
            "username": user["username"],
            "email": payload.email,
            "full_name": payload.full_name,
            "phone_number": payload.phone_number,
            "city": payload.city,
            "state_region": payload.state_region,
            "github_url": payload.github_url,
            "portfolio_url": payload.portfolio_url,
        },
    )

    updated_user = data.get("user")
    if not updated_user:
        raise HTTPException(status_code=502, detail="auth service did not return updated user")

    storage.CURRENT_USER = updated_user["username"]
    contributor_id = _resolve_contributor_id(updated_user)

    token = _extract_bearer(request)
    if token and token in _SESSIONS:
        _SESSIONS[token]["user"] = updated_user
        _SESSIONS[token]["contributor_id"] = contributor_id
        _save_sessions()

    return {
        "ok": True,
        "user": updated_user,
    }


@router.post("/password")
def change_password(payload: ChangePasswordRequest, request: Request):
    user = _session_user(request)

    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="new password must be at least 6 characters")

    data = _post_to_auth(
        "/auth/password",
        {
            "username": user["username"],
            "current_password": payload.current_password,
            "new_password": payload.new_password,
        },
    )

    return {
        "ok": True,
        "detail": data.get("detail") or "password updated successfully",
    }


@router.post("/logout")
def logout(request: Request):
    token = _extract_bearer(request)
    if token:
        _SESSIONS.pop(token, None)
        _save_sessions()

    storage.CURRENT_USER = None
    return {"ok": True}
