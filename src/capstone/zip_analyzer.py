"""Zip analysis pipeline orchestrator."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from time import perf_counter
from typing import Iterable, List, Tuple, Dict
from zipfile import BadZipFile, ZipFile

from .collaboration import analyze_git_logs
from .collaboration_analysis import build_collaboration_analysis, to_compact_collaboration
from .git_analysis import parse_git_log_stream
from .config import Preferences, update_preferences
from .language_detection import (
    classify_activity,
    detect_frameworks_from_package_json,
    detect_frameworks_from_python_requirements,
    detect_language,
)
from .logging_utils import get_logger
from .metrics import FileMetric, MetricSummary, compute_metrics
from .modes import ModeResolution
from .skills import SkillObservation, build_skill_timeline, compute_skill_scores
from .storage import open_db, close_db, store_analysis_snapshot, upsert_contributor, link_user_to_project, store_contributor_stats
import sqlite3
from . import file_store


logger = get_logger(__name__)


class InvalidArchiveError(ValueError):
    """Raised when the provided file is not a valid zip archive."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.payload = {"error": "InvalidInput", "detail": detail}


class ZipAnalyzer:
    """Analyse zip archives to produce JSONL metadata and summaries."""

    def __init__(self) -> None:
        self._logger = logger

    @staticmethod
    def _is_git_log_path(path_lower: str) -> bool:
        return (
            ".git/logs/git_log" in path_lower
            or path_lower.endswith("git_log")
            or path_lower.endswith("git_log.txt")
        )

    @staticmethod
    def _decode_utf16_git_log(raw: bytes) -> str | None:
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                decoded = raw.decode(encoding)
            except UnicodeDecodeError:
                continue
            if "commit:" in decoded or "\x00" not in decoded:
                return decoded
        return None

    def _decode_content_text(
        self,
        *,
        raw: bytes,
        path: str,
        is_git_log: bool,
        warnings: List[dict[str, str]],
    ) -> str:
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            if is_git_log:
                decoded_utf16 = self._decode_utf16_git_log(raw)
                if decoded_utf16 is not None:
                    return decoded_utf16
            warnings.append(
                {
                    "path": path,
                    "error": "NonUtf8",
                    "detail": "File contains non-UTF-8 bytes",
                }
            )
            return raw.decode("utf-8", errors="ignore")
        if is_git_log and "\x00" in decoded:
            decoded_utf16 = self._decode_utf16_git_log(raw)
            if decoded_utf16 is not None:
                return decoded_utf16
        return decoded

    def analyze(
        self,
        zip_path: Path,
        metadata_path: Path,
        summary_path: Path,
        mode: ModeResolution,
        preferences: Preferences,
        project_id: str | None = None,
        db_dir: Path | None = None,
        conn: sqlite3.Connection | None = None,
        skip_contributor_storage: bool = False,
    ) -> dict[str, object]:
        start = perf_counter()
        zip_path = zip_path.expanduser().resolve()
        if zip_path.suffix.lower() != ".zip":
            detail = "Expected a .zip archive"
            self._logger.error("Invalid input format for %s", zip_path)
            raise InvalidArchiveError(detail)

        if conn is None:
            conn = open_db(db_dir)
        try:
            stored = file_store.ensure_file(
                conn,
                zip_path,
                original_name=zip_path.name,
                source="zip_analyzer",
                upload_id=project_id,
            )
            conn.commit()

        except sqlite3.OperationalError as exc:
            if "readonly" not in str(exc).lower():
                raise
            # Retry once with a fresh connection in case the handle is stale/readonly.
            try:
                close_db()
            except Exception:
                pass
            conn = open_db(db_dir)
            stored = file_store.ensure_file(
                conn,
                zip_path,
                original_name=zip_path.name,
                source="zip_analyzer",
                upload_id=project_id,
            )
        canonical_zip_path = Path(stored["path"])

        try:
            with ZipFile(canonical_zip_path) as archive:
                return self._analyze_archive(
                    archive,
                    canonical_zip_path,
                    metadata_path,
                    summary_path,
                    mode,
                    preferences,
                    start,
                    project_id,
                    db_dir,
                    conn,
                    stored,
                    skip_contributor_storage=skip_contributor_storage,
                )
        except BadZipFile as exc:
            detail = f"Corrupted zip archive ({exc})"
            self._logger.error("Failed to read archive %s", zip_path, exc_info=True)
            raise InvalidArchiveError(detail)

    def _analyze_archive(
        self,
        archive: ZipFile,
        zip_path: Path,
        metadata_path: Path,
        summary_path: Path,
        mode: ModeResolution,
        preferences: Preferences,
        start: float,
        project_id: str | None,
        db_dir: Path | None,
        conn,
        stored_file: dict,
        skip_contributor_storage: bool = False,
    ) -> dict[str, object]:
        metadata_records: List[dict[str, object]] = []
        metrics_inputs: List[FileMetric] = []
        language_counter: Counter[str] = Counter()
        frameworks = set()
        git_logs: list[str] = []
        skill_events: List[Tuple[str, str, datetime, float]] = []
        # Collect non-fatal issues 
        warnings: List[dict[str, str]] = []
        seen_paths: set[str] = set()
        supported_extensions = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".rb",
            ".go",
            ".rs",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".swift",
            ".kt",
            ".m",
            ".php",
            ".html",
            ".css",
            ".scss",
            ".md",
            ".json",
            ".yml",
            ".yaml",
            ".sql",
            ".sh",
            ".bat",
            ".ps1",
            ".txt",
            ".rst",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".pdf",
            ".csv",
        }

        for info in archive.infolist():
            if info.is_dir():
                continue
            seen_paths.add(info.filename.lower())
            try:
                raw = archive.read(info)
            except BadZipFile as exc:
                warnings.append(
                    {
                        "path": info.filename,
                        "error": "CorruptedFile",
                        "detail": str(exc),
                    }
                )
                self._logger.error("Failed to read archive member %s", info.filename, exc_info=True)
                continue

            record = self._build_record(info, mode)
            metadata_records.append(record)

            if record.get("language"):
                language_counter[record["language"]] += 1
                skill_events.append((record["language"], "language", datetime.fromisoformat(record["modified"]), 1.0))

            metrics_inputs.append(
                FileMetric(
                    path=record["path"],
                    size=record["size"],
                    modified=datetime.fromisoformat(record["modified"]),
                    activity=record["activity"],
                )
            )

            path_lower = info.filename.lower()
            is_git_log = self._is_git_log_path(path_lower)
            # Lightweight content validation for common error
            suffix = PurePosixPath(path_lower).suffix
            if info.file_size == 0:
                warnings.append(
                    {
                        "path": info.filename,
                        "error": "EmptyFile",
                        "detail": "File is empty (0 bytes)",
                    }
                )
            if suffix and suffix not in supported_extensions:
                warnings.append(
                    {
                        "path": info.filename,
                        "error": "UnsupportedExtension",
                        "detail": f"Unsupported file extension: {suffix}",
                    }
                )
            content_text = self._decode_content_text(
                raw=raw,
                path=info.filename,
                is_git_log=is_git_log,
                warnings=warnings,
            )
            if path_lower.endswith(".json"):
                try:
                    json.loads(content_text)
                except json.JSONDecodeError as exc:
                    warnings.append(
                        {
                            "path": info.filename,
                            "error": "InvalidFormat",
                            "detail": f"Invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}",
                        }
                    )
            if path_lower.endswith("package.json"):
                detected = detect_frameworks_from_package_json(content_text)
                frameworks.update(detected)
                for fw in detected:
                    skill_events.append((fw, "framework", datetime.fromisoformat(record["modified"]), 1.0))
            elif path_lower.endswith("requirements.txt"):
                detected = detect_frameworks_from_python_requirements(content_text.splitlines())
                frameworks.update(detected)
                for fw in detected:
                    skill_events.append((fw, "framework", datetime.fromisoformat(record["modified"]), 1.0))
            elif is_git_log:
                git_logs.extend(content_text.splitlines())
            tool_skills = self._detect_tool_skills(path_lower)
            if tool_skills:
                ts = datetime.fromisoformat(record["modified"])
                for skill_name, category in tool_skills:
                    skill_events.append((skill_name, category, ts, 1.0))

        # Surface missing key files 
        missing_required = [
            name
            for name in ("README.md", "package.json", "requirements.txt")
            if not any(path.endswith(f"/{name.lower()}") or path == name.lower() for path in seen_paths)
        ]
        if missing_required:
            warnings.append(
                {
                    "path": str(zip_path),
                    "error": "MissingKeyFiles",
                    "detail": f"Missing required file(s): {', '.join(missing_required)}",
                }
            )

        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("w", encoding="utf-8") as fh:
            for record in metadata_records:
                fh.write(json.dumps(record))
                fh.write("\n")

        metric_summary = compute_metrics(metrics_inputs)
        collaboration = self._summarize_collaboration(git_logs)
        # Build author→email map from the raw git log lines while they are still available.
        # to_compact_collaboration drops email, so we capture it here for upsert_contributor below.
        author_email_map, noreply_only_authors = _build_author_email_map(git_logs)
        duration = perf_counter() - start

        skill_observations = [
            SkillObservation(skill=lang, weight=count, category="language")
            for lang, count in language_counter.items()
        ]
        for framework in frameworks:
            skill_observations.append(SkillObservation(skill=framework, weight=1.0, category="framework"))
        skills = [score.__dict__ for score in compute_skill_scores(skill_observations, min_confidence=0.05)]
        skill_timeline = build_skill_timeline(skill_events)
        top_skills_by_year = _compute_top_skills_by_year(skill_timeline, top_n=5)

        summary = {
            "archive": str(zip_path),
            "archive_file_id": stored_file["file_id"],
            "archive_hash": stored_file["hash"],
            "archive_dedup": stored_file["dedup"],
            "requested_mode": mode.requested,
            "resolved_mode": mode.resolved,
            "mode_reason": mode.reason,
            "local_mode_label": preferences.labels.get("local_mode", "Local Analysis Mode"),
            "file_summary": asdict(metric_summary),
            "languages": dict(language_counter),
            "frameworks": sorted(frameworks),
            "collaboration": collaboration,
            "metadata_output": str(metadata_path),
            "scan_duration_seconds": round(duration, 4),
            "warnings": warnings,
            "warning_count": len(warnings),
            "skills": skills,
            "skill_timeline": {
                "generated_at": datetime.utcnow().isoformat(),
                "skills": list(skill_timeline.values()),
            },
            "top_skills_by_year": top_skills_by_year,
        }

        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

        update_preferences(
            last_opened_path=str(zip_path.parent),
            analysis_mode=mode.resolved,
        )

        project_id = project_id or zip_path.stem
        classification = collaboration.get("classification", "unknown")
        primary_contributor = collaboration.get("primary_contributor")
        conn = open_db(db_dir)
        store_analysis_snapshot(
            conn,
            project_id=project_id,
            classification=classification,
            primary_contributor=primary_contributor,
            snapshot=summary,
            zip_path=str(stored_file.get("path") or zip_path),
        )
        self._logger.info("Stored zip analysis snapshot for %s", project_id)

        # store zip contributors in users and user_projects
        # (skipped for GitHub imports — sync_contributor_stats handles this via the API)
        if not skip_contributor_storage:
            contrib_raw = (
                collaboration.get("contributors (commits, PRs, issues, reviews)")
                or collaboration.get("contributors (commits, line changes, reviews)")
                or {}
            )
            if isinstance(contrib_raw, dict):
                for cname, cdata in contrib_raw.items():
                    cname = str(cname).strip()
                    if not cname or cname.lower().endswith("[bot]"):
                        continue
                    # Skip authors who only ever committed with noreply/bot emails
                    if cname in noreply_only_authors:
                        continue
                    uid = upsert_contributor(conn, cname, email=author_email_map.get(cname))
                    link_user_to_project(conn, uid, project_id, contributor_name=cname)
                    commits, _lines, reviews = _parse_contrib_data(cdata)
                    score = commits * 1.0 + reviews * 0.5
                    store_contributor_stats(
                        conn,
                        project_id=project_id,
                        contributor=cname,
                        user_id=uid,
                        commits=commits,
                        reviews=reviews,
                        score=score,
                        source="zip",
                    )
                self._logger.info("Stored %d zip contributors for project %s", len(contrib_raw), project_id)

        return summary

    def _build_record(self, info, mode: ModeResolution) -> dict[str, object]:
        modified = datetime(*info.date_time).isoformat()
        language = detect_language(info.filename)
        activity = classify_activity(info.filename)
        unique_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{info.filename}:{info.file_size}:{modified}").hex
        record = {
            "id": unique_id,
            "path": info.filename,
            "size": info.file_size,
            "compressed_size": info.compress_size,
            "modified": modified,
            "language": language,
            "activity": activity,
            "analysis_mode": mode.resolved,
        }
        return record

    def _detect_tool_skills(self, path_lower: str) -> List[Tuple[str, str]]:
        """
        Lightweight taxonomy for tools/domains inferred from filenames.
        Expands the skill set beyond languages/frameworks when obvious markers exist.
        """
        skills: List[Tuple[str, str]] = []
        if "dockerfile" in path_lower:
            skills.append(("docker", "tool"))
        if path_lower.endswith((".sh", ".bash")) or "/scripts/" in path_lower:
            skills.append(("bash", "tool"))
        if path_lower.endswith("makefile"):
            skills.append(("make", "tool"))
        if path_lower.endswith(".sql"):
            skills.append(("sql", "language"))
        if path_lower.endswith(".ipynb"):
            skills.append(("jupyter", "tool"))
        if "terraform" in path_lower:
            skills.append(("terraform", "tool"))
        return skills

    def _summarize_collaboration(self, git_logs: Iterable[str]) -> dict[str, object]:
        logs = list(git_logs)
        if not logs:
            return {"classification": "unknown", "contributors (commits, line changes, reviews)": {}, "primary_contributor": None}

        # Prefer rich analysis when git log contains numstat-style entries.
        try:
            if any(line.startswith("commit:") for line in logs):
                entries = parse_git_log_stream("\n".join(logs))
                analysis = build_collaboration_analysis(entries)
                result = to_compact_collaboration(analysis)
                # Extract first/last commit dates directly from raw log lines (format: commit:SHA|author|email|TIMESTAMP|subject)
                timestamps: list[int] = []
                for line in logs:
                    if line.startswith("commit:"):
                        try:
                            parts = line.split(":", 1)[1].split("|")
                            if len(parts) >= 4:
                                ts = int(parts[3])
                                if ts > 0:
                                    timestamps.append(ts)
                        except (ValueError, IndexError):
                            pass
                if timestamps:
                    result["first_commit_date"] = datetime.utcfromtimestamp(min(timestamps)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    result["last_commit_date"] = datetime.utcfromtimestamp(max(timestamps)).strftime("%Y-%m-%dT%H:%M:%SZ")
                return result
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._logger.warning("Failed rich collaboration parse; falling back to basic: %s", exc)

        basic = analyze_git_logs(logs)
        return {
            "classification": basic.classification,
            "contributors (commits, line changes, reviews)": {
                name: [count, 0, 0] for name, count in basic.contributors.items()
            },
            "primary_contributor": basic.primary_contributor,
            "contribution_compute": "weightedScore = commits*1.0 + line_changes*0.0 + reviews*0.5",
        }


def _parse_contrib_data(value: object) -> tuple[int, int, int]:
    """Parse a contrib_raw value into (commits, lines, reviews).

    Handles both list/tuple [c, l, r] and string "[c, l, r]" from
    to_compact_collaboration, as well as bare integers (commit count only).
    """
    if isinstance(value, (list, tuple)):
        data = list(value)
    elif isinstance(value, str):
        try:
            data = [int(x.strip()) for x in value.strip("[] ").split(",")]
        except (ValueError, AttributeError):
            data = []
    elif isinstance(value, (int, float)):
        data = [int(value)]
    else:
        data = []
    commits = int(data[0]) if len(data) > 0 else 0
    lines = int(data[1]) if len(data) > 1 else 0
    reviews = int(data[2]) if len(data) > 2 else 0
    return commits, lines, reviews


def _build_author_email_map(git_log_lines: list[str]) -> tuple[dict[str, str], set[str]]:
    """Return ({author_name: real_email}, noreply_only_authors) from raw git log lines.

    noreply_only_authors contains authors whose EVERY commit used a noreply/bot email
    (i.e. they have no real email entry). These are typically automated accounts.
    First real-email occurrence per author wins.
    """
    _NOREPLY_SUFFIXES = ("@users.noreply.github.com", "@noreply.github.com")
    result: dict[str, str] = {}
    seen_noreply: set[str] = set()   # authors seen with noreply email

    for line in git_log_lines:
        if not line.startswith("commit:"):
            continue
        parts = line[len("commit:"):].split("|")
        if len(parts) < 3:
            continue
        author = parts[1].strip()
        email = parts[2].strip()
        if not author or author.lower().endswith("[bot]") or not email:
            continue
        lowered = email.lower()
        if lowered == "noreply@github.com" or any(lowered.endswith(s) for s in _NOREPLY_SUFFIXES):
            seen_noreply.add(author)
            continue
        if author not in result:
            result[author] = email

    # Authors only ever seen with noreply emails and never with a real email
    noreply_only = seen_noreply - result.keys()
    return result, noreply_only


def _compute_top_skills_by_year(skill_timeline: Dict[str, Dict[str, object]], top_n: int = 5) -> Dict[str, List[Dict[str, float]]]:
    """
    Reduce skill_timeline into a per-year top-N structure for easy rendering/export.
    """
    years: Dict[str, Dict[str, float]] = {}
    for entry in skill_timeline.values():
        for year, weight in (entry.get("year_counts") or {}).items():
            bucket = years.setdefault(year, {})
            bucket[entry["skill"]] = bucket.get(entry["skill"], 0.0) + float(weight or 0.0)
    payload: Dict[str, List[Dict[str, float]]] = {}
    for year, data in years.items():
        ranked = sorted(data.items(), key=lambda item: (-item[1], item[0]))
        payload[year] = [{"skill": skill, "weight": weight} for skill, weight in ranked[: max(1, top_n)]]
    return dict(sorted(payload.items()))
