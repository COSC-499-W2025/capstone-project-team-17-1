from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
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
    conn.commit()


def describe_resume_schema(conn: sqlite3.Connection) -> Dict[str, Any]:
    ensure_resume_schema(conn)
    tables = {}
    counts = {}
    for table in ("resume_entries", "resume_entry_links"):
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
    entry_id = entry_id or str(uuid4())
    section = section.lower()
    payload = json.dumps(metadata or {})
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
    _insert_links(conn, entry_id, projects or [], skills or [])
    conn.commit()
    return entry_id


def _insert_links(conn: sqlite3.Connection, entry_id: str, projects: Sequence[str], skills: Sequence[str]) -> None:
    for pid in projects:
        conn.execute(
            "INSERT INTO resume_entry_links(entry_id, link_type, link_value) VALUES (?, 'project', ?)",
            (entry_id, pid),
        )
    for skill in skills:
        conn.execute(
            "INSERT INTO resume_entry_links(entry_id, link_type, link_value) VALUES (?, 'skill', ?)",
            (entry_id, skill.lower()),
        )

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


def resolve_resume_projects(conn: sqlite3.Connection, entries: Iterable[ResumeEntry]) -> Dict[str, Optional[dict]]:
    ids = sorted({pid for entry in entries for pid in entry.project_ids})
    context: Dict[str, Optional[dict]] = {}
    for pid in ids:
        context[pid] = fetch_latest_snapshot(conn, pid)
    return context


def build_resume_preview(
    result: ResumeRetrievalResult,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in result.entries:
        fallback = entry.body.splitlines()[0] if entry.body.splitlines() else entry.body
        excerpt = (entry.summary or fallback or entry.title).strip()
        grouped[entry.section].append(
            {
                "id": entry.id,
                "title": entry.title,
                "excerpt": excerpt,
                "updated_at": entry.updated_at,
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
    last_updated = max((entry.updated for entry in result.entries if entry.updated), default=None)
    preview = {
        "sections": sections_payload,
        "warnings": result.warnings,
        "missingSections": result.missing_sections,
        "schema": result.schema_state,
        "projectContext": project_context,
        "lastUpdated": last_updated.isoformat() if last_updated else None,
    }
    return preview


def resume_to_markdown(entries: Sequence[ResumeEntry]) -> str:
    grouped = _group_by_section(entries)
    lines: List[str] = []
    for section, items in grouped:
        lines.append(f"## {section.title()}")
        for entry in items:
            period = _format_period(entry.metadata)
            summary = entry.summary or entry.body
            lines.append(f"- **{entry.title}** {period} — {summary.strip()}")
            if entry.skills:
                lines.append(f"  - Skills: {', '.join(entry.skills)}")
        lines.append("")
    return "\n".join(line for line in lines if line).strip()


def resume_to_json(entries: Sequence[ResumeEntry]) -> Dict[str, Any]:
    grouped = _group_by_section(entries)
    sections = []
    for section, items in grouped:
        sections.append({"name": section, "items": [entry.to_dict() for entry in items]})
    return {"generatedAt": datetime.now(timezone.utc).isoformat(), "sections": sections}


def resume_to_pdf(entries: Sequence[ResumeEntry]) -> bytes:
    markdown = resume_to_markdown(entries)
    return _markdown_to_pdf(markdown)

# export in differnt formats
def export_resume(entries: Sequence[ResumeEntry], *, fmt: str, destination: Optional[Path] = None) -> bytes:
    fmt = fmt.lower()
    if fmt not in {"markdown", "json", "pdf"}:
        raise ValueError(f"Unsupported export format: {fmt}")
    if fmt == "markdown":
        data = resume_to_markdown(entries).encode("utf-8")
    elif fmt == "json":
        data = json.dumps(resume_to_json(entries), indent=2).encode("utf-8")
    else:
        data = resume_to_pdf(entries)
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
    "ResumeRetrievalResult",
    "ensure_resume_schema",
    "describe_resume_schema",
    "insert_resume_entry",
    "query_resume_entries",
    "resolve_resume_projects",
    "build_resume_preview",
    "resume_to_markdown",
    "resume_to_json",
    "resume_to_pdf",
    "export_resume",
]
