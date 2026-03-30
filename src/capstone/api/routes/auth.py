from __future__ import annotations

import secrets
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


def _sync_profile_to_local_db(auth_user: dict) -> None:
    """Write the Cloudflare auth profile into the local singleton user table (id=1)."""
    username = (auth_user.get("username") or "").strip()
    if not username:
        return
    github_url = (auth_user.get("github_url") or "").strip() or None
    github_handle = github_url.rstrip("/").split("/")[-1].strip() if github_url else None
    try:
        conn = storage.open_db()
        storage.upsert_user(
            conn,
            username,
            github_username=github_handle,
            github_url=github_url,
            full_name=(auth_user.get("full_name") or "").strip() or None,
            phone_number=(auth_user.get("phone_number") or "").strip() or None,
            city=(auth_user.get("city") or "").strip() or None,
            state_region=(auth_user.get("state_region") or "").strip() or None,
            portfolio_url=(auth_user.get("portfolio_url") or "").strip() or None,
        )
        storage.close_db()
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


def _get_auth_base_url() -> str:
    return (_AUTH_BASE_URL or "https://loom-auth.amirparsaaminian1383.workers.dev").rstrip("/")


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


def _request_auth(method: str, path: str, payload: dict) -> dict:
    url = f"{_get_auth_base_url()}{path}"
    try:
        response = requests.request(method, url, json=payload, timeout=15)
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


def get_authenticated_storage_user_key(request: Request) -> Optional[str]:
    username = get_authenticated_username(request)
    return storage.resolve_storage_user_key(username)

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

    data = _request_auth("POST",
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
    if payload.github_url and not user.get("github_url"):
        user["github_url"] = payload.github_url

    storage.set_current_user(user["username"])
    _sync_profile_to_local_db(user)

    token = _new_token()
    _SESSIONS[token] = {"user": user}
    _save_sessions()
    print(
        f"[auth/register] username={user.get('username')!r} "
        f"local_db={str(storage.get_database_path())!r}",
        flush=True,
    )

    return {
        "token": token,
        "user": user,
    }


@router.post("/login")
def login(payload: LoginRequest):
    data = _request_auth("POST",
        "/auth/login",
        {
            "username": payload.username.strip(),
            "password": payload.password,
        },
    )

    user = data.get("user")
    if not user:
        raise HTTPException(status_code=502, detail="auth service did not return user")

    storage.set_current_user(user["username"])
    _sync_profile_to_local_db(user)

    token = _new_token()
    _SESSIONS[token] = {"user": user}
    _save_sessions()
    print(
        f"[auth/login] username={user.get('username')!r} "
        f"local_db={str(storage.get_database_path())!r}",
        flush=True,
    )

    return {
        "token": token,
        "user": user,
    }

@router.get("/me")
def me(request: Request):
    session = _require_session(request)
    user = session["user"]
    # Always restore CURRENT_USER from the session — critical after server restart
    storage.set_current_user(user["username"])
    from capstone.portfolio_retrieval import _db_session
    from capstone.api.routes.resumes import _get_current_user_contributor_id
    with _db_session(None) as conn:
        contributor_id = _get_current_user_contributor_id(conn)
    return {"user": user, "contributor_id": contributor_id}

@router.put("/me")
def update_me(payload: UpdateProfileRequest, request: Request):
    user = _session_user(request)

    data = _request_auth("PUT",
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

    storage.set_current_user(updated_user["username"])
    _sync_profile_to_local_db(updated_user)

    token = _extract_bearer(request)
    if token and token in _SESSIONS:
        _SESSIONS[token]["user"] = updated_user
        _save_sessions()

    return {
        "ok": True,
        "user": updated_user,
    }


@router.get("/me/education")
def get_my_education(request: Request):
    _require_session(request)
    from capstone.portfolio_retrieval import _db_session
    with _db_session(None) as conn:
        entries = storage.get_user_education(conn, 1)
    return {"data": entries, "error": None}


@router.put("/me/education")
async def update_my_education(request: Request):
    _require_session(request)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    entries = payload.get("education")
    if not isinstance(entries, list):
        raise HTTPException(status_code=400, detail="education must be a list")
    for e in entries:
        if not isinstance(e, dict) or not str(e.get("university") or "").strip():
            raise HTTPException(status_code=400, detail="each entry requires a university field")
    from capstone.portfolio_retrieval import _db_session
    with _db_session(None) as conn:
        storage.replace_user_education(conn, 1, entries)
        result = storage.get_user_education(conn, 1)
    return {"data": result, "error": None}


@router.post("/password")
def change_password(payload: ChangePasswordRequest, request: Request):
    user = _session_user(request)

    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="new password must be at least 6 characters")

    data = _request_auth("POST",
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
    before_user = storage.get_current_user()
    if token:
        _SESSIONS.pop(token, None)
        _save_sessions()

    storage.set_current_user(None)
    print(
        f"[auth/logout] previous_user={before_user!r} mode='guest' "
        f"local_db={str(storage.get_database_path())!r}",
        flush=True,
    )
    return {"ok": True}
