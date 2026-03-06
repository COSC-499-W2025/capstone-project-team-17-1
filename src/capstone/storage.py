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



def get_base_data_dir():
    if getattr(sys, "frozen", False):
        # Running as PyInstaller exe
        base = Path(os.getenv("LOCALAPPDATA")) / "Loom"
    else:
        # Running in development
        base = Path.cwd() / "runtime_data"

    base.mkdir(parents=True, exist_ok=True)
    return base

BASE_DIR = get_base_data_dir()
_DB_HANDLE: Optional[sqlite3.Connection] = None
_DB_PATH: Optional[Path] = None


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


# Schema + migrations

def _initialize_schema(conn: sqlite3.Connection) -> None:
    # Main analysis snapshots per project
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            classification TEXT NOT NULL,
            primary_contributor TEXT,
            snapshot JSON NOT NULL,
            repo_url TEXT,
            token_enc TEXT,
            zip_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

    )
        # Human-in-the-loop edits / overrides for portfolio + resume output
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_overrides (
            project_id TEXT PRIMARY KEY,
            key_role TEXT,
            evidence TEXT,
            portfolio_blurb TEXT,
            resume_bullets_json TEXT,
            selected INTEGER,
            rank INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # stroring user consent
    conn.execute("""
    CREATE TABLE IF NOT EXISTS privacy_consent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        local_consent INTEGER DEFAULT 0,
        external_consent INTEGER DEFAULT 0,
        updated_at TEXT
    )
    """)

    # Contributor stats history (append-only; we fetch latest per contributor)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_metadata (
            project_id TEXT PRIMARY KEY,
            start_date TEXT,
            end_date TEXT,
            status TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_analysis_results (
            project_id TEXT PRIMARY KEY,
            errors_json TEXT,
            updated_at TEXT
        )
        """)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contributor_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            contributor TEXT NOT NULL,
            user_id INTEGER,
            commits INTEGER NOT NULL DEFAULT 0,
            pull_requests INTEGER NOT NULL DEFAULT 0,
            issues INTEGER NOT NULL DEFAULT 0,
            reviews INTEGER NOT NULL DEFAULT 0,
            score REAL NOT NULL DEFAULT 0,
            weights_hash TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            filename TEXT,
            content_type TEXT,
            image_b64 TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_project_images_project
        ON project_images (project_id, created_at)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contributor_stats_project
        ON contributor_stats (project_id, contributor, created_at)
        """
    )

    # Users derived from contribution data (GitHub or local logs)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            phone_number TEXT,
            city TEXT,
            state_region TEXT,
            github_url TEXT,
            portfolio_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_identity
        ON users (username, COALESCE(email, ''))
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_id TEXT NOT NULL,
            contributor_name TEXT,
            first_commit_at TEXT,
            last_commit_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, project_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_auth (
        id INTEGER PRIMARY KEY,
        access_token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_projects_project
        ON user_projects (project_id)
        """
    )

    # Modular resume schema (MVP).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'Default Resume',
            target_role TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
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
        """
    )
    conn.execute(
        """
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
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resumes_user
        ON resumes (user_id, updated_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resume_sections_resume
        ON resume_sections (resume_id, sort_order)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resume_items_section
        ON resume_items (section_id, sort_order)
        """
    )

    # Evidence of success (metrics/feedback/evaluations), append-only
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,   -- metric | feedback | evaluation | other
            label TEXT,                    -- short name e.g. "Stars", "Grade", "Client feedback"
            value TEXT,                    -- store as text; can be numeric or freeform
            source TEXT,                   -- where it came from (user, github, etc.)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_project_evidence_project
        ON project_evidence (project_id, created_at)
        """
    )

    # ---- Migrations / backfills ----

    # 1) contributor_stats legacy migration: if an older schema has "line_changes"
    info = conn.execute("PRAGMA table_info(contributor_stats)").fetchall()
    columns = {row[1] for row in info}
    if "line_changes" in columns:
        conn.execute("ALTER TABLE contributor_stats RENAME TO contributor_stats_old")
        conn.execute(
            """
            CREATE TABLE contributor_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                contributor TEXT NOT NULL,
                commits INTEGER NOT NULL DEFAULT 0,
                pull_requests INTEGER NOT NULL DEFAULT 0,
                issues INTEGER NOT NULL DEFAULT 0,
                reviews INTEGER NOT NULL DEFAULT 0,
                score REAL NOT NULL DEFAULT 0,
                weights_hash TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        select_weights = "weights_hash" if "weights_hash" in columns else "NULL AS weights_hash"
        conn.execute(
            f"""
            INSERT INTO contributor_stats (
                project_id,
                contributor,
                commits,
                pull_requests,
                issues,
                reviews,
                score,
                weights_hash,
                source,
                created_at
            )
            SELECT
                project_id,
                contributor,
                commits,
                pull_requests,
                issues,
                reviews,
                score,
                {select_weights},
                source,
                created_at
            FROM contributor_stats_old
            """
        )
        conn.execute("DROP TABLE contributor_stats_old")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_contributor_stats_project
            ON contributor_stats (project_id, contributor, created_at)
            """
        )
        conn.commit()

    # Add user_id column to contributor_stats when missing
    info = conn.execute("PRAGMA table_info(contributor_stats)").fetchall()
    columns = {row[1] for row in info}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE contributor_stats ADD COLUMN user_id INTEGER")
        conn.commit()

    # Add profile columns to users when missing (backward-compatible migration).
    user_info = conn.execute("PRAGMA table_info(users)").fetchall()
    user_columns = {row[1] for row in user_info}
    for column_name, column_type in (
        ("full_name", "TEXT"),
        ("phone_number", "TEXT"),
        ("city", "TEXT"),
        ("state_region", "TEXT"),
        ("github_url", "TEXT"),
        ("portfolio_url", "TEXT"),
    ):
        if column_name not in user_columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
    conn.commit()

    # Add per-user per-project activity period columns when missing.
    user_projects_info = conn.execute("PRAGMA table_info(user_projects)").fetchall()
    user_projects_columns = {row[1] for row in user_projects_info}
    for column_name in ("first_commit_at", "last_commit_at"):
        if column_name not in user_projects_columns:
            conn.execute(f"ALTER TABLE user_projects ADD COLUMN {column_name} TEXT")
    conn.commit()

    desired_users_order = [
        "id",
        "username",
        "email",
        "full_name",
        "phone_number",
        "city",
        "state_region",
        "github_url",
        "portfolio_url",
        "created_at",
        "updated_at",
    ]
    user_info = conn.execute("PRAGMA table_info(users)").fetchall()
    current_users_order = [row[1] for row in user_info]
    if all(col in current_users_order for col in desired_users_order) and current_users_order != desired_users_order:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("ALTER TABLE users RENAME TO users_old")
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT,
                full_name TEXT,
                phone_number TEXT,
                city TEXT,
                state_region TEXT,
                github_url TEXT,
                portfolio_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO users (
                id, username, email, full_name, phone_number, city, state_region,
                github_url, portfolio_url, created_at, updated_at
            )
            SELECT
                id,
                username,
                email,
                full_name,
                phone_number,
                city,
                state_region,
                CASE
                    WHEN github_url IS NULL OR TRIM(github_url) = ''
                    THEN ('https://github.com/' || username)
                    ELSE github_url
                END,
                portfolio_url,
                created_at,
                updated_at
            FROM users_old
            """
        )
        conn.execute("DROP TABLE users_old")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_identity
            ON users (username, COALESCE(email, ''))
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

    # Repair legacy FK if user_projects points to users_old.
    fk_rows = conn.execute("PRAGMA foreign_key_list(user_projects)").fetchall()
    fk_targets = {row[2] for row in fk_rows if len(row) > 2}
    if "users_old" in fk_targets:
        conn.execute("ALTER TABLE user_projects RENAME TO user_projects_old")
        conn.execute(
            """
            CREATE TABLE user_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                contributor_name TEXT,
                first_commit_at TEXT,
                last_commit_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, project_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_projects_project
            ON user_projects (project_id)
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO user_projects (
                id, user_id, project_id, contributor_name, first_commit_at, last_commit_at, created_at
            )
            SELECT id, user_id, project_id, contributor_name, NULL, NULL, created_at
            FROM user_projects_old
            """
        )
        conn.execute("DROP TABLE user_projects_old")
        conn.commit()

    # Align resume timestamp columns with users (UTC CURRENT_TIMESTAMP defaults).
    resume_ts_specs = {
        "resumes": {"created_at": "CURRENT_TIMESTAMP", "updated_at": "CURRENT_TIMESTAMP"},
        "resume_sections": {"created_at": "CURRENT_TIMESTAMP", "updated_at": "CURRENT_TIMESTAMP"},
        "resume_items": {"created_at": "CURRENT_TIMESTAMP", "updated_at": "CURRENT_TIMESTAMP"},
    }
    needs_resume_ts_migration = False
    for table_name, expected in resume_ts_specs.items():
        table_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        column_map = {row[1]: row for row in table_info}
        for column_name, expected_default in expected.items():
            row = column_map.get(column_name)
            if not row:
                needs_resume_ts_migration = True
                break
            col_type = str(row[2] or "").upper()
            default_value = str(row[4] or "").upper()
            if col_type != "TIMESTAMP" or default_value != expected_default:
                needs_resume_ts_migration = True
                break
        if needs_resume_ts_migration:
            break

    if needs_resume_ts_migration:
        conn.execute("PRAGMA foreign_keys = OFF")

        conn.execute("ALTER TABLE resumes RENAME TO resumes_old")
        conn.execute(
            """
            CREATE TABLE resumes (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'Default Resume',
                target_role TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            INSERT INTO resumes (id, user_id, title, target_role, status, created_at, updated_at)
            SELECT id, user_id, title, target_role, status, created_at, updated_at
            FROM resumes_old
            """
        )
        conn.execute("DROP TABLE resumes_old")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_resumes_user
            ON resumes (user_id, updated_at)
            """
        )

        conn.execute("ALTER TABLE resume_sections RENAME TO resume_sections_old")
        conn.execute(
            """
            CREATE TABLE resume_sections (
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
            """
        )
        conn.execute(
            """
            INSERT INTO resume_sections (
                id, resume_id, key, label, is_custom, sort_order, is_enabled, created_at, updated_at
            )
            SELECT id, resume_id, key, label, is_custom, sort_order, is_enabled, created_at, updated_at
            FROM resume_sections_old
            """
        )
        conn.execute("DROP TABLE resume_sections_old")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_resume_sections_resume
            ON resume_sections (resume_id, sort_order)
            """
        )

        conn.execute("ALTER TABLE resume_items RENAME TO resume_items_old")
        conn.execute(
            """
            CREATE TABLE resume_items (
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
            """
        )
        conn.execute(
            """
            INSERT INTO resume_items (
                id, section_id, title, subtitle, start_date, end_date, location, content,
                bullets_json, metadata_json, sort_order, is_enabled, created_at, updated_at
            )
            SELECT
                id, section_id, title, subtitle, start_date, end_date, location, content,
                bullets_json, metadata_json, sort_order, is_enabled, created_at, updated_at
            FROM resume_items_old
            """
        )
        conn.execute("DROP TABLE resume_items_old")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_resume_items_section
            ON resume_items (section_id, sort_order)
            """
        )

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

    # 2) project_analysis legacy columns backfill / add columns if missing
    info = conn.execute("PRAGMA table_info(project_analysis)").fetchall()
    columns = {row[1] for row in info}

    # Some older DBs may have had project_name instead of project_id
    if "project_id" not in columns:
        conn.execute("ALTER TABLE project_analysis ADD COLUMN project_id TEXT")
    if "repo_url" not in columns:
        conn.execute("ALTER TABLE project_analysis ADD COLUMN repo_url TEXT")
    if "token_enc" not in columns:
        conn.execute("ALTER TABLE project_analysis ADD COLUMN token_enc TEXT")
    if "zip_path" not in columns:
        conn.execute("ALTER TABLE project_analysis ADD COLUMN zip_path TEXT")

    if "project_name" in columns:
        # Copy project_name into project_id if project_id is NULL
        conn.execute(
            """
            UPDATE project_analysis
            SET project_id = COALESCE(project_id, project_name)
            WHERE project_id IS NULL
            """
        )
    conn.commit()

    # 3) legacy github_sources table migration into project_analysis
    legacy_source = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='github_sources'"
    ).fetchone()
    if legacy_source:
        rows = conn.execute("SELECT project_id, repo_url, token_enc, zip_path FROM github_sources").fetchall()
        for project_id, repo_url, token_enc, zip_path in rows:
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
                        token_enc,
                        zip_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project_id, "unknown", None, json.dumps({}), repo_url, token_enc, zip_path),
        )
        conn.execute("DROP TABLE github_sources")
        conn.commit()

    # content-addressable file store tables
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            hash TEXT UNIQUE,
            size_bytes INTEGER NOT NULL,
            mime TEXT,
            path TEXT NOT NULL,
            ref_count INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS uploads (
            upload_id TEXT PRIMARY KEY,
            original_name TEXT,
            uploader TEXT,
            source TEXT,
            hash TEXT NOT NULL,
            file_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_files_hash
        ON files (hash)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_uploads_file
        ON uploads (file_id)
        """
    )
    _repair_user_identity_links(conn)
    conn.commit()


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
        "SELECT id, username, email FROM users ORDER BY id"
    ).fetchall()

    # First pass: normalize/remove noreply emails while preserving uniqueness.
    for user_id, username, email in users:
        if not _is_noreply_email(email):
            continue
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? AND (email IS NULL OR TRIM(email) = '') ORDER BY id LIMIT 1",
            (username,),
        ).fetchone()
        if existing and int(existing[0]) != int(user_id):
            canonical_id = int(existing[0])
            conn.execute(
                "UPDATE contributor_stats SET user_id = ? WHERE user_id = ?",
                (canonical_id, int(user_id)),
            )
            old_links = conn.execute(
                """
                SELECT project_id, contributor_name
                FROM user_projects
                WHERE user_id = ?
                """,
                (int(user_id),),
            ).fetchall()
            for project_id, contributor_name in old_links:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO user_projects (user_id, project_id, contributor_name)
                    VALUES (?, ?, ?)
                    """,
                    (canonical_id, project_id, contributor_name),
                )
            conn.execute("DELETE FROM user_projects WHERE user_id = ?", (int(user_id),))
            conn.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        else:
            conn.execute("UPDATE users SET email = NULL WHERE id = ?", (int(user_id),))

    # Second pass: enforce contributor -> username mapping for every stats row.
    contributors = conn.execute(
        "SELECT DISTINCT contributor FROM contributor_stats WHERE contributor IS NOT NULL AND TRIM(contributor) != ''"
    ).fetchall()
    for (contributor,) in contributors:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? ORDER BY id LIMIT 1",
            (contributor,),
        ).fetchone()
        if row:
            canonical_user_id = int(row[0])
        else:
            cursor = conn.execute(
                "INSERT INTO users (username, email, github_url) VALUES (?, NULL, ?)",
                (contributor, _default_github_url(contributor)),
            )
            canonical_user_id = int(cursor.lastrowid)

        conn.execute(
            "UPDATE contributor_stats SET user_id = ? WHERE contributor = ?",
            (canonical_user_id, contributor),
        )

        projects = conn.execute(
            "SELECT DISTINCT project_id FROM contributor_stats WHERE contributor = ? AND project_id IS NOT NULL",
            (contributor,),
        ).fetchall()
        for (project_id,) in projects:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_projects (user_id, project_id, contributor_name)
                VALUES (?, ?, ?)
                """,
                (canonical_user_id, project_id, contributor),
            )
            conn.execute(
                """
                DELETE FROM user_projects
                WHERE contributor_name = ?
                  AND project_id = ?
                  AND user_id != ?
                """,
                (contributor, project_id, canonical_user_id),
            )


