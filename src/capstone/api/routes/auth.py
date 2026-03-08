from __future__ import annotations

import os
import secrets
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import capstone.storage as storage

router = APIRouter(prefix="/auth", tags=["auth"])

# server.py still calls configure(), so keep it
_AUTH_BASE_URL: Optional[str] = None

# local in memory sessions for the desktop app
_SESSIONS: dict[str, dict] = {}


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
    # Set your Worker URL through environment variable instead.
    global _AUTH_BASE_URL
    _AUTH_BASE_URL = "https://loom-auth.amirparsaaminian1383.workers.dev"


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
    _require_session(request)
    raise HTTPException(
        status_code=501,
        detail="profile update is not implemented in the D1 auth service yet",
    )


@router.post("/password")
def change_password(payload: ChangePasswordRequest, request: Request):
    _require_session(request)
    raise HTTPException(
        status_code=501,
        detail="password change is not implemented in the D1 auth service yet",
    )


@router.post("/logout")
def logout(request: Request):
    token = _extract_bearer(request)
    if token:
        _SESSIONS.pop(token, None)

    storage.CURRENT_USER = None
    return {"ok": True}