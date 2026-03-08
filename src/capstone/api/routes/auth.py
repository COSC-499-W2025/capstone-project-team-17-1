from __future__ import annotations

import os
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

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


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
        },
    )

    user = data.get("user")
    if not user:
        # fallback in case worker returns only username
        user = {
            "username": payload.username.strip(),
            "email": payload.email,
        }

    token = _new_token()
    _SESSIONS[token] = {"user": user}

    storage.CURRENT_USER = user["username"]
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

    token = _new_token()
    _SESSIONS[token] = {"user": user}
    _save_sessions()

    storage.CURRENT_USER = user["username"]

    return {
        "token": token,
        "user": user,
    }

@router.get("/me")
def me(request: Request):
    session = _require_session(request)
    return {"user": session["user"]}

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

    token = _extract_bearer(request)
    if token and token in _SESSIONS:
        _SESSIONS[token]["user"] = updated_user
        _save_sessions()

    storage.CURRENT_USER = updated_user["username"]

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