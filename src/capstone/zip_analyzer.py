"""Zip analysis pipeline orchestrator."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Iterable, List, Tuple, Dict
from zipfile import BadZipFile, ZipFile

from .collaboration import CollaborationSummary, analyze_git_logs
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
from .storage import open_db, store_analysis_snapshot


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

    def analyze(
        self,
        zip_path: Path,
        metadata_path: Path,
        summary_path: Path,
        mode: ModeResolution,
        preferences: Preferences,
        project_id: str | None = None,
        db_dir: Path | None = None,
    ) -> dict[str, object]:
        start = perf_counter()
        zip_path = zip_path.expanduser().resolve()
        if zip_path.suffix.lower() != ".zip":
            detail = "Expected a .zip archive"
            self._logger.error("Invalid input format for %s", zip_path)
            raise InvalidArchiveError(detail)

        try:
            with ZipFile(zip_path) as archive:
                return self._analyze_archive(
                    archive,
                    zip_path,
                    metadata_path,
                    summary_path,
                    mode,
                    preferences,
                    start,
                    project_id,
                    db_dir,
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
    ) -> dict[str, object]:
        metadata_records: List[dict[str, object]] = []
        metrics_inputs: List[FileMetric] = []
        language_counter: Counter[str] = Counter()
        frameworks = set()
        git_logs: list[str] = []
        skill_events: List[Tuple[str, str, datetime, float]] = []

        for info in archive.infolist():
            if info.is_dir():
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
            if path_lower.endswith("package.json"):
                content = archive.read(info).decode("utf-8", errors="ignore")
                detected = detect_frameworks_from_package_json(content)
                frameworks.update(detected)
                for fw in detected:
                    skill_events.append((fw, "framework", datetime.fromisoformat(record["modified"]), 1.0))
            elif path_lower.endswith("requirements.txt"):
                content = archive.read(info).decode("utf-8", errors="ignore").splitlines()
                detected = detect_frameworks_from_python_requirements(content)
                frameworks.update(detected)
                for fw in detected:
                    skill_events.append((fw, "framework", datetime.fromisoformat(record["modified"]), 1.0))
            elif ".git/logs/" in path_lower:
                content = archive.read(info).decode("utf-8", errors="ignore")
                git_logs.extend(content.splitlines())
            tool_skills = self._detect_tool_skills(path_lower)
            if tool_skills:
                ts = datetime.fromisoformat(record["modified"])
                for skill_name, category in tool_skills:
                    skill_events.append((skill_name, category, ts, 1.0))

        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("w", encoding="utf-8") as fh:
            for record in metadata_records:
                fh.write(json.dumps(record))
                fh.write("\n")

        metric_summary = compute_metrics(metrics_inputs)
        collaboration = self._summarize_collaboration(git_logs)
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
            "requested_mode": mode.requested,
            "resolved_mode": mode.resolved,
            "mode_reason": mode.reason,
            "local_mode_label": preferences.labels.get("local_mode", "Local Analysis Mode"),
            "file_summary": asdict(metric_summary),
            "languages": dict(language_counter),
            "frameworks": sorted(frameworks),
            "collaboration": asdict(collaboration),
            "metadata_output": str(metadata_path),
            "scan_duration_seconds": round(duration, 4),
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
        classification = collaboration.classification
        primary_contributor = collaboration.primary_contributor
        conn = open_db(db_dir)
        store_analysis_snapshot(
            conn,
            project_id=project_id,
            classification=classification,
            primary_contributor=primary_contributor,
            snapshot=summary,
        )
        self._logger.info("Stored zip analysis snapshot for %s", project_id)

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

    def _summarize_collaboration(self, git_logs: Iterable[str]) -> CollaborationSummary:
        if not git_logs:
            return CollaborationSummary("unknown", {}, None)
        return analyze_git_logs(git_logs)


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
