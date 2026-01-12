from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence

from .config import Config, load_config, reset_config
from .consent import (
    ConsentError,
    ExternalPermissionDenied,
    ensure_consent,
    ensure_external_permission,
    export_consent,
    grant_consent,
    prompt_for_consent,
)
from .logging_utils import get_logger
from .modes import ModeResolution, resolve_mode
from .project_ranking import rank_projects_from_snapshots
from .storage import (
    backup_database,
    close_db,
    export_snapshots_to_json,
    fetch_latest_snapshot,
    fetch_latest_snapshots,
    open_db,
    store_analysis_snapshot,
)
from .timeline import write_projects_timeline, write_skills_timeline
from .top_project_summaries import (
    AutoWriter,
    EvidenceItem,
    create_summary_template,
    export_markdown,
    export_readme_snippet,
)
from .zip_analyzer import InvalidArchiveError, ZipAnalyzer


logger = get_logger(__name__)


class ArchiveAnalysisError(RuntimeError):
    """Raised when archive analysis fails with a structured payload."""

    def __init__(self, payload: Mapping[str, object]) -> None:
        detail = payload.get("detail") if isinstance(payload, Mapping) else None
        message = detail if isinstance(detail, str) else payload.get("error", "Archive analysis failed")
        super().__init__(message)
        self.payload = dict(payload) if isinstance(payload, Mapping) else {"error": "InvalidInput", "detail": str(payload)}


class ConsentService:
    """Encapsulate local and external consent flows for easy mocking."""

    def __init__(
        self,
        *,
        ensure_consent_fn: Callable[..., object] = ensure_consent,
        prompt_fn: Callable[..., str] = prompt_for_consent,
        grant_fn: Callable[..., Config] = grant_consent,
        ensure_external_fn: Callable[..., object] = ensure_external_permission,
    ) -> None:
        self._ensure_consent = ensure_consent_fn
        self._prompt_for_consent = prompt_fn
        self._grant_consent = grant_fn
        self._ensure_external = ensure_external_fn

    def ensure_local_consent(self) -> object:
        return self._ensure_consent(require_granted=True)

    def prompt_and_grant(self) -> object:
        decision = self._prompt_for_consent()
        if decision == "accepted":
            config_state = self._grant_consent()
            return config_state.consent
        raise ConsentError("User declined consent prompt")

    def ensure_external(self, mode: ModeResolution, **kwargs: object) -> None:
        if mode.resolved != "external":
            return
        self._ensure_external(**kwargs)


class ConfigService:
    """Wrap configuration read/write helpers."""

    def __init__(
        self,
        *,
        load_fn: Callable[[], Config] = load_config,
        reset_fn: Callable[[], Config] = reset_config,
        export_consent_fn: Callable[[], dict[str, object]] = export_consent,
    ) -> None:
        self._load = load_fn
        self._reset = reset_fn
        self._export_consent = export_consent_fn

    def load(self) -> Config:
        return self._load()

    def reset(self) -> Config:
        return self._reset()

    def export_consent(self) -> dict[str, object]:
        return self._export_consent()


class ArchiveAnalyzerService:
    """Validate and analyze zip archives."""

    def __init__(self, analyzer: ZipAnalyzer | None = None) -> None:
        self._analyzer = analyzer or ZipAnalyzer()

    def validate_archive(self, archive_arg: str) -> tuple[Path | None, dict[str, object] | None, int]:
        archive_arg = (archive_arg or "").strip()
        if not archive_arg:
            payload = {"error": "InvalidInput", "detail": "Archive path must not be empty"}
            return None, payload, 5

        archive_path = Path(archive_arg).expanduser()
        if not archive_path.exists():
            detail = f"Archive not found: {archive_path}"
            payload = {"error": "FileNotFound", "detail": detail}
            return None, payload, 4
        if archive_path.suffix.lower() != ".zip":
            payload = {
                "error": "InvalidInput",
                "detail": "Unsupported file format. Please provide a .zip archive.",
            }
            return None, payload, 3

        return archive_path, None, 0

    def analyze(self, *args: object, **kwargs: object) -> dict[str, object]:
        try:
            return self._analyzer.analyze(*args, **kwargs)
        except InvalidArchiveError as exc:  # pragma: no cover - thin wrapper
            payload = getattr(exc, "payload", {"error": "InvalidInput", "detail": str(exc)})
            raise ArchiveAnalysisError(payload) from exc


