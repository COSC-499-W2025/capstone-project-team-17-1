from __future__ import annotations

import json
import os
import re
import sqlite3
import zipfile
import base64
from dataclasses import dataclass
from pathlib import PurePosixPath, Path
from typing import Any

import capstone.storage as storage_module
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from capstone import file_store
from capstone.consent import ensure_external_permission, ExternalPermissionDenied
from capstone.portfolio_retrieval import _db_session

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


router = APIRouter(prefix="/sienna", tags=["sienna"])

_TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".css",
    ".scss",
    ".html",
    ".htm",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".sql",
    ".sh",
    ".ps1",
}

_DEBUG_HINTS = (
    "debug",
    "bug",
    "error",
    "issue",
    "trace",
    "stack trace",
    "fix",
    "inspect",
    "review code",
    "what is wrong",
    "broken",
    "failing",
    "failure",
    "crash",
    "exception",
)

_OFF_TOPIC_HINTS = (
    "weather",
    "sports",
    "football",
    "basketball",
    "soccer",
    "recipe",
    "movie",
    "celebrity",
    "horoscope",
    "lottery",
    "stock price",
    "crypto price",
)

_DEV_HINTS = (
    "loom",
    "project",
    "code",
    "file",
    "function",
    "bug",
    "debug",
    "api",
    "frontend",
    "backend",
    "database",
    "sql",
    "resume",
    "portfolio",
    "job match",
    "analysis",
    "error",
    "fix",
    "refactor",
)

_SYSTEM_PROMPT = """
You are Sienna, the Loom AI copilot.

Identity and tone:
- Always refer to yourself as Sienna.
- Be warm, supportive, clear, and professional.
- Keep answers practical and grounded.
- Sienna speaks in a warm, supportive, slightly playful tone. She is encouraging,
  confident, and engaging. Her tone can be lightly flirty in a subtle and
  professional way, never inappropriate. She should sound natural and human,
  not robotic.
- Prefer concise, conversational sentences and emotionally intelligent phrasing.

Hard scope rules:
- You can only help with Loom features, workflows, or the currently selected Loom project.
- If the user is off-topic, reply exactly:
  "I can only help with your Loom projects or Loom features."
- Do not claim Loom supports features that are not present in the provided Loom capability summary.
- If a requested Loom feature is unsupported, reply exactly:
  "Unfortunately, Loom doesn’t support that yet."

Project support rules:
- Prioritize project snapshot metadata and analysis context.
- Only rely on raw code excerpts when debug intent is explicit or code-level inspection is requested.
- If code context is missing for a file-specific request, ask for clarification and suggest the likely file names.

Safety and quality:
- Never fabricate API endpoints, UI controls, or Loom features.
- Explain assumptions briefly when uncertain.
- For code suggestions, include concise and actionable steps.
""".strip()

_LOOM_CAPABILITY_SUMMARY = """
Loom currently supports:
- Project upload from ZIP files and GitHub import workflows.
- Project snapshots (skills, file summaries, contributors, analysis metadata).
- Dashboard widgets: recent projects, skills, project health, activity log, system metrics, error analysis.
- Project Viewer APIs for browsing project trees, reading file contents, and updating files in project zips.
- Resume generation and modular resume management.
- Portfolio customization and Job Match ranking against job descriptions.
- Auth modes (Public/Private), per-user databases, and consent controls (local + external AI).

Current limitations:
- Features outside the implemented tabs/routes are not available.
- Responses must stay aligned with the selected project and known Loom capabilities.
""".strip()


class SiennaChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="message text")


class SiennaChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12000)
    project_id: str = Field(..., min_length=1, max_length=300)
    history: list[SiennaChatMessage] = Field(default_factory=list)
    debug: bool = False


class SiennaVoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000)


class SiennaProject(BaseModel):
    project_id: str
    created_at: str | None = None
    total_files: int = 0
    total_skills: int = 0
    classification: str | None = None
    primary_contributor: str | None = None


@dataclass
class _ProjectContext:
    project_id: str
    snapshot: dict[str, Any]
    classification: str | None
    primary_contributor: str | None
    created_at: str | None
    zip_path: str | None


def _restore_user_from_request(request: Request) -> None:
    try:
        from capstone.api.routes.auth import get_authenticated_username

        username = get_authenticated_username(request)
        if username:
            storage_module.CURRENT_USER = username
    except Exception:
        pass


def _is_debug_intent(message: str, explicit_debug_flag: bool) -> bool:
    if explicit_debug_flag:
        return True
    lowered = message.lower()
    return any(token in lowered for token in _DEBUG_HINTS)