# -----------------------------
# DB lifecycle
# -----------------------------
def open_db(base_dir: Path | None = None) -> sqlite3.Connection:
    target_dir = base_dir or BASE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "capstone.db"

    logger.info("Opening database at %s", db_path)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass

    _initialize_schema(conn)
    _migrate_uploads_table(conn)

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

# --- migration: allow multiple uploads per upload_id (incremental snapshots)
def _migrate_uploads_table(conn: sqlite3.Connection) -> None:
    # Check if uploads exists
    uploads_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='uploads'"
    ).fetchone()

    if not uploads_exists:
        return

    # Check if uploads_old already exists
    uploads_old_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='uploads_old'"
    ).fetchone()

    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='uploads'"
    ).fetchone()

    if not row or not row[0]:
        return

    sql = row[0].lower()

    needs_migration = (
        "upload_id" in sql and
        ("primary key" in sql or "unique" in sql)
    )

    if not needs_migration:
        return

    # If uploads_old already exists, migration already ran
    if uploads_old_exists:
        return

    # Safe migration
    conn.execute("ALTER TABLE uploads RENAME TO uploads_old")

    conn.execute(
        """
        CREATE TABLE uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT NOT NULL,
            original_name TEXT,
            uploader TEXT,
            source TEXT,
            hash TEXT,
            file_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(file_id) REFERENCES files(file_id)
        )
        """
    )

    conn.execute(
        """
        INSERT INTO uploads (upload_id, original_name, uploader, source, hash, file_id, created_at)
        SELECT upload_id, original_name, uploader, source, hash, file_id, created_at
        FROM uploads_old
        """
    )

    conn.execute("DROP TABLE uploads_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uploads_upload_id ON uploads(upload_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uploads_file_id ON uploads(file_id)")
    conn.commit()