class SnapshotStore:
    """Encapsulate database lifecycle and snapshot persistence."""

    def __init__(
        self,
        db_dir: Path | None = None,
        *,
        open_fn: Callable[[Path | None], object] = open_db,
        close_fn: Callable[[], None] = close_db,
        fetch_latest_fn: Callable[[object, str], Mapping[str, object] | None] = fetch_latest_snapshot,
        fetch_all_fn: Callable[[object], Iterable[Mapping[str, object]]] = fetch_latest_snapshots,
        store_snapshot_fn: Callable[[object, str, str, str | None, Mapping[str, object] | None], None] = store_analysis_snapshot,
        backup_fn: Callable[[object, Path], Path] = backup_database,
        export_fn: Callable[[object, Path], int] = export_snapshots_to_json,
    ) -> None:
        self.db_dir = db_dir
        self._open = open_fn
        self._close = close_fn
        self._fetch_latest = fetch_latest_fn
        self._fetch_all = fetch_all_fn
        self._store_snapshot = store_snapshot_fn
        self._backup = backup_fn
        self._export = export_fn
        self._conn: object | None = None

    def open(self) -> object:
        if self._conn is None:
            self._conn = self._open(self.db_dir)
        return self._conn

    def close(self) -> None:
        self._close()
        self._conn = None

    def fetch_latest(self, project_id: str) -> Mapping[str, object] | None:
        conn = self.open()
        return self._fetch_latest(conn, project_id)

    def fetch_all_latest(self) -> Iterable[Mapping[str, object]]:
        conn = self.open()
        return self._fetch_all(conn)

    def store_snapshot(
        self,
        project_id: str,
        *,
        classification: str = "unknown",
        primary_contributor: str | None = None,
        snapshot: Mapping[str, object] | None = None,
    ) -> None:
        conn = self.open()
        self._store_snapshot(conn, project_id, classification, primary_contributor, snapshot)

    def backup(self, destination: Path) -> Path:
        conn = self.open()
        return self._backup(conn, destination)

    def export_json(self, output_path: Path) -> int:
        conn = self.open()
        return self._export(conn, output_path)


class SnapshotSummaryService:
    """Provide structured summaries derived from the latest snapshot."""

    def __init__(self, store: SnapshotStore) -> None:
        self.store = store

    def _load_snapshot(self, project_id: str) -> Mapping[str, object] | None:
        return self.store.fetch_latest(project_id)

    def collab_summary(self, project_id: str) -> dict[str, object]:
        snapshot = self._load_snapshot(project_id)
        if not snapshot:
            return {"projectId": project_id, "detail": "No snapshots found"}
        collab = snapshot.get("collaboration") or {}
        return {
            "projectId": project_id,
            "classification": collab.get("classification", snapshot.get("classification", "unknown")),
            "primaryContributor": collab.get("primary_contributor") or snapshot.get("primary_contributor"),
            "collaboration": collab,
        }

    def tech_summary(self, project_id: str) -> dict[str, object]:
        snapshot = self._load_snapshot(project_id)
        if not snapshot:
            return {"projectId": project_id, "detail": "No snapshots found"}
        return {
            "projectId": project_id,
            "languages": snapshot.get("languages", {}),
            "frameworks": snapshot.get("frameworks", []),
        }

    def skill_summary(self, project_id: str) -> dict[str, object]:
        snapshot = self._load_snapshot(project_id)
        if not snapshot:
            return {"projectId": project_id, "detail": "No snapshots found"}
        return {
            "projectId": project_id,
            "skills": snapshot.get("skills", []),
            "skillTimeline": (snapshot.get("skill_timeline") or {}).get("skills", []),
            "topSkillsByYear": snapshot.get("top_skills_by_year", {}),
        }

    def metrics_summary(self, project_id: str) -> dict[str, object]:
        snapshot = self._load_snapshot(project_id)
        if not snapshot:
            return {"projectId": project_id, "detail": "No snapshots found"}
        file_summary = snapshot.get("file_summary", {}) or {}
        return {
            "projectId": project_id,
            "fileSummary": file_summary,
            "activityBreakdown": file_summary.get("activity_breakdown", {}),
            "timeline": file_summary.get("timeline", {}),
        }


class TimelineService:
    """Export project and skill timelines."""

    def __init__(
        self,
        *,
        projects_fn: Callable[[Path | None, Path], int] = write_projects_timeline,
        skills_fn: Callable[[Path | None, Path], int] = write_skills_timeline,
    ) -> None:
        self._projects_fn = projects_fn
        self._skills_fn = skills_fn

    def export_projects(self, db_dir: Path | None, output: Path) -> int:
        return self._projects_fn(db_dir, output)

    def export_skills(self, db_dir: Path | None, output: Path) -> int:
        return self._skills_fn(db_dir, output)