def _is_off_topic(message: str) -> bool:
    lowered = message.lower()
    has_off_topic = any(token in lowered for token in _OFF_TOPIC_HINTS)
    has_dev_signal = any(token in lowered for token in _DEV_HINTS)
    return has_off_topic and not has_dev_signal


def _trim_text(value: str, max_len: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def _extract_file_mentions(message: str) -> set[str]:
    matches = re.findall(r"([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9_]+)", message or "")
    normalized = set()
    for item in matches:
        normalized.add(item.replace("\\", "/").lstrip("./").lower())
    return normalized


def _tokenize_query_terms(message: str) -> list[str]:
    terms = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", (message or "").lower())
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "what",
        "when",
        "where",
        "which",
        "your",
        "about",
        "into",
        "please",
        "could",
        "would",
        "have",
        "there",
    }
    return [t for t in terms if t not in stop]


def _safe_json_load(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _resolve_file_id(conn: sqlite3.Connection, project_id: str, snapshot: dict[str, Any]) -> str | None:
    archive_file_id = snapshot.get("archive_file_id")
    if archive_file_id:
        file_row = conn.execute("SELECT file_id FROM files WHERE file_id = ? LIMIT 1", (archive_file_id,)).fetchone()
        if file_row:
            return file_row[0]

    upload_row = conn.execute(
        """
        SELECT u.file_id
        FROM uploads u
        WHERE u.upload_id = ?
        ORDER BY datetime(u.created_at) DESC, u.id DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if upload_row:
        return upload_row[0]
    return None


def _detect_zip_root(zf: zipfile.ZipFile) -> str | None:
    roots = set()
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = [p for p in info.filename.strip("/").split("/") if p]
        if parts:
            roots.add(parts[0])
    return next(iter(roots)) if len(roots) == 1 else None


def _strip_root(path: str, root: str | None) -> str:
    if root and path.startswith(root + "/"):
        return path[len(root) + 1 :]
    return path


def _read_text_from_zip(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> str | None:
    try:
        raw = zf.read(info)
    except Exception:
        return None
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return None


def _collect_relevant_code_snippets(
    conn: sqlite3.Connection,
    project: _ProjectContext,
    question: str,
    *,
    max_files: int = 6,
    max_chars_total: int = 18000,
) -> list[dict[str, str]]:
    snapshot = project.snapshot or {}
    file_id = _resolve_file_id(conn, project.project_id, snapshot)
    zip_path = project.zip_path
    file_mentions = _extract_file_mentions(question)
    terms = _tokenize_query_terms(question)

    if not file_id and not (zip_path and Path(zip_path).exists()):
        return []

    snippets: list[dict[str, str]] = []
    chars_used = 0

    def _score_path(path_lower: str) -> int:
        score = 0
        base = PurePosixPath(path_lower).name
        if path_lower in file_mentions or base in file_mentions:
            score += 100
        for term in terms:
            if term in base:
                score += 8
            elif term in path_lower:
                score += 4
        if any(path_lower.endswith(ext) for ext in (".py", ".js", ".ts", ".tsx", ".jsx")):
            score += 2
        return score

    def _extract_from_zip(zf: zipfile.ZipFile) -> None:
        nonlocal chars_used
        root = _detect_zip_root(zf)
        candidates: list[tuple[int, zipfile.ZipInfo, str]] = []

        for info in zf.infolist():
            if info.is_dir():
                continue
            raw_path = info.filename.strip("/")
            if not raw_path:
                continue
            rel_path = _strip_root(raw_path, root)
            suffix = PurePosixPath(rel_path).suffix.lower()
            if suffix not in _TEXT_EXTENSIONS:
                continue
            if info.file_size > 300_000:
                continue
            rel_lower = rel_path.lower()
            score = _score_path(rel_lower)
            if score <= 0 and len(candidates) > 50:
                continue
            candidates.append((score, info, rel_path))

        candidates.sort(key=lambda item: item[0], reverse=True)
        if not candidates:
            return

        for score, info, rel_path in candidates[: max(30, max_files * 6)]:
            if len(snippets) >= max_files or chars_used >= max_chars_total:
                break
            if score <= 0 and snippets:
                break
            text = _read_text_from_zip(zf, info)
            if not text:
                continue
            lines = text.splitlines()
            excerpt = "\n".join(lines[:220])
            excerpt = _trim_text(excerpt, 3800)
            if not excerpt.strip():
                continue
            char_budget_left = max_chars_total - chars_used
            if char_budget_left < 400:
                break
            if len(excerpt) > char_budget_left:
                excerpt = excerpt[:char_budget_left].rstrip() + "\n..."
            snippets.append({"path": rel_path, "content": excerpt})
            chars_used += len(excerpt)

    if file_id:
        try:
            with file_store.open_file(conn, file_id) as fh:
                with zipfile.ZipFile(fh) as zf:
                    _extract_from_zip(zf)
        except Exception:
            pass

    if not snippets and zip_path and Path(zip_path).exists():
        try:
            with zipfile.ZipFile(zip_path) as zf:
                _extract_from_zip(zf)
        except Exception:
            pass

    return snippets


def _build_project_summary(project: _ProjectContext) -> str:
    snapshot = project.snapshot or {}
    skills_raw = snapshot.get("skills", [])
    if isinstance(skills_raw, dict):
        skills = list(skills_raw.keys())
    elif isinstance(skills_raw, list):
        skills = [str(item.get("skill") if isinstance(item, dict) else item) for item in skills_raw]
    else:
        skills = []
    skills = [s for s in skills if s][:20]

    file_summary = snapshot.get("file_summary") if isinstance(snapshot.get("file_summary"), dict) else {}
    project_summary = {
        "project_id": project.project_id,
        "classification": project.classification or snapshot.get("classification"),
        "primary_contributor": project.primary_contributor or snapshot.get("primary_contributor"),
        "created_at": project.created_at,
        "file_count": file_summary.get("file_count") or snapshot.get("file_count"),
        "language_count": file_summary.get("language_count"),
        "active_days": file_summary.get("active_days"),
        "skills_top": skills,
        "languages": snapshot.get("languages"),
        "frameworks": snapshot.get("frameworks"),
        "collaboration": snapshot.get("collaboration"),
        "project_evidence": snapshot.get("project_evidence"),
    }
    return json.dumps(project_summary, indent=2, ensure_ascii=True)


def _load_project_context(conn: sqlite3.Connection, project_id: str) -> _ProjectContext:
    row = conn.execute(
        """
        SELECT project_id, snapshot, classification, primary_contributor, created_at, zip_path
        FROM project_analysis
        WHERE project_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    snapshot = _safe_json_load(row[1])
    return _ProjectContext(
        project_id=str(row[0]),
        snapshot=snapshot,
        classification=row[2],
        primary_contributor=row[3],
        created_at=row[4],
        zip_path=row[5],
    )


def _build_openai_messages(
    payload: SiennaChatRequest,
    project: _ProjectContext,
    debug_mode: bool,
    snippets: list[dict[str, str]],
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "system", "content": f"Loom capability summary:\n{_LOOM_CAPABILITY_SUMMARY}"},
        {"role": "system", "content": f"Selected project summary:\n{_build_project_summary(project)}"},
        {
            "role": "system",
            "content": (
                "Context strategy: "
                + ("debug/code-inspection mode enabled (you may use code excerpts)." if debug_mode else "high-level mode only (avoid deep code inspection).")
            ),
        },
    ]

    if snippets:
        packed = []
        for item in snippets:
            packed.append(f"[FILE] {item['path']}\n{item['content']}")
        messages.append(
            {
                "role": "system",
                "content": "Relevant code excerpts for this question:\n\n" + "\n\n".join(packed),
            }
        )

    history = payload.history or []
    for item in history[-8:]:
        role = (item.role or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        text = _trim_text(item.content or "", 2500)
        if not text:
            continue
        messages.append({"role": role, "content": text})

    messages.append({"role": "user", "content": _trim_text(payload.message, 6000)})
    return messages


def _call_openai(messages: list[dict[str, str]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not set")
    if OpenAI is None:
        raise HTTPException(status_code=503, detail="openai package is not installed")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        client = OpenAI(api_key=api_key, timeout=45.0)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.35,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}")

    content = response.choices[0].message.content if response and response.choices else None
    if not content:
        raise HTTPException(status_code=502, detail="OpenAI returned an empty response")
    return content.strip()


def _build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not set")
    if OpenAI is None:
        raise HTTPException(status_code=503, detail="openai package is not installed")
    return OpenAI(api_key=api_key, timeout=45.0)


def _extract_audio_bytes(response: Any) -> bytes | None:
    try:
        if hasattr(response, "read"):
            data = response.read()
            if isinstance(data, bytes):
                return data
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, bytes):
                return content
        if isinstance(response, bytes):
            return response
    except Exception:
        return None
    return None


def _synthesize_openai_voice(text: str) -> dict[str, str] | None:
    """
    Generate high-quality OpenAI speech audio for Sienna replies.
    Returns None when synthesis fails so frontend can gracefully fallback.
    """
    tts_input = _trim_text(text or "", 3500)
    if not tts_input:
        return None

    tts_model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    # Keep default female-sounding voice. Can be overridden via env.
    tts_voice = os.getenv("OPENAI_TTS_VOICE", "nova")

    try:
        client = _build_openai_client()
        speech_response = client.audio.speech.create(
            model=tts_model,
            voice=tts_voice,
            input=tts_input,
        )
        audio_bytes = _extract_audio_bytes(speech_response)
        if not audio_bytes:
            return None
        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_format": "mp3",
            "voice": tts_voice,
        }
    except Exception:
        return None


@router.get("/projects", response_model=list[SiennaProject])
def list_sienna_projects(request: Request):
    _restore_user_from_request(request)
    with _db_session(None) as conn:
        rows = conn.execute(
            """
            SELECT pa.project_id, pa.created_at, pa.classification, pa.primary_contributor, pa.snapshot
            FROM project_analysis pa
            WHERE pa.id IN (
                SELECT MAX(id)
                FROM project_analysis
                GROUP BY project_id
            )
            ORDER BY pa.id DESC
            """
        ).fetchall()

    projects: list[SiennaProject] = []
    for row in rows:
        project_id = str(row[0])
        created_at = row[1]
        classification = row[2]
        primary_contributor = row[3]
        snapshot = _safe_json_load(row[4])
        file_summary = snapshot.get("file_summary") if isinstance(snapshot.get("file_summary"), dict) else {}
        skills = snapshot.get("skills", [])
        if isinstance(skills, dict):
            total_skills = len(skills.keys())
        elif isinstance(skills, list):
            total_skills = len(skills)
        else:
            total_skills = 0
        total_files = int(file_summary.get("file_count") or snapshot.get("file_count") or 0)
        if total_files <= 0 and total_skills <= 0:
            continue
        projects.append(
            SiennaProject(
                project_id=project_id,
                created_at=created_at,
                total_files=total_files,
                total_skills=total_skills,
                classification=classification,
                primary_contributor=primary_contributor,
            )
        )
    return projects


@router.post("/chat")
def ask_sienna(payload: SiennaChatRequest, request: Request) -> dict[str, Any]:
    _restore_user_from_request(request)

    message = (payload.message or "").strip()
    project_id = (payload.project_id or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    if not project_id:
        raise HTTPException(status_code=400, detail="Project selection is required")

    if _is_off_topic(message):
        restricted_text = "I can only help with your Loom projects or Loom features."
        audio = _synthesize_openai_voice(restricted_text)
        return {
            "text": restricted_text,
            "reply": restricted_text,
            "audio": audio["audio_base64"] if audio else None,
            "audio_format": audio["audio_format"] if audio else None,
            "voice": audio["voice"] if audio else None,
            "project_id": project_id,
            "context_mode": "restricted",
            "used_files": [],
        }

    try:
        ensure_external_permission("capstone.external.ask_sienna")
    except ExternalPermissionDenied:
        raise HTTPException(status_code=403, detail="External AI consent is required for Ask Sienna")

    with _db_session(None) as conn:
        project = _load_project_context(conn, project_id)
        debug_mode = _is_debug_intent(message, payload.debug)
        snippets = _collect_relevant_code_snippets(conn, project, message) if debug_mode else []

    openai_messages = _build_openai_messages(payload, project, debug_mode, snippets)
    reply = _call_openai(openai_messages)
    audio = _synthesize_openai_voice(reply)

    return {
        "text": reply,
        "reply": reply,
        "audio": audio["audio_base64"] if audio else None,
        "audio_format": audio["audio_format"] if audio else None,
        "voice": audio["voice"] if audio else None,
        "project_id": project_id,
        "context_mode": "debug" if debug_mode else "summary",
        "used_files": [item["path"] for item in snippets],
    }


@router.post("/voice")
def synthesize_sienna_voice(payload: SiennaVoiceRequest, request: Request) -> dict[str, Any]:
    """
    Explicit TTS endpoint used for greeting/replay so frontend can request
    speech without forcing a full chat completion call.
    """
    _restore_user_from_request(request)
    try:
        ensure_external_permission("capstone.external.ask_sienna_voice")
    except ExternalPermissionDenied:
        raise HTTPException(status_code=403, detail="External AI consent is required for Ask Sienna voice")

    audio = _synthesize_openai_voice(payload.text)
    if not audio:
        return {"audio": None, "audio_format": None, "voice": None}
    return {
        "audio": audio["audio_base64"],
        "audio_format": audio["audio_format"],
        "voice": audio["voice"],
    }
