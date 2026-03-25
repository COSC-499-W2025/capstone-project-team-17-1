from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from uuid import uuid4

from .logging_utils import get_logger
from .storage import fetch_latest_snapshot

logger = get_logger(__name__)

DEFAULT_SECTIONS: Tuple[str, ...] = (
    "summary",
    "experience",
    "projects",
    "skills",
    "education",
    "achievements",
)


@dataclass(frozen=True)
class ResumeEntry:
    id: str
    section: str
    title: str
    summary: Optional[str]
    body: str
    status: str
    created_at: str
    updated_at: str
    project_ids: Tuple[str, ...]
    skills: Tuple[str, ...]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "section": self.section,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "projects": list(self.project_ids),
            "skills": list(self.skills),
            "metadata": self.metadata,
        }

    @property
    def created(self) -> Optional[datetime]:
        return _parse_dt(self.created_at)

    @property
    def updated(self) -> Optional[datetime]:
        return _parse_dt(self.updated_at)

    def is_outdated(self) -> bool:
        expiry = self.metadata.get("expires_at")
        if not expiry:
            return False
        expiry_dt = _parse_dt(expiry)
        if not expiry_dt:
            return False
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        return expiry_dt < datetime.now(timezone.utc)


@dataclass(frozen=True)
class ResumeRetrievalResult:
    entries: List[ResumeEntry]
    warnings: List[str]
    missing_sections: List[str]
    schema_state: Dict[str, Any]


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def ensure_resume_schema(conn: sqlite3.Connection) -> None:
    # Minimal schema
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS resume_entries (
            id TEXT PRIMARY KEY,
            section TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS resume_entry_links (
            entry_id TEXT NOT NULL,
            link_type TEXT NOT NULL CHECK(link_type IN ('project','skill')),
            link_value TEXT NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES resume_entries(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_resume_entry_links
        ON resume_entry_links(link_type, link_value, entry_id);
        """
    )
    _ensure_resume_project_description_table(conn)
    conn.commit()


def _ensure_resume_project_description_table(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='resume_project_descriptions'"
    ).fetchone()
    if not exists:
        # create the multi-variant wording table
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS resume_project_descriptions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                variant_name TEXT,
                audience TEXT,
                summary TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_resume_project_descriptions_project
            ON resume_project_descriptions(project_id, is_active, updated_at);
            """
        )
        return
    columns = {row[1] for row in conn.execute("PRAGMA table_info(resume_project_descriptions)").fetchall()}
    if "id" in columns:
        return
    # Legacy table had project_id as the primary key
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS resume_project_descriptions_v2 (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            variant_name TEXT,
            audience TEXT,
            summary TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );
        INSERT INTO resume_project_descriptions_v2(
            id, project_id, variant_name, audience, summary, is_active, created_at, updated_at, metadata
        )
        SELECT
            lower(hex(randomblob(16))),
            project_id,
            NULL,
            NULL,
            summary,
            1,
            created_at,
            updated_at,
            metadata
        FROM resume_project_descriptions;
        DROP TABLE resume_project_descriptions;
        ALTER TABLE resume_project_descriptions_v2 RENAME TO resume_project_descriptions;
        CREATE INDEX IF NOT EXISTS idx_resume_project_descriptions_project
        ON resume_project_descriptions(project_id, is_active, updated_at);
        """
    )


@dataclass(frozen=True)
class ResumeProjectDescription:
    id: str
    project_id: str
    variant_name: Optional[str]
    audience: Optional[str]
    summary: str
    is_active: bool
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "variant_name": self.variant_name,
            "audience": self.audience,
            "summary": self.summary,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


def describe_resume_schema(conn: sqlite3.Connection) -> Dict[str, Any]:
    ensure_resume_schema(conn)
    tables = {}
    counts = {}
    for table in ("resume_entries", "resume_entry_links", "resume_project_descriptions"):
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        columns = [
            {"name": row[1], "type": row[2], "notnull": bool(row[3]), "default": row[4]}
            for row in info
        ]
        tables[table] = columns
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return {"tables": tables, "counts": counts}

#insert resume 
def insert_resume_entry(
    conn: sqlite3.Connection,
    *,
    section: str,
    title: str,
    body: str,
    summary: Optional[str] = None,
    status: str = "active",
    metadata: Optional[Dict[str, Any]] = None,
    projects: Optional[Sequence[str]] = None,
    skills: Optional[Sequence[str]] = None,
    entry_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> str:
    ensure_resume_schema(conn)
    section = section.lower()
    if not status:
        status = "active"
    metadata = metadata or {}
    payload = json.dumps(metadata)
    projects = list(dict.fromkeys(projects or []))
    skills = [str(s).lower() for s in (skills or [])]
    skills = list(dict.fromkeys(skills))
    # Skip insertion 
    duplicate_id = _find_duplicate_resume_entry(
        conn,
        section=section,
        title=title,
        body=body,
        summary=summary,
        status=status,
        metadata=metadata,
        projects=projects,
        skills=skills,
    )
    if duplicate_id:
        return duplicate_id
    entry_id = entry_id or str(uuid4())
    conn.execute( # insert into entries
        """
        INSERT INTO resume_entries(id, section, title, summary, body, status, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (entry_id, section, title, summary, body, status, payload),
    )
    if created_at:
        conn.execute(
            """
            UPDATE resume_entries
            SET created_at=?, updated_at=?
            WHERE id=?
            """,
            (created_at, created_at, entry_id),
        )
    _insert_links(conn, entry_id, projects, skills)
    conn.commit()
    return entry_id


def _insert_links(conn: sqlite3.Connection, entry_id: str, projects: Sequence[str], skills: Sequence[str]) -> None:
    for pid in dict.fromkeys(projects):
        conn.execute(
            "INSERT INTO resume_entry_links(entry_id, link_type, link_value) VALUES (?, 'project', ?)",
            (entry_id, pid),
        )
    for skill in dict.fromkeys(skills):
        conn.execute(
            "INSERT INTO resume_entry_links(entry_id, link_type, link_value) VALUES (?, 'skill', ?)",
            (entry_id, skill.lower()),
        )


def _find_duplicate_resume_entry(
    conn: sqlite3.Connection,
    *,
    section: str,
    title: str,
    body: str,
    summary: Optional[str],
    status: str,
    metadata: Dict[str, Any],
    projects: Sequence[str],
    skills: Sequence[str],
) -> Optional[str]:
    # Detect duplicate entries
    rows = conn.execute(
        """
        SELECT id, summary, status, metadata
        FROM resume_entries
        WHERE section = ? AND title = ? AND body = ?
        """,
        (section, title, body),
    ).fetchall()
    if not rows:
        return None
    target_projects = tuple(sorted(projects))
    target_skills = tuple(sorted(skills))
    links = _fetch_links(conn, [row[0] for row in rows])
    for row in rows:
        if row[1] != summary:
            continue
        if row[2] != status:
            continue
        raw_meta = row[3]
        if raw_meta:
            try:
                stored_meta = json.loads(raw_meta)
            except json.JSONDecodeError:
                stored_meta = {}
        else:
            stored_meta = {}
        if stored_meta != metadata:
            continue
        link = links.get(row[0], {})
        if tuple(sorted(link.get("project", ()))) != target_projects:
            continue
        if tuple(sorted(link.get("skill", ()))) != target_skills:
            continue
        return row[0]
    return None


def get_resume_entry(conn: sqlite3.Connection, entry_id: str) -> Optional[ResumeEntry]:
    ensure_resume_schema(conn)
    row = conn.execute(
        """
        SELECT id, section, title, summary, body, status, created_at, updated_at, metadata
        FROM resume_entries
        WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()
    if not row:
        return None
    link_map = _fetch_links(conn, [entry_id])
    return _row_to_entry(row, link_map)


def update_resume_entry(
    conn: sqlite3.Connection,
    *,
    entry_id: str,
    section: Any = None,
    title: Any = None,
    summary: Any = None,
    body: Any = None,
    status: Any = None,
    metadata: Any = None,
    projects: Any = None,
    skills: Any = None,
    _summary_provided: bool = False,
    _metadata_provided: bool = False,
    _projects_provided: bool = False,
    _skills_provided: bool = False,
) -> Optional[ResumeEntry]:
    ensure_resume_schema(conn)
    existing = get_resume_entry(conn, entry_id)
    if not existing:
        return None

    updates: List[str] = []
    params: List[Any] = []
    if section is not None:
        updates.append("section = ?")
        params.append(str(section).lower())
    if title is not None:
        updates.append("title = ?")
        params.append(str(title))
    if body is not None:
        updates.append("body = ?")
        params.append(str(body))
    if status is not None:
        updates.append("status = ?")
        params.append(str(status))
    if _summary_provided:
        updates.append("summary = ?")
        params.append(summary)
    if _metadata_provided:
        updates.append("metadata = ?")
        params.append(json.dumps(metadata or {}))

    if updates:
        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(entry_id)
        conn.execute(
            f"UPDATE resume_entries SET {', '.join(updates)} WHERE id = ?",
            params,
        )

    if _projects_provided or _skills_provided:
        conn.execute("DELETE FROM resume_entry_links WHERE entry_id = ?", (entry_id,))
        _insert_links(
            conn,
            entry_id,
            projects if _projects_provided and isinstance(projects, (list, tuple)) else (),
            skills if _skills_provided and isinstance(skills, (list, tuple)) else (),
        )

    conn.commit()
    return get_resume_entry(conn, entry_id)
#query 
def query_resume_entries(
    conn: sqlite3.Connection,
    *,
    sections: Optional[Sequence[str]] = None,
    keywords: Optional[Sequence[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_outdated: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> ResumeRetrievalResult:
    ensure_resume_schema(conn)
    where: List[str] = []
    params: List[Any] = []
    if sections:
        normalized = [s.lower() for s in sections]
        placeholders = ",".join("?" * len(normalized))
        where.append(f"section IN ({placeholders})")
        params.extend(normalized)
    if keywords:
        for keyword in keywords:
            pattern = f"%{keyword.lower()}%"
            where.append("(LOWER(title) LIKE ? OR LOWER(COALESCE(summary,'')) LIKE ? OR LOWER(body) LIKE ?)")
            params.extend([pattern, pattern, pattern])
    if start_date:
        where.append("date(created_at) >= date(?)")
        params.append(start_date)
    if end_date:
        where.append("date(created_at) <= date(?)")
        params.append(end_date)
    if not include_outdated:
        where.append("status = 'active'")
    else:
        where.append("status != 'deleted'")

    where_sql = " AND ".join(where) if where else "1=1"
    rows = conn.execute(
        f"""
        SELECT id, section, title, summary, body, status, created_at, updated_at, metadata
        FROM resume_entries
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (*params, max(1, limit), max(0, offset)),
    ).fetchall()

    entry_ids = [row[0] for row in rows]
    link_map = _fetch_links(conn, entry_ids)
    keep: List[ResumeEntry] = []
    warnings: List[str] = []
    excluded = 0
    for row in rows:
        entry = _row_to_entry(row, link_map)
        if entry.is_outdated() and not include_outdated:
            excluded += 1
            continue
        keep.append(entry)

    if excluded:
        warnings.append(f"Skipped {excluded} outdated resume item(s); rerun with include_outdated=True to review them.")
    sections_present = sorted({entry.section for entry in keep})
    missing_sections = [sec for sec in DEFAULT_SECTIONS if sec not in sections_present]
    if missing_sections:
        warnings.append(f"No saved resume entries for section(s): {', '.join(missing_sections)}.")
    schema_state = describe_resume_schema(conn)
    return ResumeRetrievalResult(entries=keep, warnings=warnings, missing_sections=missing_sections, schema_state=schema_state)


def _row_to_entry(row: sqlite3.Row | Sequence[Any], link_map: Dict[str, Dict[str, Tuple[str, ...]]]) -> ResumeEntry:
    metadata = {}
    if row[8]:
        try:
            metadata = json.loads(row[8])
        except json.JSONDecodeError:
            logger.warning("Failed to parse metadata for resume entry %s", row[0])
            metadata = {}
    links = link_map.get(row[0], {"project": (), "skill": ()})
    return ResumeEntry(
        id=row[0],
        section=row[1],
        title=row[2],
        summary=row[3],
        body=row[4],
        status=row[5],
        created_at=row[6],
        updated_at=row[7],
        project_ids=links.get("project", ()),
        skills=links.get("skill", ()),
        metadata=metadata,
    )

#fetch the links
def _fetch_links(conn: sqlite3.Connection, entry_ids: Sequence[str]) -> Dict[str, Dict[str, Tuple[str, ...]]]:
    if not entry_ids:
        return {}
    placeholders = ",".join("?" * len(entry_ids))
    rows = conn.execute(
        f"""
        SELECT entry_id, link_type, link_value
        FROM resume_entry_links
        WHERE entry_id IN ({placeholders})
        """,
        entry_ids,
    ).fetchall()
    mapping: Dict[str, Dict[str, List[str]]] = {}
    for entry_id, link_type, value in rows:
        mapping.setdefault(entry_id, {}).setdefault(link_type, []).append(value)
    return {
        entry_id: {
            link_type: tuple(values)
            for link_type, values in link_dict.items()
        }
        for entry_id, link_dict in mapping.items()
    }


def upsert_resume_project_description(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    summary: str,
    variant_name: Optional[str] = None,
    audience: Optional[str] = None,
    is_active: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> ResumeProjectDescription:
    ensure_resume_schema(conn)
    if not project_id:
        raise ValueError("project_id must be provided")
    if not summary:
        raise ValueError("summary must be provided")
    now = updated_at or datetime.now(timezone.utc).isoformat()
    created_value = created_at or now
    payload = json.dumps(metadata or {})
    row = conn.execute(
        """
        SELECT id
        FROM resume_project_descriptions
        WHERE project_id = ?
          AND variant_name IS ?
          AND audience IS ?
        LIMIT 1
        """,
        (project_id, variant_name, audience),
    ).fetchone()
    if row:
        entry_id = row[0]
        conn.execute(
            """
            UPDATE resume_project_descriptions
            SET summary = ?, metadata = ?, is_active = ?, updated_at = ?
            WHERE id = ?
            """,
            (summary, payload, 1 if is_active else 0, now, entry_id),
        )
    else:
        entry_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO resume_project_descriptions(
                id, project_id, variant_name, audience, summary, is_active, metadata, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (entry_id, project_id, variant_name, audience, summary, 1 if is_active else 0, payload, created_value, now),
        )
    if is_active:
        # Keep a single active wording per project
        conn.execute(
            """
            UPDATE resume_project_descriptions
            SET is_active = 0
            WHERE project_id = ? AND id != ?
            """,
            (project_id, entry_id),
        )
    conn.commit()
    result = get_resume_project_description(
        conn,
        project_id,
        variant_name=variant_name,
        audience=audience,
        active_only=False,
    )
    if result is None:
        raise RuntimeError("Failed to persist resume project description")
    return result


def get_resume_project_description(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    variant_name: Optional[str] = None,
    audience: Optional[str] = None,
    active_only: bool = True,
) -> Optional[ResumeProjectDescription]:
    ensure_resume_schema(conn)
    if variant_name is not None or audience is not None:
        row = conn.execute(
            """
            SELECT id, project_id, variant_name, audience, summary, is_active, created_at, updated_at, metadata
            FROM resume_project_descriptions
            WHERE project_id = ?
              AND variant_name IS ?
              AND audience IS ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (project_id, variant_name, audience),
        ).fetchone()
        return _row_to_project_description(row) if row else None
    if active_only:
        row = conn.execute(
            """
            SELECT id, project_id, variant_name, audience, summary, is_active, created_at, updated_at, metadata
            FROM resume_project_descriptions
            WHERE project_id = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, project_id, variant_name, audience, summary, is_active, created_at, updated_at, metadata
            FROM resume_project_descriptions
            WHERE project_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
    return _row_to_project_description(row) if row else None


def list_resume_project_descriptions(
    conn: sqlite3.Connection,
    *,
    project_ids: Optional[Sequence[str]] = None,
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> List[ResumeProjectDescription]:
    ensure_resume_schema(conn)
    where = []
    params: List[Any] = []
    if project_ids:
        placeholders = ",".join("?" * len(project_ids))
        where.append(f"project_id IN ({placeholders})")
        params.extend(list(project_ids))
    if active_only:
        where.append("is_active = 1")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"""
        SELECT id, project_id, variant_name, audience, summary, is_active, created_at, updated_at, metadata
        FROM resume_project_descriptions
        {where_sql}
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (*params, max(1, limit), max(0, offset)),
    ).fetchall()
    return [_row_to_project_description(row) for row in rows]


def delete_resume_project_description(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    variant_name: Optional[str] = None,
    audience: Optional[str] = None,
    active_only: bool = True,
) -> int:
    ensure_resume_schema(conn)
    if not project_id:
        raise ValueError("project_id must be provided")
    where = ["project_id = ?"]
    params: List[Any] = [project_id]
    if variant_name is not None:
        where.append("variant_name IS ?")
        params.append(variant_name)
    if audience is not None:
        where.append("audience IS ?")
        params.append(audience)
    if active_only:
        where.append("is_active = 1")
    sql = f"""
        DELETE FROM resume_project_descriptions
        WHERE {' AND '.join(where)}
    """
    cur = conn.execute(sql, params)
    conn.commit()
    return int(cur.rowcount or 0)


def _row_to_project_description(row: sqlite3.Row | Sequence[Any]) -> ResumeProjectDescription:
    metadata: Dict[str, Any] = {}
    if row[8]:
        try:
            metadata = json.loads(row[8])
        except json.JSONDecodeError:
            logger.warning("Failed to parse metadata for resume project %s", row[1])
            metadata = {}
    return ResumeProjectDescription(
        id=row[0],
        project_id=row[1],
        variant_name=row[2],
        audience=row[3],
        summary=row[4],
        is_active=bool(row[5]),
        created_at=row[6],
        updated_at=row[7],
        metadata=metadata,
    )


def resolve_resume_projects(conn: sqlite3.Connection, entries: Iterable[ResumeEntry]) -> Dict[str, Optional[dict]]:
    ids = sorted({pid for entry in entries for pid in entry.project_ids})
    context: Dict[str, Optional[dict]] = {}
    for pid in ids:
        context[pid] = fetch_latest_snapshot(conn, pid)
    return context


def resolve_resume_project_descriptions(
    conn: sqlite3.Connection,
    entries: Iterable[ResumeEntry],
) -> Dict[str, Optional[dict]]:
    ids = sorted({pid for entry in entries for pid in entry.project_ids})
    if not ids:
        return {}
    descriptions = list_resume_project_descriptions(conn, project_ids=ids, active_only=True, limit=len(ids))
    by_id = {desc.project_id: desc.to_dict() for desc in descriptions}
    return {pid: by_id.get(pid) for pid in ids}


def build_resume_project_summary(project_id: str, snapshot: Mapping[str, Any]) -> str:
    name = str(snapshot.get("project_name") or snapshot.get("project") or snapshot.get("project_id") or project_id)
    classification = snapshot.get("classification") or snapshot.get("project_type")
    file_summary = snapshot.get("file_summary") if isinstance(snapshot.get("file_summary"), dict) else {}

    file_count = _coerce_int(file_summary.get("file_count"))
    active_days = _coerce_int(file_summary.get("active_days") or file_summary.get("duration_days"))

    languages = snapshot.get("languages") if isinstance(snapshot.get("languages"), dict) else {}
    frameworks = snapshot.get("frameworks") or []
    skills = snapshot.get("skills") or []

    stack_items: List[str] = []
    for name_item in _normalise_list(frameworks):
        stack_items.append(name_item)
    _lang_list = [{"skill": k, "confidence": float(v)} for k, v in languages.items()]
    for name_item in _pick_top_skill_names(_lang_list, limit=2):
        stack_items.append(name_item)
    for name_item in _pick_top_skill_names(skills, limit=2):
        stack_items.append(name_item)

    stack_items = _dedupe_preserve_order(stack_items)
    stack_text = f" using {', '.join(stack_items[:3])}" if stack_items else ""
    if classification:
        opening = f"Built {name}, a {classification} project{stack_text}."
    else:
        opening = f"Built {name}{stack_text}."

    impact_parts: List[str] = []
    if file_count:
        impact_parts.append(f"{file_count} files")
    if active_days:
        impact_parts.append(f"{active_days} active days")
    if impact_parts:
        return f"{opening} Delivered {', '.join(impact_parts)}."
    return opening


def build_resume_project_item(
    project_id: str,
    snapshot: Mapping[str, Any],
    *,
    contributor_name: str = "",
    data_user_id: Optional[int] = None,
    contributor_stats_map: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Return a rich project item dict for resume sections.

    Populates title, subtitle, start_date, end_date, content, and bullets
    from the analysis snapshot, replacing the bare single-sentence summary.
    """
    name = str(snapshot.get("project_name") or snapshot.get("project") or snapshot.get("project_id") or project_id)
    file_summary = snapshot.get("file_summary") if isinstance(snapshot.get("file_summary"), dict) else {}
    collaboration = snapshot.get("collaboration") if isinstance(snapshot.get("collaboration"), dict) else {}

    # Prefer git commit dates (accurate) over ZIP file modification timestamps (unreliable)
    earliest = str(collaboration.get("first_commit_date") or file_summary.get("earliest_modification") or "")
    latest = str(collaboration.get("last_commit_date") or file_summary.get("latest_modification") or "")

    languages = snapshot.get("languages") if isinstance(snapshot.get("languages"), dict) else {}
    frameworks = snapshot.get("frameworks") or []

    # --- subtitle: frameworks first, then top languages, then skills ---
    stack_items: List[str] = []
    for fw in _normalise_list(frameworks):
        stack_items.append(fw)
    _lang_list = [{"skill": k, "confidence": float(v)} for k, v in languages.items()]
    for lang in _pick_top_skill_names(_lang_list, limit=3):
        stack_items.append(lang)
    _raw_skills = snapshot.get("skills") or []
    if isinstance(_raw_skills, dict):
        _raw_skills = [{"skill": k, "confidence": float(v)} for k, v in _raw_skills.items()]
    for sk in _pick_top_skill_names(_raw_skills, limit=3):
        stack_items.append(sk)
    stack_items = _dedupe_preserve_order(stack_items)[:5]
    subtitle = ", ".join(stack_items)

    # --- dates: Mon YYYY (e.g. "Jan 2026") ---
    _MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    def _to_mon_year(iso: str) -> str:
        try:
            year = int(iso[:4])
            month = int(iso[5:7])
            return f"{_MONTHS[month - 1]} {year}"
        except Exception:
            return ""

    start_date = _to_mon_year(earliest)
    end_date = _to_mon_year(latest)

    # --- role inference from skills ---
    _BACKEND_SKILLS = {"python", "java", "go", "rust", "php", "ruby", "c", "c++",
                       "kotlin", "swift", "scala", "shell", "sql", "r"}
    _FRONTEND_SKILLS = {"javascript", "typescript", "css", "html", "scss", "less",
                        "vue", "svelte"}
    skills_dict = snapshot.get("skills") if isinstance(snapshot.get("skills"), dict) else {}
    # Merge with languages for role detection
    all_skill_keys = {k.lower() for k in list(skills_dict.keys()) + list(languages.keys())}
    _has_backend = bool(all_skill_keys & _BACKEND_SKILLS)
    _has_frontend = bool(all_skill_keys & _FRONTEND_SKILLS)
    if _has_backend and _has_frontend:
        role_label = "full-stack "
    elif _has_backend:
        role_label = "backend "
    elif _has_frontend:
        role_label = "frontend "
    else:
        role_label = ""

    # --- primary language phrase (Template 1) ---
    # Prefer skills dict (ZIP) or languages dict (GitHub), pick top 2 by count
    _skill_counts: List[tuple] = []
    for k, v in skills_dict.items():
        try:
            _skill_counts.append((k, int(v)))
        except Exception:
            pass
    for k, v in languages.items():
        if not any(k == s for s, _ in _skill_counts):
            try:
                _skill_counts.append((k, int(float(v))))
            except Exception:
                pass
    _skill_counts.sort(key=lambda x: -x[1])
    top_langs = [_normalise_lang_name(s) for s, _ in _skill_counts[:2] if s]
    lang_sentence = ""
    if top_langs:
        lang_sentence = f" Primarily built with {' and '.join(top_langs)}."

    # --- contribution stats ---
    # contributor_name (passed in) takes priority; fall back to snapshot's primary_contributor
    _snapshot_primary = str(collaboration.get("primary_contributor") or "")
    target_contributor = contributor_name.strip() or _snapshot_primary

    total_commits = primary_commits = contributor_count = 0
    total_prs = primary_prs = total_issues = primary_issues = total_reviews = primary_reviews = 0
    _has_prs_schema = False

    if contributor_stats_map:
        # contributor_stats table has full GitHub API data (commits + PRs + issues + reviews)
        _has_prs_schema = True
        contributor_count = len(contributor_stats_map)
        for cname, cstats in contributor_stats_map.items():
            c  = _coerce_int(cstats.get("commits"))
            p  = _coerce_int(cstats.get("pull_requests"))
            ii = _coerce_int(cstats.get("issues"))
            rv = _coerce_int(cstats.get("reviews"))
            total_commits += c
            total_prs     += p
            total_issues  += ii
            total_reviews += rv
            # Match by user_id first (reliable), then fall back to name comparison
            uid_set = cstats.get("user_ids") or set()
            is_target = (
                (data_user_id and data_user_id in uid_set)
                or (target_contributor and cname.lower() == target_contributor.lower())
            )
            if is_target:
                primary_commits = c
                primary_prs     = p
                primary_issues  = ii
                primary_reviews = rv
    else:
        # Fall back to snapshot collaboration dict (git-log only: commits + line_changes)
        _prs_key = "contributors (commits, PRs, issues, reviews)"
        _lines_key = "contributors (commits, line changes, reviews)"
        contrib_raw = collaboration.get(_prs_key) or collaboration.get(_lines_key) or {}
        _has_prs_schema = _prs_key in collaboration

        if isinstance(contrib_raw, dict):
            contributor_count = len(contrib_raw)
            for cname, cdata in contrib_raw.items():
                if isinstance(cdata, str):
                    import ast as _ast
                    try:
                        cdata = _ast.literal_eval(cdata)
                    except Exception:
                        cdata = _coerce_int(cdata)
                if isinstance(cdata, (list, tuple)):
                    c  = _coerce_int(cdata[0]) if len(cdata) > 0 else 0
                    p  = _coerce_int(cdata[1]) if len(cdata) > 1 else 0
                    ii = _coerce_int(cdata[2]) if len(cdata) > 2 and _has_prs_schema else 0
                    rv = _coerce_int(cdata[3] if _has_prs_schema else cdata[2]) if len(cdata) > (3 if _has_prs_schema else 2) else 0
                else:
                    c = _coerce_int(cdata)
                    p = ii = rv = 0
                total_commits += c
                total_prs     += p
                total_issues  += ii
                total_reviews += rv
                if target_contributor and cname.lower() == target_contributor.lower():
                    primary_commits = c
                    primary_prs     = p
                    primary_issues  = ii
                    primary_reviews = rv

    # --- contribution sentence ---
    contrib_sentence = ""
    if contributor_count <= 1:
        contrib_sentence = " Sole contributor with 100% contribution."
    elif total_commits:
        if _has_prs_schema:
            _total_activity = total_prs + total_issues + total_reviews
            _primary_activity = primary_prs + primary_issues + primary_reviews
            if _total_activity:
                pct = round(_primary_activity / _total_activity * 100)
            elif primary_commits:
                pct = round(primary_commits / total_commits * 100)
            else:
                pct = round(100 / contributor_count)
        elif primary_commits:
            pct = round(primary_commits / total_commits * 100)
        else:
            pct = round(100 / contributor_count)
        details: List[str] = []
        if _has_prs_schema:
            # GitHub API data: show PRs / issues / reviews
            if total_prs:     details.append(f"{primary_prs}/{total_prs} PRs")
            if total_issues:  details.append(f"{primary_issues}/{total_issues} issues")
            if total_reviews: details.append(f"{primary_reviews}/{total_reviews} reviews")
        else:
            # git-log data: show commits count as the breakdown
            details.append(f"{primary_commits}/{total_commits} commits")
        detail_str = f" ({', '.join(details)})" if details else ""
        _article = "an" if str(contributor_count)[0] in "8" or contributor_count in (11, 18) else "a"
        contrib_sentence = f" Contributed ~{pct}% in {_article} {contributor_count}-person team{detail_str}."

    # --- role sentence (separate, omit if undetected) ---
    if role_label == "full-stack ":
        role_sentence = " Worked as a full-stack developer."
    elif role_label == "backend ":
        role_sentence = " Worked as a backend developer."
    elif role_label == "frontend ":
        role_sentence = " Worked as a frontend developer."
    else:
        role_sentence = ""

    # --- content: professional sentences ---
    if contributor_count <= 1:
        type_label = "individual "
    else:
        type_label = "collaborative "
    content = f"Developed {type_label}project.{lang_sentence}{role_sentence}{contrib_sentence}"

    # --- bullets ---
    bullets: List[str] = []

    return {
        "title": name,
        "subtitle": subtitle,
        "start_date": start_date,
        "end_date": end_date,
        "content": content,
        "bullets": bullets,
    }


def generate_resume_project_descriptions(
    conn: sqlite3.Connection,
    *,
    project_ids: Sequence[str],
    overwrite: bool = False,
) -> List[ResumeProjectDescription]:
    ensure_resume_schema(conn)
    results: List[ResumeProjectDescription] = []
    now = datetime.now(timezone.utc).isoformat()
    for project_id in project_ids:
        if not project_id:
            continue
        existing_active = get_resume_project_description(conn, str(project_id))
        if existing_active and not overwrite:
            summary = existing_active.summary
            if summary:
                conn.execute(
                    """
                    UPDATE resume_entries
                    SET summary = ?, updated_at = ?
                    WHERE id IN (
                        SELECT entry_id
                        FROM resume_entry_links
                        WHERE link_type = 'project' AND link_value = ?
                    )
                    AND (summary IS NULL OR TRIM(summary) = '')
                    """,
                    (summary, now, str(project_id)),
                )
            results.append(existing_active)
            continue
        snapshot = fetch_latest_snapshot(conn, str(project_id))
        if not snapshot:
            logger.warning("No snapshot found for resume project %s", project_id)
            continue
        active = True
        if existing_active:
            # Avoid overriding a custom active wording with auto-generated content.
            source = (existing_active.metadata or {}).get("source")
            if source == "custom":
                active = False
        summary = build_resume_project_summary(str(project_id), snapshot)
        item = upsert_resume_project_description(
            conn,
            project_id=str(project_id),
            summary=summary,
            variant_name="auto",
            is_active=active,
            metadata={"source": "auto", "generated_at": now},
        )
        # Write back auto summaries into linked resume entries when blank.
        conn.execute(
            """
            UPDATE resume_entries
            SET summary = ?, updated_at = ?
            WHERE id IN (
                SELECT entry_id
                FROM resume_entry_links
                WHERE link_type = 'project' AND link_value = ?
            )
            AND (summary IS NULL OR TRIM(summary) = '')
            """,
            (summary, now, str(project_id)),
        )
        results.append(item)
    return results


def build_resume_preview(
    result: ResumeRetrievalResult,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    resume_project_descriptions = (
        resolve_resume_project_descriptions(conn, result.entries) if conn else {}
    )
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in result.entries:
        override_summary, source = _resolve_summary_override(entry, resume_project_descriptions)
        fallback = entry.body.splitlines()[0] if entry.body.splitlines() else entry.body
        excerpt = (override_summary or entry.summary or fallback or entry.title).strip()
        grouped[entry.section].append(
            {
                "id": entry.id,
                "section": entry.section,
                "title": entry.title,
                "excerpt": excerpt,
                "source": source,
                "updated_at": entry.updated_at,
                "metadata": entry.metadata,
                "entrySummary": entry.summary,
                "entryBody": entry.body,
                "status": entry.status,
                "projectIds": list(entry.project_ids),
                "skills": list(entry.skills),
            }
        )
    sections_payload = []
    for section in DEFAULT_SECTIONS:
        items = grouped.get(section, [])
        if not items:
            continue
        sections_payload.append({"name": section, "items": items})
    extra_sections = sorted(set(grouped.keys()) - set(DEFAULT_SECTIONS))
    for section in extra_sections:
        sections_payload.append({"name": section, "items": grouped[section]})

    project_context = resolve_resume_projects(conn, result.entries) if conn else {}
    updated_values: List[datetime] = []
    for entry in result.entries:
        updated = entry.updated
        if not updated:
            continue
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        updated_values.append(updated)
    last_updated = max(updated_values, default=None)
    preview = {
        "sections": sections_payload,
        "warnings": result.warnings,
        "missingSections": result.missing_sections,
        "schema": result.schema_state,
        "projectContext": project_context,
        "resumeProjectDescriptions": resume_project_descriptions,
        "lastUpdated": last_updated.isoformat() if last_updated else None,
    }
    return preview


def resume_to_markdown(
    entries: Sequence[ResumeEntry],
    *,
    project_descriptions: Optional[Mapping[str, ResumeProjectDescription]] = None,
) -> str:
    grouped = _group_by_section(entries)
    lines: List[str] = []
    for section, items in grouped:
        lines.append(f"## {section.title()}")
        for entry in items:
            period = _format_period(entry.metadata)
            summary = _resolve_entry_summary(entry, project_descriptions)
            lines.append(f"- **{entry.title}** {period} — {summary.strip()}")
            if entry.skills:
                lines.append(f"  - Skills: {', '.join(entry.skills)}")
        lines.append("")
    return "\n".join(line for line in lines if line).strip()


def resume_to_json(
    entries: Sequence[ResumeEntry],
    *,
    project_descriptions: Optional[Mapping[str, ResumeProjectDescription]] = None,
) -> Dict[str, Any]:
    grouped = _group_by_section(entries)
    sections = []
    for section, items in grouped:
        rendered: List[Dict[str, Any]] = []
        for entry in items:
            payload = entry.to_dict()
            summary = _resolve_entry_summary(entry, project_descriptions)
            if summary:
                payload["summary"] = summary
            rendered.append(payload)
        sections.append({"name": section, "items": rendered})
    return {"generatedAt": datetime.now(timezone.utc).isoformat(), "sections": sections}


def resume_to_pdf(
    entries: Sequence[ResumeEntry],
    *,
    project_descriptions: Optional[Mapping[str, ResumeProjectDescription]] = None,
) -> bytes:
    markdown = resume_to_markdown(entries, project_descriptions=project_descriptions)
    return _markdown_to_pdf(markdown)

# export in differnt formats
def export_resume(
    entries: Sequence[ResumeEntry],
    *,
    fmt: str,
    destination: Optional[Path] = None,
    project_descriptions: Optional[Mapping[str, ResumeProjectDescription]] = None,
) -> bytes:
    fmt = fmt.lower()
    if fmt not in {"markdown", "json", "pdf"}:
        raise ValueError(f"Unsupported export format: {fmt}")
    if fmt == "markdown":
        data = resume_to_markdown(entries, project_descriptions=project_descriptions).encode("utf-8")
    elif fmt == "json":
        data = json.dumps(
            resume_to_json(entries, project_descriptions=project_descriptions),
            indent=2,
        ).encode("utf-8")
    else:
        data = resume_to_pdf(entries, project_descriptions=project_descriptions)
    if destination:
        destination.write_bytes(data)
        logger.info("Wrote resume export (%s) to %s", fmt, destination)
    return data


def _group_by_section(entries: Sequence[ResumeEntry]) -> List[Tuple[str, List[ResumeEntry]]]:
    buckets: Dict[str, List[ResumeEntry]] = defaultdict(list)
    for entry in entries:
        buckets[entry.section].append(entry)
    ordered_sections = list(DEFAULT_SECTIONS) + sorted(set(buckets.keys()) - set(DEFAULT_SECTIONS))
    grouped: List[Tuple[str, List[ResumeEntry]]] = []
    for section in ordered_sections:
        if section in buckets:
            grouped.append((section, buckets[section]))
    return grouped


def _format_period(metadata: Dict[str, Any]) -> str:
    start = metadata.get("start_date")
    end = metadata.get("end_date") or "Present"
    if not start:
        return f"({end})"
    return f"({start} – {end})"


def _resolve_entry_summary(
    entry: ResumeEntry,
    project_descriptions: Optional[Mapping[str, ResumeProjectDescription]],
) -> str:
    if project_descriptions and entry.project_ids:
        for project_id in entry.project_ids:
            desc = project_descriptions.get(project_id)
            if desc and desc.summary:
                return desc.summary
    return entry.summary or entry.body


def _resolve_summary_override(
    entry: ResumeEntry,
    resume_project_descriptions: Mapping[str, Optional[dict]],
) -> tuple[Optional[str], str]:
    if not entry.project_ids or not resume_project_descriptions:
        return None, "fallback"
    for project_id in entry.project_ids:
        desc = resume_project_descriptions.get(project_id) or {}
        summary = desc.get("summary") if isinstance(desc, dict) else None
        if summary:
            # custom wording beats generated wording
            source = "custom"
            metadata = desc.get("metadata") if isinstance(desc, dict) else None
            if isinstance(metadata, dict) and metadata.get("source") == "auto":
                source = "generated"
            return str(summary), source
    return None, "fallback"


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


# Canonical display names for languages (lowercase key → display name).
# Built from language_detection._EXTENSION_LANGUAGE values plus extras.
_LANG_DISPLAY: dict[str, str] = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "ruby": "Ruby", "go": "Go", "rust": "Rust",
    "c": "C", "c++": "C++", "c#": "C#", "swift": "Swift", "kotlin": "Kotlin",
    "objective-c": "Objective-C", "php": "PHP", "html": "HTML", "css": "CSS",
    "scss": "CSS", "markdown": "Markdown", "json": "JSON", "yaml": "YAML",
    "sql": "SQL", "shell": "Shell", "batchfile": "Batchfile",
    "powershell": "PowerShell", "scala": "Scala", "r": "R",
}


def _normalise_lang_name(name: str) -> str:
    """Return the canonical display name for a language, preserving case for unknowns."""
    return _LANG_DISPLAY.get(name.strip().lower(), name.strip())


def _normalise_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = value
    elif value is None:
        items = []
    else:
        items = [value]
    results: List[str] = []
    for item in items:
        if item is None:
            continue
        results.append(str(item))
    return results



def _pick_top_skill_names(skills: Any, limit: int = 2) -> List[str]:
    items: List[tuple[str, float]] = []
    if not isinstance(skills, list):
        skills = [] if skills is None else [skills]
    for skill in skills:
        if isinstance(skill, dict):
            name = str(skill.get("skill") or skill.get("name") or "")
            if not name:
                continue
            score = 0.0
            try:
                score = float(skill.get("confidence") or 0.0)
            except Exception:
                score = 0.0
            items.append((name, score))
            continue
        if skill is not None:
            items.append((str(skill), 0.0))
    items.sort(key=lambda item: (-item[1], item[0].lower()))
    return [_normalise_lang_name(name) for name, _ in items[:limit]]


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    results: List[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results


def _markdown_to_pdf(markdown: str) -> bytes:
    # Produce a tiny single-page PDF 
    lines = markdown.splitlines() or ["Resume"]
    pdf_lines = ["BT", "/F1 11 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        escaped = (
            line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        if index == 0:
            pdf_lines.append(f"({escaped}) Tj")
        else:
            pdf_lines.append("T*")
            pdf_lines.append(f"({escaped}) Tj")
    pdf_lines.append("ET")
    content = "\n".join(pdf_lines)
    stream = f"<< /Length {len(content)} >>\nstream\n{content}\nendstream"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        stream.encode("latin-1", "ignore"),
    ]
    buffer = bytearray()
    buffer.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer.extend(f"{idx} 0 obj\n".encode("latin-1"))
        buffer.extend(obj)
        buffer.extend(b"\nendobj\n")
    xref_offset = len(buffer)
    buffer.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for off in offsets:
        buffer.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    buffer.extend(b"trailer << /Size 6 /Root 1 0 R >>\n")
    buffer.extend(f"startxref\n{xref_offset}\n%%EOF".encode("latin-1"))
    return bytes(buffer)


__all__ = [
    "ResumeEntry",
    "ResumeProjectDescription",
    "ResumeRetrievalResult",
    "ensure_resume_schema",
    "describe_resume_schema",
    "insert_resume_entry",
    "get_resume_entry",
    "update_resume_entry",
    "upsert_resume_project_description",
    "get_resume_project_description",
    "list_resume_project_descriptions",
    "delete_resume_project_description",
    "query_resume_entries",
    "resolve_resume_projects",
    "resolve_resume_project_descriptions",
    "build_resume_project_summary",
    "generate_resume_project_descriptions",
    "build_resume_preview",
    "resume_to_markdown",
    "resume_to_json",
    "resume_to_pdf",
    "export_resume",
]
