from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import capstone.storage as storage

router = APIRouter(prefix="/auth", tags=["auth"])

_DB_DIR: Optional[str] = None
# In-memory session map; users persist in DB
_SESSIONS: dict[str, int] = {}
_ITERATIONS = 200_000


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


def configure(db_dir: Optional[str]) -> None:
    global _DB_DIR
    _DB_DIR = db_dir


def _open_conn():
    if _DB_DIR:
        return storage.open_db(Path(_DB_DIR))
    return storage.open_db()


def _ensure_auth_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            user_id INTEGER NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_accounts_user_id
        ON auth_accounts (user_id)
        """
    )
    conn.commit()


def _hash_password(password: str, salt_hex: str) -> str:
    # hash password
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        _ITERATIONS,
    )
    return digest.hex()


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _extract_bearer(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None


def _require_user_id(request: Request) -> int:
    # Centralized bearer-token validation
    token = _extract_bearer(request)
    if not token or token not in _SESSIONS:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return int(_SESSIONS[token])


def _user_payload(conn, user_id: int) -> dict:
    row = conn.execute(
        """
        SELECT id, username, email, full_name, phone_number, city, state_region,
               github_url, portfolio_url, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone_number": row["phone_number"],
        "city": row["city"],
        "state_region": row["state_region"],
        "github_url": row["github_url"],
        "portfolio_url": row["portfolio_url"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/bootstrap")
def bootstrap(request: Request):
    token = _extract_bearer(request)
    conn = _open_conn()
    try:
        _ensure_auth_tables(conn)
        row = conn.execute("SELECT COUNT(*) AS c FROM auth_accounts").fetchone()
        has_users = bool(row and int(row["c"]) > 0)
        user = None
        authenticated = False
        if token and token in _SESSIONS:
            user_id = _SESSIONS[token]
            user = _user_payload(conn, user_id)
            authenticated = True
        return {"has_users": has_users, "authenticated": authenticated, "user": user}
    finally:
        conn.close()


@router.post("/register")
def register(payload: RegisterRequest):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")

    conn = _open_conn()
    try:
        _ensure_auth_tables(conn)
        existing = conn.execute(
            "SELECT 1 FROM auth_accounts WHERE username = ? LIMIT 1",
            (username,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="username already exists")

        user_id = storage.upsert_user(conn, username, email=payload.email)
        salt_hex = secrets.token_hex(16)
        password_hash = _hash_password(payload.password, salt_hex)
        conn.execute(
            """
            INSERT INTO auth_accounts (username, password_hash, salt, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, salt_hex, user_id),
        )
        conn.commit()

        token = _new_token()
        _SESSIONS[token] = int(user_id)
        user = _user_payload(conn, int(user_id))
        return {"token": token, "user": user}
    finally:
        conn.close()


@router.post("/login")
def login(payload: LoginRequest):
    username = payload.username.strip()
    conn = _open_conn()
    try:
        _ensure_auth_tables(conn)
        row = conn.execute(
            """
            SELECT user_id, password_hash, salt
            FROM auth_accounts
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="invalid username or password")

        candidate = _hash_password(payload.password, row["salt"])
        if not hmac.compare_digest(candidate, row["password_hash"]):
            raise HTTPException(status_code=401, detail="invalid username or password")

        token = _new_token()
        user_id = int(row["user_id"])
        _SESSIONS[token] = user_id
        user = _user_payload(conn, user_id)
        return {"token": token, "user": user}
    finally:
        conn.close()


@router.get("/me")
def me(request: Request):
    user_id = _require_user_id(request)
    conn = _open_conn()
    try:
        return {"user": _user_payload(conn, user_id)}
    finally:
        conn.close()


@router.put("/me")
def update_me(payload: UpdateProfileRequest, request: Request):
    user_id = _require_user_id(request)
    conn = _open_conn()
    try:
        conn.execute(
            """
            UPDATE users
            SET
                email = ?,
                full_name = ?,
                phone_number = ?,
                city = ?,
                state_region = ?,
                github_url = ?,
                portfolio_url = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                (payload.email or None),
                (payload.full_name or None),
                (payload.phone_number or None),
                (payload.city or None),
                (payload.state_region or None),
                (payload.github_url or None),
                (payload.portfolio_url or None),
                user_id,
            ),
        )
        conn.commit()
        return {"ok": True, "user": _user_payload(conn, user_id)}
    finally:
        conn.close()


@router.post("/password")
def change_password(payload: ChangePasswordRequest, request: Request):
    user_id = _require_user_id(request)
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="new password must be at least 6 characters")
    conn = _open_conn()
    try:
        row = conn.execute(
            "SELECT password_hash, salt FROM auth_accounts WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="auth account not found")
        old_candidate = _hash_password(payload.current_password, row["salt"])
        if not hmac.compare_digest(old_candidate, row["password_hash"]):
            raise HTTPException(status_code=401, detail="current password is incorrect")

        new_salt = secrets.token_hex(16)
        new_hash = _hash_password(payload.new_password, new_salt)
        conn.execute(
            """
            UPDATE auth_accounts
            SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (new_hash, new_salt, user_id),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/logout")
def logout(request: Request):
    token = _extract_bearer(request)
    if token:
        _SESSIONS.pop(token, None)
    return {"ok": True}