# Snapshots

def store_analysis_snapshot(
    conn: sqlite3.Connection,
    project_id: str,
    classification: str = "unknown",
    primary_contributor: str | None = None,
    snapshot: dict | None = None,
    zip_path: str | None = None, 
) -> None:
    """Insert a new snapshot row for a project."""
    if not project_id:
        raise ValueError("project_id must be provided")

    doc = dict(snapshot or {})
    doc.setdefault("project_id", project_id)
    doc.setdefault("classification", classification)
    doc.setdefault("primary_contributor", primary_contributor)

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
    (
        project_id,
        classification,
        primary_contributor,
        payload,
        zip_path,  # 👈 STORE IT HERE
    ),
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
    """

    rows = conn.execute(
        """
        SELECT pa.project_id,
               pa.snapshot,
               pa.zip_path,
               pa.created_at
        FROM project_analysis pa
        JOIN (
            SELECT project_id, MAX(datetime(created_at)) AS max_created
            FROM project_analysis
            GROUP BY project_id
        ) latest
          ON latest.project_id = pa.project_id
         AND datetime(pa.created_at) = latest.max_created
        ORDER BY datetime(pa.created_at) DESC
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
    source: str | None = None,
) -> None:
    if not project_id:
        raise ValueError("project_id must be provided")
    if not contributor:
        raise ValueError("contributor must be provided")

    conn.execute(
        """
        INSERT INTO contributor_stats (
            project_id,
            contributor,
            user_id,
            commits,
            pull_requests,
            issues,
            reviews,
            score,
            weights_hash,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            contributor,
            user_id,
            int(commits),
            int(pull_requests),
            int(issues),
            int(reviews),
            float(score),
            weights_hash,
            source,
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
        WITH latest_time AS (
            SELECT contributor, MAX(created_at) AS created_at
            FROM contributor_stats
            WHERE project_id = ?
            GROUP BY contributor
        ),
        latest_row AS (
            SELECT cs.contributor, MAX(cs.id) AS id
            FROM contributor_stats cs
            JOIN latest_time lt
              ON lt.contributor = cs.contributor
             AND lt.created_at = cs.created_at
            WHERE cs.project_id = ?
            GROUP BY cs.contributor
        )
        SELECT
            cs.id,
            cs.project_id,
            cs.contributor,
            cs.user_id,
            cs.commits,
            cs.pull_requests,
            cs.issues,
            cs.reviews,
            cs.score,
            cs.weights_hash,
            cs.source,
            cs.created_at
        FROM contributor_stats cs
        JOIN latest_row lr ON lr.id = cs.id
        ORDER BY cs.score DESC, cs.contributor ASC
        """,
        (project_id, project_id),
    )

    rows = cursor.fetchall()
    payload: list[dict] = []
    for row in rows:
        (
            row_id,
            project_id,
            contributor,
            user_id,
            commits,
            pull_requests,
            issues,
            reviews,
            score,
            weights_hash,
            source,
            created_at,
        ) = row
        payload.append(
            {
            "id": row_id,
            "project_id": project_id,
            "contributor": contributor,
            "user_id": user_id,
            "commits": commits,
            "pull_requests": pull_requests,
            "issues": issues,
            "reviews": reviews,
                "score": score,
                "weights_hash": weights_hash,
                "source": source,
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
        UPDATE contributor_stats
        SET score = ?, weights_hash = ?
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

def upsert_user(
    conn: sqlite3.Connection,
    username: str,
    *,
    email: str | None = None,
) -> int:
    if not username:
        raise ValueError("username must be provided")
    username = str(username).strip()
    email = _normalize_user_email(email)
    default_github = _default_github_url(username)

    # Prefer matching by email when available, otherwise by username.
    row = None
    if email:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE email = ? LIMIT 1",
            (email,),
        ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE username = ? LIMIT 1",
            (username,),
        ).fetchone()
    if row:
        user_id = int(row[0])
        conn.execute(
            """
            UPDATE users
            SET
                username = COALESCE(?, username),
                email = COALESCE(?, email),
                github_url = CASE
                    WHEN github_url IS NULL OR TRIM(github_url) = ''
                    THEN COALESCE(?, github_url)
                    ELSE github_url
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (username, email, default_github, user_id),
        )
        conn.commit()
        return user_id

    cursor = conn.execute(
        """
        INSERT INTO users (username, email, github_url)
        VALUES (?, ?, ?)
        """,
        (username, email, default_github),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_user_profile(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT
            id,
            username,
            email,
            full_name,
            phone_number,
            city,
            state_region,
            github_url,
            portfolio_url
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (int(user_id),),
    ).fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "username": row[1],
        "email": row[2],
        "full_name": row[3],
        "phone_number": row[4],
        "city": row[5],
        "state_region": row[6],
        "github_url": row[7],
        "portfolio_url": row[8],
    }


def update_user_profile(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    full_name: str | None = None,
    phone_number: str | None = None,
    city: str | None = None,
    state_region: str | None = None,
    github_url: str | None = None,
    portfolio_url: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE users
        SET
            full_name = COALESCE(?, full_name),
            phone_number = COALESCE(?, phone_number),
            city = COALESCE(?, city),
            state_region = COALESCE(?, state_region),
            github_url = COALESCE(?, github_url),
            portfolio_url = COALESCE(?, portfolio_url),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            full_name,
            phone_number,
            city,
            state_region,
            github_url,
            portfolio_url,
            int(user_id),
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
    resume_title: str | None = None,
    create_new: bool = False,
) -> str:
    """
    Ensure a draft modular resume exists for the user and persist default modules.
    - header/core_skill/project are refreshed from latest generated data.
    - summary/education/experience are ensured as empty templates (insert only when missing).
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
                "subtitle": project.get("stack") or "",
                "start_date": project.get("start_date") or "",
                "end_date": project.get("end_date") or "",
                "location": project.get("location") or "",
                "content": project.get("content") or "",
            }
        )
    _replace_items("project", project_items)

    # Ensure empty templates for summary/education/experience (insert only if missing).
    # Education/Experience placeholders use entry-title defaults expected by PDF rendering.
    template_titles = {
        "summary": "Summary",
        "education": "University",
        "experience": "Event",
    }
    for key, label in (("summary", "Summary"), ("education", "Education"), ("experience", "Experience")):
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
                (str(uuid.uuid4()), section_id, template_titles[key]),
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
    """List all resumes for a user (no sections/items)."""
    rows = conn.execute(
        """
        SELECT id, user_id, title, target_role, status, created_at, updated_at
        FROM resumes
        WHERE user_id = ?
        ORDER BY datetime(updated_at) DESC, id DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [
        {
            "id": r[0], "user_id": r[1], "title": r[2],
            "target_role": r[3], "status": r[4],
            "created_at": r[5], "updated_at": r[6],
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


def link_user_to_project(
    conn: sqlite3.Connection,
    user_id: int,
    project_id: str,
    *,
    contributor_name: str | None = None,
    first_commit_at: str | None = None,
    last_commit_at: str | None = None,
) -> None:
    if not user_id:
        raise ValueError("user_id must be provided")
    if not project_id:
        raise ValueError("project_id must be provided")
    conn.execute(
        """
        INSERT OR IGNORE INTO user_projects (
            user_id, project_id, contributor_name, first_commit_at, last_commit_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(user_id), project_id, contributor_name, first_commit_at, last_commit_at),
    )
    existing = conn.execute(
        """
        SELECT contributor_name, first_commit_at, last_commit_at
        FROM user_projects
        WHERE user_id = ? AND project_id = ?
        """,
        (int(user_id), project_id),
    ).fetchone()
    if existing:
        merged_name = contributor_name if contributor_name is not None else existing[0]
        merged_first = existing[1]
        merged_last = existing[2]
        if first_commit_at and (not merged_first or str(first_commit_at) < str(merged_first)):
            merged_first = first_commit_at
        if last_commit_at and (not merged_last or str(last_commit_at) > str(merged_last)):
            merged_last = last_commit_at
        conn.execute(
            """
            UPDATE user_projects
            SET contributor_name = ?, first_commit_at = ?, last_commit_at = ?
            WHERE user_id = ? AND project_id = ?
            """,
            (merged_name, merged_first, merged_last, int(user_id), project_id),
        )
    conn.commit()


def fetch_user_project_activity_periods(
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
        FROM user_projects
        WHERE user_id = ?
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


def upsert_users_from_contributors(
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
        username = getattr(row, "contributor", None) or getattr(row, "username", None)
        email = getattr(row, "email", None)
        if not username:
            continue
        user_id = upsert_user(conn, username, email=email)
        link_user_to_project(conn, user_id, project_id, contributor_name=username)

def save_project_metadata(conn, project_id, meta):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO project_metadata
        (project_id, start_date, end_date, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            project_id,
            meta["start_date"],
            meta["end_date"],
            meta["status"],
        ),
    )
    conn.commit()

def load_project_metadata(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT project_id, start_date, end_date, status FROM project_metadata")

    return {
        row[0]: {
            "start_date": row[1],
            "end_date": row[2],
            "status": row[3],
        }
        for row in cursor.fetchall()
    }

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
    # users
    "upsert_user",
    "get_user_profile",
    "update_user_profile",
    "upsert_default_resume_modules",
    "link_user_to_project",
    "fetch_user_project_activity_periods",
    "upsert_users_from_contributors",
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
