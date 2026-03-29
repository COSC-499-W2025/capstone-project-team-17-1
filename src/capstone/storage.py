"""
Lightweight storage utilities used to persist analysis data.

This module centralizes:
- DB open/close lifecycle
- Schema initialization + simple migrations
- Snapshot persistence/retrieval
- GitHub source persistence (repo URL + encrypted token)
- Contributor stats persistence/retrieval
- Project evidence persistence/retrieval (metrics/feedback/evaluations)
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Iterable, Optional
import json
from datetime import datetime
from .config import CONFIG_SECRET
from .logging_utils import get_logger
import os
from pathlib import Path
import sys

logger = get_logger(__name__)

def _user_dir(username: str) -> str:
    """Return a filesystem-safe, case-sensitive directory name for a username.
    Uses SHA256 so 'erensun408' and 'ErenSun408' always get different dirs,
    even on case-insensitive filesystems (Windows/macOS).
    """
    return hashlib.sha256(username.encode()).hexdigest()[:24]


def get_user_db_path():

    global CURRENT_USER

    if CURRENT_USER is None:
        return BASE_DIR / "guest_capstone.db"

    path = BASE_DIR / "users" / _user_dir(CURRENT_USER)
    path.mkdir(parents=True, exist_ok=True)

    return path / "capstone.db"

def _load_dotenv():
    """Load key=value pairs from a .env file in the project root (if present).
    Only sets variables that are not already set in the environment.
    No external dependencies required.
    """
    # Walk up from this file to find the project root (.env lives next to pyproject.toml)
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent, here.parent.parent.parent]:
        env_file = parent / ".env"
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            break

_load_dotenv()


def get_base_data_dir():

    local_appdata = os.getenv("LOCALAPPDATA")
    appdata = os.getenv("APPDATA")
    home = os.path.expanduser("~")
    root = local_appdata or appdata or home
    base = Path(root) / "Loom"

    base.mkdir(parents=True, exist_ok=True)
    return base

BASE_DIR = get_base_data_dir()
_DB_HANDLE: Optional[sqlite3.Connection] = None
_DB_PATH: Optional[Path] = None
CURRENT_USER = None
_SCHEMA_READY: set[str] = set()

def _is_noreply_email(email: str | None) -> bool:
    if not email:
        return False
    lowered = email.strip().lower()
    if not lowered:
        return False
    return (
        lowered == "noreply@github.com"
        or lowered.endswith("@users.noreply.github.com")
        or lowered.endswith("@noreply.github.com")
    )


def _normalize_user_email(email: str | None) -> str | None:
    if not email:
        return None
    value = email.strip()
    if not value:
        return None
    if _is_noreply_email(value):
        return None
    return value


def _default_github_url(username: str | None) -> str | None:
    if username is None:
        return None
    token = str(username).strip()
    if not token:
        return None
    return f"https://github.com/{token}"


def _has_required_schema(conn: sqlite3.Connection) -> bool:
    """
    Return True when the core tables needed for read endpoints already exist.
    This allows the app to keep serving reads if the database is temporarily
    opened in a readonly state and schema bootstrapping cannot run.
    """
    required = {
        "project_analysis",
        "files",
        "uploads",
        "error_analysis_results",
    }
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    existing = {str(row[0]) for row in rows}
    return required.issubset(existing)


# Schema + migrations

def _initialize_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes. No migration logic — see _run_migrations."""

    # --- Parent tables (no FKs) ---

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            username TEXT NOT NULL,
            password_hash TEXT,
            github_username TEXT,
            github_url TEXT,
            github_token_enc TEXT,
            full_name TEXT,
            phone_number TEXT,
            city TEXT,
            state_region TEXT,
            portfolio_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
    """)
    # Ensure singleton row exists so resumes/user_education FKs are always satisfiable.
    # upsert_user() overwrites this with the real login profile on first sign-in.
    conn.execute("INSERT OR IGNORE INTO user (id, username) VALUES (1, 'guest')")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS contributors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_username TEXT NOT NULL,
            email TEXT,
            github_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # project_metadata removed in M21 — superseded by projects.status / first_commit_at / last_commit_at
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      TEXT NOT NULL UNIQUE,
            name            TEXT NOT NULL,
            source          TEXT NOT NULL DEFAULT 'zip',
            github_url      TEXT,
            github_branch   TEXT,
            has_git         INTEGER NOT NULL DEFAULT 0,
            type            TEXT,
            status          TEXT NOT NULL DEFAULT 'ongoing',
            first_commit_at TEXT,
            last_commit_at  TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            hash TEXT UNIQUE,
            size_bytes INTEGER NOT NULL,
            mime TEXT,
            path TEXT NOT NULL,
            ref_count INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS privacy_consent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_consent INTEGER DEFAULT 0,
            external_consent INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)

    # github_projects removed in M21 — superseded by projects (source, github_url, github_branch)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS github_auth (
            id INTEGER PRIMARY KEY,
            access_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- Child tables ---

    conn.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT NOT NULL,
            original_name TEXT,
            uploader TEXT,
            source TEXT,
            hash TEXT,
            file_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (file_id) REFERENCES files(file_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            classification TEXT NOT NULL,
            primary_contributor TEXT,
            snapshot JSON NOT NULL,
            repo_url TEXT,
            token_enc TEXT,
            zip_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_overrides (
            project_id TEXT PRIMARY KEY,
            key_role TEXT,
            evidence TEXT,
            portfolio_blurb TEXT,
            resume_bullets_json TEXT,
            selected INTEGER,
            rank INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_analysis_results (
            project_id TEXT PRIMARY KEY,
            errors_json TEXT,
            updated_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            filename TEXT,
            content_type TEXT,
            image_b64 TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            label TEXT,
            value TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
    """)

    # contributor_stats removed in M22 — superseded by project_contributors
    # user_projects removed in M22 — superseded by project_contributors
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_contributors (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      TEXT NOT NULL,
            contributor_id  INTEGER NOT NULL,
            first_commit_at TEXT,
            last_commit_at  TEXT,
            commits         INTEGER NOT NULL DEFAULT 0,
            pull_requests   INTEGER NOT NULL DEFAULT 0,
            issues          INTEGER NOT NULL DEFAULT 0,
            reviews         INTEGER NOT NULL DEFAULT 0,
            score           REAL NOT NULL DEFAULT 0,
            weights_hash    TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (project_id, contributor_id),
            FOREIGN KEY (contributor_id) REFERENCES contributors(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL DEFAULT 'Default Resume',
            target_role TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resume_sections (
            id TEXT PRIMARY KEY,
            resume_id TEXT NOT NULL,
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            is_custom INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resume_items (
            id TEXT PRIMARY KEY,
            section_id TEXT NOT NULL,
            title TEXT,
            subtitle TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            content TEXT,
            bullets_json TEXT,
            metadata_json TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES resume_sections(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            university TEXT NOT NULL,
            degree TEXT,
            start_date TEXT,
            end_date TEXT,
            city TEXT,
            state TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_images_project ON project_images (project_id, created_at)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_contributors_identity ON contributors (github_username, COALESCE(email, ''))")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_contributors_project ON project_contributors (project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_contributors_contributor ON project_contributors (contributor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes (user_id, updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resume_sections_resume ON resume_sections (resume_id, sort_order)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resume_items_section ON resume_items (section_id, sort_order)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_evidence_project ON project_evidence (project_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files (hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uploads_file ON uploads (file_id)")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


_SQLITE_INTERNAL = {"sqlite_sequence", "sqlite_stat1", "sqlite_stat2", "sqlite_stat3", "sqlite_stat4"}


def _sqlite_affinity(type_str: str) -> str:
    """Return the SQLite type affinity for a declared column type.

    Follows the SQLite affinity rules so that equivalent types (e.g. JSON and
    TEXT, or INT and INTEGER) compare equal during schema checks.
    """
    t = type_str.upper()
    if "INT" in t:
        return "INTEGER"
    if any(x in t for x in ("CHAR", "CLOB", "TEXT", "JSON")):
        return "TEXT"
    if t == "" or "BLOB" in t:
        return "BLOB"
    if any(x in t for x in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return "NUMERIC"


def _schema_matches_expected(conn: sqlite3.Connection) -> bool:
    """Return True when the live DB schema matches _initialize_schema output.

    Rules:
    - Expected table missing from live DB: OK — CREATE TABLE IF NOT EXISTS will add it.
    - Extra legacy tables in live DB: OK — ignored.
    - Shared table with ANY column difference (extra or missing): RESET needed.
    """
    ref = sqlite3.connect(":memory:")
    try:
        _initialize_schema(ref)
        expected_tables = {
            row[0] for row in ref.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        } - _SQLITE_INTERNAL
        actual_tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        } - _SQLITE_INTERNAL
        for table in expected_tables & actual_tables:
            expected_cols = {
                row[1]
                for row in ref.execute(f"PRAGMA table_info('{table}')")
            }
            actual_cols = {
                row[1]
                for row in conn.execute(f"PRAGMA table_info('{table}')")
            }
            if expected_cols != actual_cols:
                logger.info(
                    "Schema mismatch in table %r: expected %s, got %s",
                    table,
                    expected_cols - actual_cols,
                    actual_cols - expected_cols,
                )
                return False
        return True
    finally:
        ref.close()


def _nuclear_reset(conn: sqlite3.Connection) -> None:
    """Drop all user tables and reinitialise from _initialize_schema."""
    logger.warning("Schema mismatch detected — dropping all tables and reinitialising")
    conn.execute("PRAGMA foreign_keys = OFF")
    tables = [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS [{table}]")
    conn.commit()
    _initialize_schema(conn)


def _migrate_legacy_contributor_stats(conn: sqlite3.Connection) -> None:
    """One-shot migration: contributor_stats (pre-M22) → contributors + project_contributors.

    Runs only when the legacy contributor_stats table is present.  After
    migration the table is dropped so this is idempotent across restarts.
    """
    if not conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='contributor_stats'"
    ).fetchone():
        return

    conn.execute("PRAGMA foreign_keys = OFF")

    # Ensure user_id column exists (added by old M2).
    cs_cols = {row[1] for row in conn.execute("PRAGMA table_info(contributor_stats)")}
    if "user_id" not in cs_cols:
        conn.execute("ALTER TABLE contributor_stats ADD COLUMN user_id INTEGER")
    if "weights_hash" not in cs_cols:
        conn.execute("ALTER TABLE contributor_stats ADD COLUMN weights_hash TEXT")

    # Resolve contributor TEXT → contributors.id, creating rows as needed.
    contributors_list = conn.execute(
        "SELECT DISTINCT contributor FROM contributor_stats "
        "WHERE contributor IS NOT NULL AND TRIM(contributor) != '' AND user_id IS NULL"
    ).fetchall()
    for (contributor,) in contributors_list:
        row = conn.execute(
            "SELECT id FROM contributors WHERE github_username = ? ORDER BY id LIMIT 1",
            (contributor,),
        ).fetchone()
        if row:
            uid = int(row[0])
        else:
            cur = conn.execute(
                "INSERT INTO contributors (github_username, email, github_url) VALUES (?, NULL, ?)",
                (contributor, _default_github_url(contributor)),
            )
            uid = int(cur.lastrowid)
        conn.execute(
            "UPDATE contributor_stats SET user_id = ? WHERE contributor = ? AND user_id IS NULL",
            (uid, contributor),
        )

    # Merge latest stats per (project_id, user_id) into project_contributors.
    conn.execute("""
        INSERT OR IGNORE INTO project_contributors
            (project_id, contributor_id, commits, pull_requests, issues, reviews,
             score, weights_hash, created_at)
        SELECT cs.project_id, cs.user_id, cs.commits, cs.pull_requests, cs.issues,
               cs.reviews, cs.score, cs.weights_hash, cs.created_at
        FROM contributor_stats cs
        WHERE cs.user_id IS NOT NULL
          AND cs.id IN (
              SELECT MAX(id) FROM contributor_stats
              WHERE user_id IS NOT NULL GROUP BY project_id, user_id
          )
    """)

    conn.execute("DROP TABLE contributor_stats")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Check schema currency; nuclear-reset when stale, then apply legacy data migrations."""
    if not _schema_matches_expected(conn):
        _nuclear_reset(conn)
    _migrate_legacy_contributor_stats(conn)


def save_error_results(conn, project_id: str, errors: list[dict]):
    conn.execute("""
        INSERT INTO error_analysis_results (project_id, errors_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(project_id)
        DO UPDATE SET
            errors_json = excluded.errors_json,
            updated_at = excluded.updated_at
    """, (project_id, json.dumps(errors), datetime.utcnow().isoformat()))
    conn.commit()


def fetch_error_results(conn):
    rows = conn.execute("""
        SELECT project_id, errors_json
        FROM error_analysis_results
    """).fetchall()

    # No rows means analysis has never been run; return None so the caller
    # can distinguish "never analyzed" from "analyzed and clean" (empty list).
    if not rows:
        return None

    results = []
    for row in rows:
        project_id, errors_json = row
        errors = json.loads(errors_json) if errors_json else []
        for err in errors:
            err["project_id"] = project_id
        results.extend(errors)

    return results

def _repair_user_identity_links(conn: sqlite3.Connection) -> None:
    """
    Repair user identity rows that were merged by generic noreply emails.
    """
    users = conn.execute(
        "SELECT id, github_username, email FROM contributors ORDER BY id"
    ).fetchall()

    # First pass: normalize/remove noreply emails while preserving uniqueness.
    for user_id, username, email in users:
        if not _is_noreply_email(email):
            continue
        existing = conn.execute(
            "SELECT id FROM contributors WHERE github_username = ? AND (email IS NULL OR TRIM(email) = '') ORDER BY id LIMIT 1",
            (username,),
        ).fetchone()
        if existing and int(existing[0]) != int(user_id):
            canonical_id = int(existing[0])
            old_projects = conn.execute(
                "SELECT project_id FROM project_contributors WHERE contributor_id = ?",
                (int(user_id),),
            ).fetchall()
            for (project_id,) in old_projects:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO project_contributors (project_id, contributor_id)
                    VALUES (?, ?)
                    """,
                    (project_id, canonical_id),
                )
            conn.execute("DELETE FROM project_contributors WHERE contributor_id = ?", (int(user_id),))
            conn.execute("DELETE FROM contributors WHERE id = ?", (int(user_id),))
        else:
            conn.execute("UPDATE contributors SET email = NULL WHERE id = ?", (int(user_id),))

    # Second pass: no-op after M22 (contributor_stats / user_projects are gone).
    # Kept as a guard so M12 remains callable on pre-M22 DBs.
    if not conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='contributor_stats'"
    ).fetchone():
        return

    contributors = conn.execute(
        "SELECT DISTINCT contributor FROM contributor_stats WHERE contributor IS NOT NULL AND TRIM(contributor) != ''"
    ).fetchall()
    for (contributor,) in contributors:
        row = conn.execute(
            "SELECT id FROM contributors WHERE github_username = ? ORDER BY id LIMIT 1",
            (contributor,),
        ).fetchone()
        if row:
            canonical_user_id = int(row[0])
        else:
            cursor = conn.execute(
                "INSERT INTO contributors (github_username, email, github_url) VALUES (?, NULL, ?)",
                (contributor, _default_github_url(contributor)),
            )
            canonical_user_id = int(cursor.lastrowid)

        conn.execute(
            "UPDATE contributor_stats SET user_id = ? WHERE contributor = ?",
            (canonical_user_id, contributor),
        )

        projects = conn.execute(
            """
            SELECT DISTINCT cs.project_id
            FROM contributor_stats cs
            JOIN projects p ON p.project_id = cs.project_id
            WHERE cs.contributor = ? AND cs.project_id IS NOT NULL
            """,
            (contributor,),
        ).fetchall()
        for (project_id,) in projects:
            conn.execute(
                """
                INSERT OR IGNORE INTO project_contributors (contributor_id, project_id)
                VALUES (?, ?)
                """,
                (canonical_user_id, project_id),
            )

def set_current_user(user_id: str | None):
    global CURRENT_USER
    CURRENT_USER = user_id

_UNSET = object()  # sentinel — distinguishes "not passed" from None


def get_database_path(user=_UNSET) -> Path:
    # Allow overriding the DB path for local debugging.
    # Uncomment the line below (and set LOOM_DB_PATH=debug_db/capstone.db) to share one DB across all users.
    # override = os.getenv("LOOM_DB_PATH")
    override = None
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    effective_user = CURRENT_USER if user is _UNSET else user
    if effective_user:
        path = BASE_DIR / "data" / "users" / _user_dir(effective_user)
        path.mkdir(parents=True, exist_ok=True)
        return path / "capstone.db"

    path = BASE_DIR / "data" / "guest"
    path.mkdir(parents=True, exist_ok=True)
    return path / "capstone.db"

# -----------------------------
# DB lifecycle
# -----------------------------
def open_db(base_dir: Path | None = None, *, user=_UNSET) -> sqlite3.Connection:
    target_dir = base_dir or BASE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = get_database_path(user=user)
    db_key = str(db_path.resolve())

    logger.info("Opening database at %s", db_path)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
    except Exception:
        pass

    if db_key not in _SCHEMA_READY:
        try:
            _initialize_schema(conn)
            _run_migrations(conn)
            _SCHEMA_READY.add(db_key)
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "readonly" not in message and "locked" not in message:
                raise
            if not _has_required_schema(conn):
                raise
            _SCHEMA_READY.add(db_key)
            logger.warning(
                "Skipping schema initialization for %s because database is temporarily unavailable for writes: %s",
                db_path,
                exc,
            )

    return conn

def close_db() -> None:
    """Close the shared database handle if it exists."""
    global _DB_HANDLE, _DB_PATH
    if _DB_HANDLE is not None:
        try:
            _DB_HANDLE.close()
        except Exception:  # pragma: no cover
            logger.warning("Failed to close DB cleanly", exc_info=True)
        finally:
            _DB_HANDLE = None
            _DB_PATH = None

# Snapshots

def store_analysis_snapshot(
    conn: sqlite3.Connection,
    project_id: str,
    classification: str = "unknown",
    primary_contributor: str | None = None,
    snapshot: dict | None = None,
    zip_path: str | None = None,
    repo_url: str | None = None,
) -> None:
    """Insert a new snapshot row for a project and upsert the projects table."""
    if not project_id:
        raise ValueError("project_id must be provided")

    doc = dict(snapshot or {})
    doc.setdefault("project_id", project_id)
    doc.setdefault("classification", classification)
    doc.setdefault("primary_contributor", primary_contributor)

    # Ensure the parent projects row exists before inserting into project_analysis (FK)
    _collab = doc.get("collaboration") or {}
    _first = _collab.get("first_commit_date")
    _last = _collab.get("last_commit_date")
    _source = "zip" if zip_path else "github"
    _github_url = repo_url or doc.get("repo_url") or doc.get("github_url")
    _type = classification if classification not in ("unknown", "") else None
    upsert_project(
        conn,
        project_id,
        source=_source,
        github_url=_github_url,
        has_git=bool(_first),
        type=_type,
        first_commit_at=_first,
        last_commit_at=_last,
    )

    payload = json.dumps(doc)
    conn.execute(
        """
        INSERT INTO project_analysis (
            project_id,
            classification,
            primary_contributor,
            snapshot,
            zip_path
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, classification, primary_contributor, payload, zip_path),
    )

    conn.commit()


def fetch_latest_snapshot(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Return the most recent snapshot for the given project, if any."""
    if not project_id:
        return None

    try:
        cursor = conn.execute(
            """
            SELECT snapshot
            FROM project_analysis
            WHERE project_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
            """,
            (project_id,),
        )
    except sqlite3.OperationalError:
        cursor = conn.execute(
            """
            SELECT snapshot
            FROM project_analysis
            WHERE project_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (project_id,),
        )
    row = cursor.fetchone()
    return json.loads(row[0]) if row else None

def fetch_latest_snapshots_with_zip(conn: sqlite3.Connection) -> list[dict]:
    """
    Returns the latest snapshot + zip_path for each project.
    Used exclusively for AI error analysis.
    Uses MAX(id) rowid-based selection to match recent_projects.py and avoid
    datetime() parsing failures on rows with NULL or non-standard created_at.
    """

    rows = conn.execute(
        """
        SELECT pa.project_id,
               pa.snapshot,
               pa.zip_path,
               pa.created_at
        FROM project_analysis pa
        WHERE pa.id IN (
            SELECT MAX(id)
            FROM project_analysis
            GROUP BY project_id
        )
        ORDER BY pa.id DESC
        """
    ).fetchall()

    snapshots = []

    for project_id, snapshot_json, zip_path, created_at in rows:
        try:
            snapshot = json.loads(snapshot_json)
        except Exception:
            snapshot = {}

        snapshots.append({
            "project_id": project_id,
            "snapshot": snapshot,
            "zip_path": zip_path,
            "created_at": created_at,
        })

    return snapshots

def fetch_project_snapshot_history(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    limit: int | None = None,
) -> list[dict]:
    """
    Fetch ALL snapshots for one project (history), newest-first by default.

    This supports Milestone #21 (incremental information over time):
    multiple uploads for the same project should produce multiple rows.
    """
    if not project_id:
        return []

    sql = """
        SELECT
            id,
            project_id,
            classification,
            primary_contributor,
            snapshot,
            created_at
        FROM project_analysis
        WHERE project_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
    """
    params: tuple = (project_id,)

    if limit is not None:
        if int(limit) <= 0:
            return []
        sql += " LIMIT ?"
        params = (project_id, int(limit))

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        sql = """
            SELECT
                NULL AS id,
                project_id,
                classification,
                primary_contributor,
                snapshot,
                created_at
            FROM project_analysis
            WHERE project_id = ?
            ORDER BY datetime(created_at) DESC
        """
        if limit is not None:
            if int(limit) <= 0:
                return []
            sql += " LIMIT ?"
            params = (project_id, int(limit))
        rows = conn.execute(sql, params).fetchall()

    out: list[dict] = []
    for row_id, pid, classification, contributor, snapshot_json, created_at in rows:
        try:
            snap = json.loads(snapshot_json)
        except Exception:
            snap = {}
        out.append(
            {
                "id": row_id,
                "project_id": pid,
                "classification": classification,
                "primary_contributor": contributor,
                "created_at": created_at,
                "snapshot": snap,
            }
        )
    return out

def fetch_latest_snapshots(conn: sqlite3.Connection, limit: int | None = None) -> list[dict]:
    """
    Return newest snapshot for every project saved in the database.
    Each item contains snapshot + metadata.
    """
    if limit is not None and int(limit) <= 0:
        return []

    try:
        cursor = conn.execute(
            f"""
            WITH latest_time AS (
                SELECT project_id, MAX(created_at) AS created_at
                FROM project_analysis
                GROUP BY project_id
            ),
            latest_row AS (
                SELECT pa.project_id, MAX(pa.id) AS id
                FROM project_analysis pa
                JOIN latest_time lt
                  ON lt.project_id = pa.project_id
                 AND lt.created_at = pa.created_at
                GROUP BY pa.project_id
            )
            SELECT a.project_id, a.classification, a.primary_contributor, a.snapshot, a.created_at
            FROM project_analysis a
            JOIN latest_row lr ON lr.id = a.id
            ORDER BY datetime(a.created_at) DESC, a.id DESC
            {"LIMIT ?" if limit is not None else ""}
            """,
            (() if limit is None else (int(limit),)),
        )
    except sqlite3.OperationalError:
        cursor = conn.execute(
            f"""
            WITH latest_time AS (
                SELECT project_id, MAX(created_at) AS created_at
                FROM project_analysis
                GROUP BY project_id
            )
            SELECT a.project_id, a.classification, a.primary_contributor, a.snapshot, a.created_at
            FROM project_analysis a
            JOIN latest_time lt
              ON lt.project_id = a.project_id
             AND lt.created_at = a.created_at
            ORDER BY datetime(a.created_at) DESC
            {"LIMIT ?" if limit is not None else ""}
            """,
            (() if limit is None else (int(limit),)),
        )

    rows = cursor.fetchall()
    payload: list[dict] = []
    for project_id, classification, contributor, snapshot_json, created_at in rows:
        try:
            snapshot = json.loads(snapshot_json)
        except Exception:
            snapshot = {}
        payload.append(
            {
                "project_id": project_id,
                "classification": classification,
                "primary_contributor": contributor,
                "created_at": created_at,
                "snapshot": snapshot,
            }
        )
    return payload


def fetch_latest_snapshots_for_projects(
    conn: sqlite3.Connection,
    project_ids: Iterable[str],
) -> dict[str, dict | None]:
    """
    Return {project_id: latest_snapshot_dict_or_None} for ONLY the given project_ids.
    One SQL query (no N+1).
    """
    ids = [str(pid) for pid in project_ids if pid]
    if not ids:
        return {}

    placeholders = ",".join(["?"] * len(ids))

    try:
        rows = conn.execute(
            f"""
            WITH latest_time AS (
                SELECT project_id, MAX(created_at) AS created_at
                FROM project_analysis
                WHERE project_id IN ({placeholders})
                GROUP BY project_id
            ),
            latest_row AS (
                SELECT pa.project_id, MAX(pa.id) AS id
                FROM project_analysis pa
                JOIN latest_time lt
                  ON lt.project_id = pa.project_id
                 AND lt.created_at = pa.created_at
                GROUP BY pa.project_id
            )
            SELECT pa.project_id, pa.snapshot
            FROM project_analysis pa
            JOIN latest_row lr ON lr.id = pa.id
            """,
            ids,
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            f"""
            WITH latest_time AS (
                SELECT project_id, MAX(created_at) AS created_at
                FROM project_analysis
                WHERE project_id IN ({placeholders})
                GROUP BY project_id
            )
            SELECT pa.project_id, pa.snapshot
            FROM project_analysis pa
            JOIN latest_time lt
              ON lt.project_id = pa.project_id
             AND lt.created_at = pa.created_at
            """,
            ids,
        ).fetchall()

    out: dict[str, dict | None] = {pid: None for pid in ids}
    for pid, snap_json in rows:
        try:
            out[pid] = json.loads(snap_json)
        except Exception:
            out[pid] = {}
    return out



# GitHub source (repo URL + token)

def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _encrypt_token(token: str, secret: str = CONFIG_SECRET) -> str:
    payload = token.encode("utf-8")
    key = _derive_key(secret)
    encrypted = _xor_bytes(payload, key)
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def _decrypt_token(token_enc: str, secret: str = CONFIG_SECRET) -> str:
    raw = base64.urlsafe_b64decode(token_enc.encode("ascii"))
    key = _derive_key(secret)
    decrypted = _xor_bytes(raw, key)
    return decrypted.decode("utf-8")


def store_github_source(
    conn: sqlite3.Connection,
    project_id: str,
    repo_url: str,
    token: str,
) -> None:
    if not project_id:
        raise ValueError("project_id must be provided")
    if not repo_url:
        raise ValueError("repo_url must be provided")
    if not token:
        raise ValueError("token must be provided")

    token_enc = _encrypt_token(token)

    # Ensure the parent projects row exists (FK constraint added in M24)
    upsert_project(conn, project_id, source="github", github_url=repo_url)

    existing = conn.execute(
        "SELECT 1 FROM project_analysis WHERE project_id = ? LIMIT 1",
        (project_id,),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE project_analysis
            SET repo_url = ?, token_enc = ?
            WHERE project_id = ?
            """,
            (repo_url, token_enc, project_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO project_analysis (
                project_id,
                classification,
                primary_contributor,
                snapshot,
                repo_url,
                token_enc
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, "unknown", None, json.dumps({}), repo_url, token_enc),
        )

    conn.commit()


def fetch_github_source(conn: sqlite3.Connection, project_id: str) -> dict | None:
    if not project_id:
        return None

    row = conn.execute(
        """
        SELECT project_id, repo_url, token_enc, created_at
        FROM project_analysis
        WHERE project_id = ?
          AND repo_url IS NOT NULL
          AND token_enc IS NOT NULL
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if not row:
        return None

    project_id, repo_url, token_enc, created_at = row
    return {
        "project_id": project_id,
        "repo_url": repo_url,
        "token": _decrypt_token(token_enc),
        "created_at": created_at,
    }

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_uploaded_file_bytes(
    conn: sqlite3.Connection,
    *,
    data: bytes,
    original_name: str | None = None,
    uploader: str | None = None,
    source: str | None = None,
    base_dir: Path | None = None,
    mime: str | None = None,
) -> dict:
    """
    Content-addressable storage:
    - Hash file bytes (sha256)
    - If hash already exists in `files`, increment ref_count and reuse file_id
    - Always create a row in `uploads` for traceability
    Returns dict with upload_id, file_id, hash, path.
    """
    if data is None:
        raise ValueError("data must be provided")

    file_hash = _sha256_bytes(data)
    size_bytes = len(data)

    # Where to store the file on disk
    # Keep it deterministic so dedupe is easy.
    root = base_dir or BASE_DIR
    files_dir = root / "blobs"
    files_dir.mkdir(parents=True, exist_ok=True)
    blob_path = files_dir / f"{file_hash}.bin"

    # Try to insert new file row, otherwise reuse existing row
    file_id = str(uuid.uuid4())

    # Use a transaction so ref_count + upload row stays consistent
    with conn:
        try:
            conn.execute(
                """
                INSERT INTO files (file_id, hash, size_bytes, mime, path, ref_count)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (file_id, file_hash, size_bytes, mime, str(blob_path)),
            )
            # Only write bytes when we successfully inserted a new hash
            blob_path.write_bytes(data)
        except sqlite3.IntegrityError:
            # hash already exists -> increment ref_count and reuse existing file_id/path
            conn.execute(
                """
                UPDATE files
                SET ref_count = ref_count + 1
                WHERE hash = ?
                """,
                (file_hash,),
            )
            row = conn.execute(
                """
                SELECT file_id, path
                FROM files
                WHERE hash = ?
                LIMIT 1
                """,
                (file_hash,),
            ).fetchone()
            file_id = row[0]
            blob_path = Path(row[1])

        upload_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO uploads (upload_id, original_name, uploader, source, hash, file_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (upload_id, original_name, uploader, source, file_hash, file_id),
        )

    return {
        "upload_id": upload_id,
        "file_id": file_id,
        "hash": file_hash,
        "path": str(blob_path),
        "size_bytes": size_bytes,
    }


def fetch_file_row_by_hash(conn: sqlite3.Connection, file_hash: str) -> dict | None:
    row = conn.execute(
        """
        SELECT file_id, hash, size_bytes, mime, path, ref_count, created_at
        FROM files
        WHERE hash = ?
        LIMIT 1
        """,
        (file_hash,),
    ).fetchone()
    if not row:
        return None
    file_id, h, size_bytes, mime, path, ref_count, created_at = row
    return {
        "file_id": file_id,
        "hash": h,
        "size_bytes": size_bytes,
        "mime": mime,
        "path": path,
        "ref_count": ref_count,
        "created_at": created_at,
    }


# Contributor stats

def store_contributor_stats(
    conn: sqlite3.Connection,
    project_id: str,
    contributor: str,
    *,
    user_id: int | None = None,
    commits: int = 0,
    pull_requests: int = 0,
    issues: int = 0,
    reviews: int = 0,
    score: float = 0.0,
    weights_hash: str | None = None,
    source: str | None = None,  # kept for API compat; no longer stored
) -> None:
    if not project_id:
        raise ValueError("project_id must be provided")
    if not contributor:
        raise ValueError("contributor must be provided")

    contributor_id = int(user_id) if user_id else None
    if contributor_id is None:
        row = conn.execute(
            "SELECT id FROM contributors WHERE github_username = ? ORDER BY id LIMIT 1",
            (contributor,),
        ).fetchone()
        if row:
            contributor_id = int(row[0])
    if contributor_id is None:
        return  # cannot store without a linked contributor

    # Ensure the parent projects row exists (FK constraint added in M24)
    upsert_project(conn, project_id)

    conn.execute(
        """
        INSERT INTO project_contributors
            (project_id, contributor_id, commits, pull_requests, issues, reviews,
             score, weights_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, contributor_id) DO UPDATE SET
            commits       = excluded.commits,
            pull_requests = excluded.pull_requests,
            issues        = excluded.issues,
            reviews       = excluded.reviews,
            score         = excluded.score,
            weights_hash  = COALESCE(excluded.weights_hash, weights_hash),
            updated_at    = CURRENT_TIMESTAMP
        """,
        (
            project_id,
            contributor_id,
            int(commits),
            int(pull_requests),
            int(issues),
            int(reviews),
            float(score),
            weights_hash,
        ),
    )
    conn.commit()


def fetch_latest_contributor_stats(
    conn: sqlite3.Connection,
    project_id: str,
) -> list[dict]:
    if not project_id:
        return []

    cursor = conn.execute(
        """
        SELECT
            pc.id,
            pc.project_id,
            c.github_username AS contributor,
            pc.contributor_id  AS user_id,
            pc.commits,
            pc.pull_requests,
            pc.issues,
            pc.reviews,
            pc.score,
            pc.weights_hash,
            pc.created_at
        FROM project_contributors pc
        JOIN contributors c ON c.id = pc.contributor_id
        WHERE pc.project_id = ?
        ORDER BY pc.score DESC, c.github_username ASC
        """,
        (project_id,),
    )

    rows = cursor.fetchall()
    payload: list[dict] = []
    for row in rows:
        (
            row_id,
            proj_id,
            contributor,
            user_id,
            commits,
            pull_requests,
            issues,
            reviews,
            score,
            weights_hash,
            created_at,
        ) = row
        payload.append(
            {
                "id": row_id,
                "project_id": proj_id,
                "contributor": contributor,
                "user_id": user_id,
                "commits": commits,
                "pull_requests": pull_requests,
                "issues": issues,
                "reviews": reviews,
                "score": score,
                "weights_hash": weights_hash,
                "source": None,  # removed; kept for dict-key compat
                "created_at": created_at,
            }
        )
    return payload
def upsert_project_thumbnail(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    image_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> None:
    """
    Store an image for a project. Latest row becomes the project's thumbnail.
    We keep history by inserting a new row.
    """
    if not project_id:
        raise ValueError("project_id must be provided")
    if not image_bytes:
        raise ValueError("image_bytes must be provided")

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    conn.execute(
        """
        INSERT INTO project_images (project_id, filename, content_type, image_b64)
        VALUES (?, ?, ?, ?)
        """,
        (project_id, filename, content_type, image_b64),
    )
    conn.commit()


def fetch_project_thumbnail_meta(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """
    Return metadata for the latest thumbnail: {project_id, filename, content_type, created_at}
    """
    if not project_id:
        return None

    row = conn.execute(
        """
        SELECT project_id, filename, content_type, created_at
        FROM project_images
        WHERE project_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if not row:
        return None

    pid, filename, content_type, created_at = row
    return {
        "project_id": pid,
        "filename": filename,
        "content_type": content_type,
        "created_at": created_at,
    }


def fetch_project_thumbnail_bytes(conn: sqlite3.Connection, project_id: str) -> bytes | None:
    """
    Return raw bytes for the latest thumbnail image for this project.
    """
    if not project_id:
        return None

    row = conn.execute(
        """
        SELECT image_b64
        FROM project_images
        WHERE project_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if not row:
        return None

    try:
        return base64.b64decode(row[0].encode("ascii"))
    except Exception:
        return None


def update_contributor_score(
    conn: sqlite3.Connection,
    row_id: int,
    *,
    score: float,
    weights_hash: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE project_contributors
        SET score = ?, weights_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (float(score), weights_hash, int(row_id)),
    )
    conn.commit()


def upsert_project_overrides(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    key_role: str | None = None,
    evidence: str | None = None,
    portfolio_blurb: str | None = None,
    resume_bullets: list[str] | None = None,
    selected: bool | None = None,
    rank: int | None = None,
) -> dict:
    if not project_id:
        raise ValueError("project_id must be provided")

    payload = {
        "project_id": project_id,
        "key_role": key_role,
        "evidence": evidence,
        "portfolio_blurb": portfolio_blurb,
        "resume_bullets_json": json.dumps(resume_bullets) if resume_bullets is not None else None,
        "selected": (1 if selected else 0) if selected is not None else None,
        "rank": rank,
    }

    conn.execute(
        """
        INSERT INTO project_overrides
            (project_id, key_role, evidence, portfolio_blurb, resume_bullets_json, selected, rank, updated_at)
        VALUES
            (:project_id, :key_role, :evidence, :portfolio_blurb, :resume_bullets_json, :selected, :rank, CURRENT_TIMESTAMP)
        ON CONFLICT(project_id) DO UPDATE SET
            key_role = COALESCE(excluded.key_role, project_overrides.key_role),
            evidence = COALESCE(excluded.evidence, project_overrides.evidence),
            portfolio_blurb = COALESCE(excluded.portfolio_blurb, project_overrides.portfolio_blurb),
            resume_bullets_json = COALESCE(excluded.resume_bullets_json, project_overrides.resume_bullets_json),
            selected = COALESCE(excluded.selected, project_overrides.selected),
            rank = COALESCE(excluded.rank, project_overrides.rank),
            updated_at = CURRENT_TIMESTAMP
        """,
        payload,
    )
    conn.commit()
    return fetch_project_overrides(conn, project_id) or {"project_id": project_id}


def fetch_project_overrides(conn: sqlite3.Connection, project_id: str) -> dict | None:
    if not project_id:
        return None

    row = conn.execute(
        """
        SELECT project_id, key_role, evidence, portfolio_blurb, resume_bullets_json, selected, rank, updated_at
        FROM project_overrides
        WHERE project_id = ?
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if not row:
        return None

    bullets = None
    if row[4]:
        try:
            bullets = json.loads(row[4])
        except Exception:
            bullets = None

    return {
        "project_id": row[0],
        "key_role": row[1],
        "evidence": row[2],
        "portfolio_blurb": row[3],
        "resume_bullets": bullets,
        "selected": bool(row[5]) if row[5] is not None else None,
        "rank": row[6],
        "updated_at": row[7],
    }
# -----------------------------
# Users and user-project links
# -----------------------------

def upsert_contributor(
    conn: sqlite3.Connection,
    github_username: str,
    *,
    email: str | None = None,
) -> int:
    if not github_username:
        raise ValueError("github_username must be provided")
    github_username = str(github_username).strip()
    email = _normalize_user_email(email)
    default_github = _default_github_url(github_username)

    # Prefer matching by email when available, otherwise by github_username.
    row = None
    if email:
        row = conn.execute(
            "SELECT id, github_username, email FROM contributors WHERE email = ? LIMIT 1",
            (email,),
        ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id, github_username, email FROM contributors WHERE github_username = ? LIMIT 1",
            (github_username,),
        ).fetchone()
    if row:
        user_id = int(row[0])
        conn.execute(
            """
            UPDATE contributors
            SET
                github_username = COALESCE(?, github_username),
                email = COALESCE(?, email),
                github_url = CASE
                    WHEN github_url IS NULL OR TRIM(github_url) = ''
                    THEN COALESCE(?, github_url)
                    ELSE github_url
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (github_username, email, default_github, user_id),
        )
        conn.commit()
        return user_id

    cursor = conn.execute(
        """
        INSERT INTO contributors (github_username, email, github_url)
        VALUES (?, ?, ?)
        """,
        (github_username, email, default_github),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_contributor_profile(conn: sqlite3.Connection, contributor_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT id, github_username, email, github_url
        FROM contributors
        WHERE id = ?
        LIMIT 1
        """,
        (int(contributor_id),),
    ).fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "github_username": row[1],
        "email": row[2],
        "github_url": row[3],
    }


def get_user(conn: sqlite3.Connection) -> dict | None:
    """Return the single login account row, or None if not yet set."""
    row = conn.execute(
        """
        SELECT id, username, password_hash, github_username, github_url,
               github_token_enc, full_name, phone_number, city, state_region,
               portfolio_url, created_at, last_login_at
        FROM user
        WHERE id = 1
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "username": row[1],
        "password_hash": row[2],
        "github_username": row[3],
        "github_url": row[4],
        "github_token_enc": row[5],
        "full_name": row[6],
        "phone_number": row[7],
        "city": row[8],
        "state_region": row[9],
        "portfolio_url": row[10],
        "created_at": row[11],
        "last_login_at": row[12],
    }


def upsert_user(
    conn: sqlite3.Connection,
    username: str,
    *,
    password_hash: str | None = None,
    github_username: str | None = None,
    github_url: str | None = None,
    github_token_enc: str | None = None,
    full_name: str | None = None,
    phone_number: str | None = None,
    city: str | None = None,
    state_region: str | None = None,
    portfolio_url: str | None = None,
) -> None:
    if not username:
        raise ValueError("username must be provided")
    conn.execute(
        """
        INSERT INTO user (id, username, password_hash, github_username, github_url,
                          github_token_enc, full_name, phone_number, city, state_region,
                          portfolio_url)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            username = excluded.username,
            password_hash = COALESCE(excluded.password_hash, password_hash),
            github_username = COALESCE(excluded.github_username, github_username),
            github_url = COALESCE(excluded.github_url, github_url),
            github_token_enc = COALESCE(excluded.github_token_enc, github_token_enc),
            full_name = COALESCE(excluded.full_name, full_name),
            phone_number = COALESCE(excluded.phone_number, phone_number),
            city = COALESCE(excluded.city, city),
            state_region = COALESCE(excluded.state_region, state_region),
            portfolio_url = COALESCE(excluded.portfolio_url, portfolio_url)
        """,
        (username, password_hash, github_username, github_url, github_token_enc,
         full_name, phone_number, city, state_region, portfolio_url),
    )
    conn.commit()


def update_user_profile(
    conn: sqlite3.Connection,
    *,
    full_name: str | None = None,
    phone_number: str | None = None,
    city: str | None = None,
    state_region: str | None = None,
    github_username: str | None = None,
    github_url: str | None = None,
    portfolio_url: str | None = None,
) -> None:
    """Update profile fields on the login account row."""
    conn.execute(
        """
        UPDATE user
        SET
            full_name = COALESCE(?, full_name),
            phone_number = COALESCE(?, phone_number),
            city = COALESCE(?, city),
            state_region = COALESCE(?, state_region),
            github_username = COALESCE(?, github_username),
            github_url = COALESCE(?, github_url),
            portfolio_url = COALESCE(?, portfolio_url)
        WHERE id = 1
        """,
        (full_name, phone_number, city, state_region, github_username, github_url, portfolio_url),
    )
    conn.commit()


def get_user_education(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, university, degree, start_date, end_date, city, state, sort_order
        FROM user_education
        WHERE user_id = ?
        ORDER BY sort_order, id
        """,
        (int(user_id),),
    ).fetchall()
    return [
        {
            "id": r[0],
            "university": r[1],
            "degree": r[2],
            "start_date": r[3],
            "end_date": r[4],
            "city": r[5],
            "state": r[6],
            "sort_order": r[7],
        }
        for r in rows
    ]


def replace_user_education(conn: sqlite3.Connection, user_id: int, entries: list[dict]) -> None:
    """Replace all education entries for a user."""
    conn.execute("DELETE FROM user_education WHERE user_id = ?", (int(user_id),))
    for idx, entry in enumerate(entries):
        conn.execute(
            """
            INSERT INTO user_education (user_id, university, degree, start_date, end_date, city, state, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(entry.get("university") or "").strip(),
                str(entry.get("degree") or "").strip() or None,
                str(entry.get("start_date") or "").strip() or None,
                str(entry.get("end_date") or "").strip() or None,
                str(entry.get("city") or "").strip() or None,
                str(entry.get("state") or "").strip() or None,
                idx,
            ),
        )
    conn.commit()


def upsert_default_resume_modules(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    header: dict[str, str],
    core_skills: list[str],
    projects: list[dict[str, str]],
    education: list[dict] | None = None,
    summary: str | None = None,
    resume_title: str | None = None,
    create_new: bool = False,
) -> str:
    """
    Ensure a draft modular resume exists for the user and persist default modules.
    - header/core_skill/project are refreshed from latest generated data.
    - education is populated from user profile data when provided.
    - summary is auto-populated when provided, else ensured as an empty template.
    - experience is ensured as an empty template (insert only when missing).
    """
    row = None
    if not create_new:
        row = conn.execute(
            """
            SELECT id
            FROM resumes
            WHERE user_id = ? AND status = 'draft'
            ORDER BY datetime(updated_at) DESC, id DESC
            LIMIT 1
            """,
            (int(user_id),),
        ).fetchone()
    if row:
        resume_id = str(row[0])
        if resume_title is not None:
            conn.execute(
                "UPDATE resumes SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (resume_title, resume_id),
            )
        else:
            conn.execute(
                "UPDATE resumes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (resume_id,),
            )
    else:
        resume_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO resumes (id, user_id, title, target_role, status)
            VALUES (?, ?, ?, NULL, 'draft')
            """,
            (
                resume_id,
                int(user_id),
                resume_title or "Default Resume",
            ),
        )

    defaults = [
        ("header", "Header"),
        ("summary", "Summary"),
        ("education", "Education"),
        ("experience", "Experience"),
        ("core_skill", "Core Skill"),
        ("project", "Project"),
    ]
    section_ids: dict[str, str] = {}
    for index, (key, label) in enumerate(defaults, start=1):
        sec = conn.execute(
            """
            SELECT id
            FROM resume_sections
            WHERE resume_id = ? AND key = ?
            LIMIT 1
            """,
            (resume_id, key),
        ).fetchone()
        if sec:
            section_id = str(sec[0])
            conn.execute(
                """
                UPDATE resume_sections
                SET label = ?, sort_order = ?, is_enabled = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (label, index, section_id),
            )
        else:
            section_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO resume_sections (
                    id, resume_id, key, label, is_custom, sort_order, is_enabled
                )
                VALUES (?, ?, ?, ?, 0, ?, 1)
                """,
                (section_id, resume_id, key, label, index),
            )
        section_ids[key] = section_id

    def _replace_items(section_key: str, items: list[dict[str, object]]) -> None:
        section_id = section_ids[section_key]
        conn.execute("DELETE FROM resume_items WHERE section_id = ?", (section_id,))
        for idx, item in enumerate(items, start=1):
            conn.execute(
                """
                INSERT INTO resume_items (
                    id, section_id, title, subtitle, start_date, end_date, location, content,
                    bullets_json, metadata_json, sort_order, is_enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    str(uuid.uuid4()),
                    section_id,
                    item.get("title"),
                    item.get("subtitle"),
                    item.get("start_date"),
                    item.get("end_date"),
                    item.get("location"),
                    item.get("content"),
                    json.dumps(item.get("bullets") or []),
                    json.dumps(item.get("metadata") or {}),
                    idx,
                ),
            )

    header_item = {
        "title": "Header",
        "content": header.get("full_name") or "",
        "metadata": {
            "full_name": header.get("full_name") or "",
            "email": header.get("email") or "",
            "phone": header.get("phone") or "",
            "location": header.get("location") or "",
            "github_url": header.get("github_url") or "",
            "portfolio_url": header.get("portfolio_url") or "",
        },
    }
    _replace_items("header", [header_item])

    skill_tokens = [str(token).strip() for token in (core_skills or []) if str(token).strip()]
    deduped_skills: list[str] = []
    seen: set[str] = set()
    for token in skill_tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped_skills.append(token)
    core_skill_item = {
        "title": "Core Skill",
        "content": ", ".join(deduped_skills),
        "bullets": deduped_skills,
    }
    _replace_items("core_skill", [core_skill_item])

    project_items: list[dict[str, object]] = []
    for project in projects or []:
        project_items.append(
            {
                "title": project.get("title") or "Project",
                "subtitle": project.get("subtitle") or project.get("stack") or "",
                "start_date": project.get("start_date") or "",
                "end_date": project.get("end_date") or "",
                "location": project.get("location") or "",
                "content": project.get("content") or "",
            }
        )
    _replace_items("project", project_items)

    # Education: populate from user profile data if provided, else ensure empty template.
    if education:
        edu_items = []
        for e in education:
            city = str(e.get("city") or "").strip()
            state = str(e.get("state") or "").strip()
            location = ", ".join(p for p in [city, state] if p)
            edu_items.append({
                "title": e.get("university") or "University",
                "subtitle": e.get("degree") or "",
                "start_date": e.get("start_date") or "",
                "end_date": e.get("end_date") or "Present",
                "location": location,
            })
        _replace_items("education", edu_items)
    else:
        section_id = section_ids["education"]
        existing = conn.execute(
            "SELECT 1 FROM resume_items WHERE section_id = ? LIMIT 1",
            (section_id,),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO resume_items (
                    id, section_id, title, subtitle, start_date, end_date, location, content,
                    bullets_json, metadata_json, sort_order, is_enabled
                )
                VALUES (?, ?, 'University', NULL, NULL, NULL, NULL, '', '[]', '{}', 1, 1)
                """,
                (str(uuid.uuid4()), section_id),
            )

    # Summary: populate from generated text when provided, else ensure empty template.
    if summary:
        _replace_items("summary", [{"title": "Summary", "content": summary}])
    else:
        section_id = section_ids["summary"]
        existing = conn.execute(
            "SELECT 1 FROM resume_items WHERE section_id = ? LIMIT 1",
            (section_id,),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO resume_items (
                    id, section_id, title, subtitle, start_date, end_date, location, content,
                    bullets_json, metadata_json, sort_order, is_enabled
                )
                VALUES (?, ?, 'Summary', NULL, NULL, NULL, NULL, '', '[]', '{}', 1, 1)
                """,
                (str(uuid.uuid4()), section_id),
            )

    # Ensure empty template for experience (insert only if missing).
    for key, title in (("experience", "Event"),):
        section_id = section_ids[key]
        existing = conn.execute(
            "SELECT 1 FROM resume_items WHERE section_id = ? LIMIT 1",
            (section_id,),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO resume_items (
                    id, section_id, title, subtitle, start_date, end_date, location, content,
                    bullets_json, metadata_json, sort_order, is_enabled
                )
                VALUES (?, ?, ?, NULL, NULL, NULL, NULL, '', '[]', '{}', 1, 1)
                """,
                (str(uuid.uuid4()), section_id, title),
            )

    conn.commit()
    return resume_id


# ---------------------------------------------------------------------------
# Modular resume query / mutation helpers
# ---------------------------------------------------------------------------

def _item_row_to_dict(row: tuple) -> dict:
    """Convert a resume_items DB row to a plain dict."""
    (
        id_, section_id, title, subtitle, start_date, end_date,
        location, content, bullets_json, metadata_json,
        sort_order, is_enabled, created_at, updated_at,
    ) = row
    return {
        "id": id_,
        "section_id": section_id,
        "title": title,
        "subtitle": subtitle,
        "start_date": start_date,
        "end_date": end_date,
        "location": location,
        "content": content,
        "bullets": json.loads(bullets_json or "[]"),
        "metadata": json.loads(metadata_json or "{}"),
        "sort_order": sort_order,
        "is_enabled": bool(is_enabled),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _section_row_to_dict(row: tuple, items: list[dict] | None = None) -> dict:
    """Convert a resume_sections DB row to a plain dict."""
    id_, resume_id, key, label, is_custom, sort_order, is_enabled, created_at, updated_at = row
    d: dict = {
        "id": id_,
        "resume_id": resume_id,
        "key": key,
        "label": label,
        "is_custom": bool(is_custom),
        "sort_order": sort_order,
        "is_enabled": bool(is_enabled),
        "created_at": created_at,
        "updated_at": updated_at,
    }
    if items is not None:
        d["items"] = items
    return d


def fetch_resumes(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """List all resumes for a user (no sections/items, but includes section_count)."""
    rows = conn.execute(
        """
        SELECT r.id, r.user_id, r.title, r.target_role, r.status,
               r.created_at, r.updated_at,
               COUNT(s.id) AS section_count
        FROM resumes r
        LEFT JOIN resume_sections s
               ON s.resume_id = r.id AND s.is_enabled = 1
        WHERE r.user_id = ?
        GROUP BY r.id
        ORDER BY datetime(r.updated_at) DESC, r.id DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [
        {
            "id": r[0], "user_id": r[1], "title": r[2],
            "target_role": r[3], "status": r[4],
            "created_at": r[5], "updated_at": r[6],
            "section_count": r[7],
        }
        for r in rows
    ]


def fetch_resume(conn: sqlite3.Connection, resume_id: str) -> dict | None:
    """Get a single resume with nested sections and items."""
    row = conn.execute(
        "SELECT id, user_id, title, target_role, status, created_at, updated_at FROM resumes WHERE id = ?",
        (resume_id,),
    ).fetchone()
    if not row:
        return None
    resume = {
        "id": row[0], "user_id": row[1], "title": row[2],
        "target_role": row[3], "status": row[4],
        "created_at": row[5], "updated_at": row[6],
        "sections": [],
    }
    sec_rows = conn.execute(
        """
        SELECT id, resume_id, key, label, is_custom, sort_order, is_enabled, created_at, updated_at
        FROM resume_sections
        WHERE resume_id = ?
        ORDER BY sort_order, id
        """,
        (resume_id,),
    ).fetchall()
    for sec_row in sec_rows:
        section_id = sec_row[0]
        item_rows = conn.execute(
            """
            SELECT id, section_id, title, subtitle, start_date, end_date, location, content,
                   bullets_json, metadata_json, sort_order, is_enabled, created_at, updated_at
            FROM resume_items
            WHERE section_id = ?
            ORDER BY sort_order, id
            """,
            (section_id,),
        ).fetchall()
        resume["sections"].append(
            _section_row_to_dict(sec_row, items=[_item_row_to_dict(ir) for ir in item_rows])
        )
    return resume


def insert_resume(
    conn: sqlite3.Connection,
    user_id: int,
    title: str = "Default Resume",
    target_role: str | None = None,
) -> str:
    """Insert a new resume row and return its id."""
    resume_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO resumes (id, user_id, title, target_role, status) VALUES (?, ?, ?, ?, 'draft')",
        (resume_id, int(user_id), title or "Default Resume", target_role),
    )
    conn.commit()
    return resume_id


def update_resume(
    conn: sqlite3.Connection,
    resume_id: str,
    *,
    title: str | None = None,
    target_role: str | None = None,
    status: str | None = None,
) -> bool:
    """Update mutable resume fields. Returns True if a row was found."""
    sets, params = [], []
    if title is not None:
        sets.append("title = ?"); params.append(title)
    if target_role is not None:
        sets.append("target_role = ?"); params.append(target_role)
    if status is not None:
        sets.append("status = ?"); params.append(status)
    if not sets:
        return bool(conn.execute("SELECT 1 FROM resumes WHERE id = ?", (resume_id,)).fetchone())
    sets.append("updated_at = CURRENT_TIMESTAMP")
    params.append(resume_id)
    cur = conn.execute(f"UPDATE resumes SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount > 0


def delete_resume(conn: sqlite3.Connection, resume_id: str) -> bool:
    """Delete a resume (cascade deletes sections + items via FK)."""
    cur = conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
    conn.commit()
    return cur.rowcount > 0


# --- Sections ---

def fetch_resume_sections(conn: sqlite3.Connection, resume_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, resume_id, key, label, is_custom, sort_order, is_enabled, created_at, updated_at
        FROM resume_sections WHERE resume_id = ? ORDER BY sort_order, id
        """,
        (resume_id,),
    ).fetchall()
    return [_section_row_to_dict(r) for r in rows]


def insert_resume_section(
    conn: sqlite3.Connection,
    resume_id: str,
    key: str,
    label: str,
    *,
    is_custom: bool = True,
    sort_order: int | None = None,
) -> str:
    if sort_order is None:
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM resume_sections WHERE resume_id = ?",
            (resume_id,),
        ).fetchone()
        sort_order = (row[0] or 0) + 1
    section_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO resume_sections (id, resume_id, key, label, is_custom, sort_order, is_enabled)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (section_id, resume_id, key, label, int(is_custom), sort_order),
    )
    conn.commit()
    return section_id


def update_resume_section(
    conn: sqlite3.Connection,
    section_id: str,
    *,
    label: str | None = None,
    is_enabled: bool | None = None,
    sort_order: int | None = None,
) -> bool:
    sets, params = [], []
    if label is not None:
        sets.append("label = ?"); params.append(label)
    if is_enabled is not None:
        sets.append("is_enabled = ?"); params.append(int(is_enabled))
    if sort_order is not None:
        sets.append("sort_order = ?"); params.append(sort_order)
    if not sets:
        return bool(conn.execute("SELECT 1 FROM resume_sections WHERE id = ?", (section_id,)).fetchone())
    sets.append("updated_at = CURRENT_TIMESTAMP")
    params.append(section_id)
    cur = conn.execute(f"UPDATE resume_sections SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount > 0


def delete_resume_section(conn: sqlite3.Connection, section_id: str) -> bool:
    cur = conn.execute("DELETE FROM resume_sections WHERE id = ?", (section_id,))
    conn.commit()
    return cur.rowcount > 0


def reorder_resume_sections(conn: sqlite3.Connection, resume_id: str, ids: list[str]) -> list[dict]:
    """Assign sort_order based on position in ids list. Unknown ids are ignored."""
    for idx, section_id in enumerate(ids, start=1):
        conn.execute(
            "UPDATE resume_sections SET sort_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND resume_id = ?",
            (idx, section_id, resume_id),
        )
    conn.commit()
    return fetch_resume_sections(conn, resume_id)


# --- Items ---

def fetch_resume_items(conn: sqlite3.Connection, section_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, section_id, title, subtitle, start_date, end_date, location, content,
               bullets_json, metadata_json, sort_order, is_enabled, created_at, updated_at
        FROM resume_items WHERE section_id = ? ORDER BY sort_order, id
        """,
        (section_id,),
    ).fetchall()
    return [_item_row_to_dict(r) for r in rows]


def insert_resume_item(
    conn: sqlite3.Connection,
    section_id: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    location: str | None = None,
    content: str | None = None,
    bullets: list | None = None,
    metadata: dict | None = None,
    sort_order: int | None = None,
) -> str:
    if sort_order is None:
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM resume_items WHERE section_id = ?",
            (section_id,),
        ).fetchone()
        sort_order = (row[0] or 0) + 1
    item_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO resume_items (
            id, section_id, title, subtitle, start_date, end_date, location, content,
            bullets_json, metadata_json, sort_order, is_enabled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            item_id, section_id, title, subtitle, start_date, end_date, location, content,
            json.dumps(bullets or []), json.dumps(metadata or {}), sort_order,
        ),
    )
    conn.commit()
    return item_id


def update_resume_item(
    conn: sqlite3.Connection,
    item_id: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    location: str | None = None,
    content: str | None = None,
    bullets: list | None = None,
    metadata: dict | None = None,
    is_enabled: bool | None = None,
) -> bool:
    sets, params = [], []
    if title is not None:
        sets.append("title = ?"); params.append(title)
    if subtitle is not None:
        sets.append("subtitle = ?"); params.append(subtitle)
    if start_date is not None:
        sets.append("start_date = ?"); params.append(start_date)
    if end_date is not None:
        sets.append("end_date = ?"); params.append(end_date)
    if location is not None:
        sets.append("location = ?"); params.append(location)
    if content is not None:
        sets.append("content = ?"); params.append(content)
    if bullets is not None:
        sets.append("bullets_json = ?"); params.append(json.dumps(bullets))
    if metadata is not None:
        sets.append("metadata_json = ?"); params.append(json.dumps(metadata))
    if is_enabled is not None:
        sets.append("is_enabled = ?"); params.append(int(is_enabled))
    if not sets:
        return bool(conn.execute("SELECT 1 FROM resume_items WHERE id = ?", (item_id,)).fetchone())
    sets.append("updated_at = CURRENT_TIMESTAMP")
    params.append(item_id)
    cur = conn.execute(f"UPDATE resume_items SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount > 0


def delete_resume_item(conn: sqlite3.Connection, item_id: str) -> bool:
    cur = conn.execute("DELETE FROM resume_items WHERE id = ?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def reorder_resume_items(conn: sqlite3.Connection, section_id: str, ids: list[str]) -> list[dict]:
    """Assign sort_order based on position in ids list."""
    for idx, item_id in enumerate(ids, start=1):
        conn.execute(
            "UPDATE resume_items SET sort_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND section_id = ?",
            (idx, item_id, section_id),
        )
    conn.commit()
    return fetch_resume_items(conn, section_id)


def link_contributor_to_project(
    conn: sqlite3.Connection,
    user_id: int,
    project_id: str,
    *,
    contributor_name: str | None = None,  # kept for API compat; no longer stored
    first_commit_at: str | None = None,
    last_commit_at: str | None = None,
) -> None:
    if not user_id:
        raise ValueError("user_id must be provided")
    if not project_id:
        raise ValueError("project_id must be provided")
    # Ensure the parent projects row exists (FK constraint added in M24)
    upsert_project(conn, project_id)
    conn.execute(
        """
        INSERT INTO project_contributors (project_id, contributor_id, first_commit_at, last_commit_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(project_id, contributor_id) DO UPDATE SET
            first_commit_at = CASE
                WHEN first_commit_at IS NULL THEN excluded.first_commit_at
                WHEN excluded.first_commit_at IS NOT NULL
                     AND excluded.first_commit_at < first_commit_at THEN excluded.first_commit_at
                ELSE first_commit_at END,
            last_commit_at = CASE
                WHEN last_commit_at IS NULL THEN excluded.last_commit_at
                WHEN excluded.last_commit_at IS NOT NULL
                     AND excluded.last_commit_at > last_commit_at THEN excluded.last_commit_at
                ELSE last_commit_at END,
            updated_at = CURRENT_TIMESTAMP
        """,
        (project_id, int(user_id), first_commit_at, last_commit_at),
    )
    conn.commit()


def fetch_project_contributor_activity_periods(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    project_ids: Iterable[str],
) -> dict[str, dict[str, str]]:
    cleaned = [str(pid).strip() for pid in project_ids if str(pid).strip()]
    if not cleaned:
        return {}
    placeholders = ",".join("?" * len(cleaned))
    rows = conn.execute(
        f"""
        SELECT project_id, first_commit_at, last_commit_at
        FROM project_contributors
        WHERE contributor_id = ?
          AND project_id IN ({placeholders})
        """,
        (int(user_id), *cleaned),
    ).fetchall()
    return {
        str(row[0]): {
            "first_commit_at": str(row[1] or ""),
            "last_commit_at": str(row[2] or ""),
        }
        for row in rows
        if row and row[0]
    }


def bulk_upsert_contributors(
    conn: sqlite3.Connection,
    project_id: str,
    contributors: Iterable[object],
) -> None:
    """
    Bulk upsert helpers: accepts any iterable with 'contributor' and optional 'email'.
    """
    if not project_id:
        return
    for row in contributors:
        github_username = getattr(row, "contributor", None) or getattr(row, "username", None)
        email = getattr(row, "email", None)
        if not github_username:
            continue
        user_id = upsert_contributor(conn, github_username, email=email)
        link_contributor_to_project(conn, user_id, project_id, contributor_name=github_username)

def save_project_metadata(conn, project_id, meta):
    """Save project timeline/status. Writes to projects table (project_metadata was removed in M21)."""
    upsert_project(
        conn,
        project_id,
        status=meta.get("status") or "ongoing",
        first_commit_at=meta.get("start_date"),
        last_commit_at=meta.get("end_date"),
    )

def load_project_metadata(conn):
    """Load project timeline/status from projects table (project_metadata was removed in M21)."""
    rows = conn.execute(
        "SELECT project_id, first_commit_at, last_commit_at, status FROM projects"
    ).fetchall()
    return {
        row[0]: {
            "start_date": row[1],
            "end_date": row[2],
            "status": row[3],
        }
        for row in rows
    }

def upsert_project(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    name: str | None = None,
    source: str = "zip",
    github_url: str | None = None,
    github_branch: str | None = None,
    has_git: bool = False,
    type: str | None = None,
    status: str = "ongoing",
    first_commit_at: str | None = None,
    last_commit_at: str | None = None,
) -> None:
    """Insert or update a project row. name defaults to project_id if not given."""
    effective_name = name or project_id
    conn.execute(
        """
        INSERT INTO projects (project_id, name, source, github_url, github_branch, has_git,
                              type, status, first_commit_at, last_commit_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
            name            = COALESCE(excluded.name, name),
            source          = CASE WHEN excluded.source != 'zip' THEN excluded.source ELSE source END,
            github_url      = COALESCE(excluded.github_url, github_url),
            github_branch   = COALESCE(excluded.github_branch, github_branch),
            has_git         = MAX(excluded.has_git, has_git),
            type            = COALESCE(excluded.type, type),
            status          = excluded.status,
            first_commit_at = COALESCE(excluded.first_commit_at, first_commit_at),
            last_commit_at  = COALESCE(excluded.last_commit_at, last_commit_at),
            updated_at      = CURRENT_TIMESTAMP
        """,
        (project_id, effective_name, source, github_url, github_branch, int(has_git),
         type, status, first_commit_at, last_commit_at),
    )
    conn.commit()


def get_project(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Return a single project row as a dict, or None if not found."""
    row = conn.execute(
        """
        SELECT id, project_id, name, source, github_url, github_branch, has_git, type,
               status, first_commit_at, last_commit_at, created_at, updated_at
        FROM projects WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "project_id": row[1], "name": row[2],
        "source": row[3], "github_url": row[4], "github_branch": row[5],
        "has_git": bool(row[6]), "type": row[7], "status": row[8],
        "first_commit_at": row[9], "last_commit_at": row[10],
        "created_at": row[11], "updated_at": row[12],
    }


def update_project_commit_range(
    conn: sqlite3.Connection,
    project_id: str,
    first_commit_at: str | None,
    last_commit_at: str | None,
) -> None:
    """Update first/last commit timestamps, keeping the earlier/later value."""
    conn.execute(
        """
        UPDATE projects SET
            first_commit_at = CASE
                WHEN first_commit_at IS NULL THEN ?
                WHEN ? IS NOT NULL AND ? < first_commit_at THEN ?
                ELSE first_commit_at END,
            last_commit_at = CASE
                WHEN last_commit_at IS NULL THEN ?
                WHEN ? IS NOT NULL AND ? > last_commit_at THEN ?
                ELSE last_commit_at END,
            updated_at = CURRENT_TIMESTAMP
        WHERE project_id = ?
        """,
        (first_commit_at, first_commit_at, first_commit_at, first_commit_at,
         last_commit_at, last_commit_at, last_commit_at, last_commit_at,
         project_id),
    )
    conn.commit()


def fetch_contributor_rankings(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    sort_by: str = "score",
) -> list[dict]:
    allowed = {
        "score": "score",
        "commits": "commits",
        "pull_requests": "pull_requests",
        "issues": "issues",
        "reviews": "reviews",
    }
    sort_key = allowed.get(sort_by, "score")
    rows = fetch_latest_contributor_stats(conn, project_id)
    return sorted(
        rows,
        key=lambda row: (-float(row.get(sort_key, 0)), row.get("contributor", "")),
    )



# Evidence of success

def store_project_evidence(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    evidence_type: str,
    label: str | None = None,
    value: str | None = None,
    source: str | None = None,
) -> None:
    """
    Store one evidence item for a project.

    evidence_type examples: "metric", "feedback", "evaluation", "other"
    label examples: "Stars", "Client feedback", "Final grade"
    value examples: "120", "Great teamwork...", "A+"
    """
    if not project_id:
        raise ValueError("project_id must be provided")
    if not evidence_type:
        raise ValueError("evidence_type must be provided")

    conn.execute(
        """
        INSERT INTO project_evidence (
            project_id,
            evidence_type,
            label,
            value,
            source
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, evidence_type, label, value, source),
    )
    conn.commit()


def fetch_project_evidence(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    limit: int | None = None,
) -> list[dict]:
    """Fetch evidence rows for a project, newest-first."""
    if not project_id:
        return []

    sql = """
        SELECT id, project_id, evidence_type, label, value, source, created_at
        FROM project_evidence
        WHERE project_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
    """
    params: tuple = (project_id,)

    if limit is not None:
        if int(limit) <= 0:
            return []
        sql += " LIMIT ?"
        params = (project_id, int(limit))

    rows = conn.execute(sql, params).fetchall()
    out: list[dict] = []
    for row in rows:
        row_id, pid, etype, label, value, source, created_at = row
        out.append(
            {
                "id": row_id,
                "project_id": pid,
                "evidence_type": etype,
                "label": label,
                "value": value,
                "source": source,
                "created_at": created_at,
            }
        )
    return out



# Backup / export

def backup_database(conn: sqlite3.Connection, destination: Path) -> Path:
    """Create a SQLite backup at the provided destination path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_conn = sqlite3.connect(destination)
    try:
        conn.backup(backup_conn)
    finally:
        backup_conn.close()
    return destination


def export_snapshots_to_json(conn: sqlite3.Connection, output_path: Path) -> int:
    """
    Export all project_analysis rows (not deduped) to a JSON file.
    Returns the number of records written.
    """
    rows = conn.execute(
        """
        SELECT project_id, classification, primary_contributor, snapshot, created_at
        FROM project_analysis
        ORDER BY created_at
        """
    ).fetchall()

    payload: list[dict] = []
    for project_id, classification, contributor, blob, created_at in rows:
        try:
            snapshot = json.loads(blob)
        except Exception:
            snapshot = {}
        payload.append(
            {
                "project_id": project_id,
                "classification": classification,
                "primary_contributor": contributor,
                "created_at": created_at,
                "snapshot": snapshot,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(payload)

# -------------------------------
# GitHub Authentication Storage
# -------------------------------

def save_github_token(token: str):
    """Store GitHub access token."""
    with open_db() as conn:
        conn.execute("DELETE FROM github_auth")
        conn.execute(
            "INSERT INTO github_auth (access_token) VALUES (?)",
            (token,)
        )
        conn.commit()


def get_github_token():
    """Return stored GitHub token if it exists."""
    with open_db() as conn:
        row = conn.execute(
            "SELECT access_token FROM github_auth LIMIT 1"
        ).fetchone()

        if row:
            return row[0]

    return None


def clear_github_token():
    """Logout GitHub user."""
    with open_db() as conn:
        conn.execute("DELETE FROM github_auth")
        conn.commit()

__all__ = [
    "open_db",
    "close_db",
    "BASE_DIR",
    # snapshots
    "store_analysis_snapshot",
    "fetch_latest_snapshot",
    "fetch_latest_snapshots",
    "fetch_latest_snapshots_for_projects",
    "fetch_project_snapshot_history",
    # github sources
    "store_github_source",
    "fetch_github_source",
    # contributor stats
    "store_contributor_stats",
    "fetch_latest_contributor_stats",
    "update_contributor_score",
    "fetch_contributor_rankings",
    # users / contributors
    "get_user",
    "upsert_user",
    "update_user_profile",
    "upsert_contributor",
    "get_contributor_profile",
    "upsert_default_resume_modules",
    "link_contributor_to_project",
    "fetch_project_contributor_activity_periods",
    "bulk_upsert_contributors",
    # evidence
    "store_project_evidence",
    "fetch_project_evidence",
    # backup/export
    "backup_database",
    "export_snapshots_to_json",
    "store_uploaded_file_bytes",
    "fetch_file_row_by_hash",

    "upsert_project_thumbnail",
    "fetch_project_thumbnail_meta",
    "fetch_project_thumbnail_bytes",
    "upsert_project_overrides",
    "fetch_project_overrides",

]