class RankingService:
    """Compute project rankings from stored snapshots."""

    def __init__(
        self,
        store: SnapshotStore,
        *,
        ranker: Callable[..., object] = rank_projects_from_snapshots,
    ) -> None:
        self.store = store
        self._ranker = ranker

    def rank(self, *, user: str | None = None, limit: int | None = None) -> tuple[list[object], dict[str, dict]]:
        raw_snapshots = self.store.fetch_all_latest()
        snapshot_map: dict[str, dict] = {}
        for row in raw_snapshots:
            pid = row.get("project_id")
            snap = row.get("snapshot")
            if not pid or not isinstance(snap, dict):
                continue
            snapshot_map[pid] = snap

        rankings = list(self._ranker(snapshot_map, user=user))
        if limit is not None and limit >= 0:
            rankings = rankings[:limit]
        return rankings, snapshot_map


class TopSummaryService:
    """Generate top project summary exports without LLM usage."""

    def __init__(
        self,
        store: SnapshotStore,
        *,
        ranker: Callable[..., object] = rank_projects_from_snapshots,
        template_fn: Callable[..., object] = create_summary_template,
        writer_cls: type[AutoWriter] = AutoWriter,
        export_markdown_fn: Callable[[object], str] = export_markdown,
        export_readme_fn: Callable[[object], str] = export_readme_snippet,
    ) -> None:
        self.store = store
        self._ranker = ranker
        self._template_fn = template_fn
        self._writer_cls = writer_cls
        self._export_markdown = export_markdown_fn
        self._export_readme = export_readme_fn

    def generate(
        self,
        *,
        project_id: str | None,
        output_dir: Path,
        pdf_output: Path | None,
    ) -> dict[str, object]:
        raw = self.store.fetch_all_latest()
        snapshots = {row["project_id"]: row["snapshot"] for row in raw if row.get("project_id") and isinstance(row.get("snapshot"), dict)}
        if not snapshots:
            return {"detail": "No project analyses available for summary.", "snapshots": 0}
        rankings = list(self._ranker(snapshots))
        target_id = project_id or (rankings[0].project_id if rankings else None)
        if not target_id:
            return {"detail": "No project available for summary.", "snapshots": len(snapshots)}
        snapshot = snapshots.get(target_id)
        if not snapshot:
            return {"error": "NotFound", "detail": f"Project '{target_id}' not found in snapshots."}
        ranking = next((r for r in rankings if r.project_id == target_id), None)
        template = self._template_fn(target_id, snapshot, ranking)
        evidence = [
            EvidenceItem(kind="metric", reference="analysis:file_count", detail=f"{snapshot.get('file_summary', {}).get('file_count', 0)} files", source="analysis"),
            EvidenceItem(kind="collaboration", reference="collaboration:contributors", detail="contributors weighted", source="analysis"),
            EvidenceItem(kind="languages", reference="languages", detail=", ".join(snapshot.get("languages", {}).keys()), source="analysis"),
        ]
        summary = self._writer_cls().compose(template, evidence, snapshot, ranking, rank_position=1, use_llm=False)
        out_dir = output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "top_project.md"
        readme_path = out_dir / "top_project_README.md"
        md_payload = self._export_markdown(summary)
        md_path.write_text(md_payload, encoding="utf-8")
        readme_path.write_text(self._export_readme(summary), encoding="utf-8")
        pdf_path = pdf_output or (out_dir / "top_project.pdf")
        pdf_path.write_bytes(md_payload.encode("utf-8"))
        return {
            "top_project": summary.title,
            "markdown": str(md_path),
            "readme": str(readme_path),
            "pdf": str(pdf_path),
            "evidence": [e.__dict__ for e in evidence],
            "confidence": {"llm_used": False, "mode": "offline", "guardrails": "facts quoted with references in markdown/readme/pdf"},
        }


@dataclass(frozen=True)
class PipelineArtifacts:
    """Bridge structure to keep pipeline integrations stable after refactor."""

    company: str
    projects: list[dict[str, object]]
    matches: list[dict[str, object]]
    company_profile: dict[str, object]
    company_qualities: dict[str, object]


class PipelineRunner:
    """Thin wrapper to keep run_full_pipeline compatible with service usage."""

    def __init__(self, resolver: Callable[..., ModeResolution] = resolve_mode) -> None:
        self._resolve_mode = resolver

    def run(self, *args: object, **kwargs: object) -> PipelineArtifacts:
        # Defer to existing run_full_pipeline to maintain behavior.
        from .pipeline import run_full_pipeline

        result = run_full_pipeline(*args, **kwargs)
        return PipelineArtifacts(
            company=result.get("company"),
            projects=result.get("projects", []),
            matches=result.get("matches", []),
            company_profile=result.get("company_profile", {}),
            company_qualities=result.get("company_qualities", {}),
        )
