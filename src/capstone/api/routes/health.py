from fastapi import APIRouter
from capstone.health import compute_health_for_all
from capstone.storage import (
    open_db,
    close_db,
    fetch_latest_snapshots,
    fetch_error_results,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/project-health")
def get_project_health():
    conn = open_db()

    try:
        raw_snapshots = fetch_latest_snapshots(conn)

        if not raw_snapshots:
            return []

        # 🔥 Convert list -> dict[project_id -> snapshot]
        snapshots = {}

        for row in raw_snapshots:
            project_id = row.get("project_id")
            snapshot = row.get("snapshot")

            if project_id and snapshot:
                snapshots[project_id] = snapshot

        # Fetch stored AI error results
        raw_errors = fetch_error_results(conn) or []

        error_reports = {}

        for row in raw_errors:
            project_id = row.get("project_id")
            severity = row.get("severity", "low")

            if not project_id:
                continue

            if project_id not in error_reports:
                error_reports[project_id] = {
                    "errors": 0,
                    "warnings": 0,
                }

            if severity == "high":
                error_reports[project_id]["errors"] += 1
            elif severity == "medium":
                error_reports[project_id]["warnings"] += 1
            else:
                error_reports[project_id]["warnings"] += 1

        health_list = compute_health_for_all(snapshots, error_reports)

        return [
            {
                "project_id": h.project_id,
                "score": h.score,
                "status": h.status,
                "errors": h.errors,
                "warnings": h.warnings,
                "last_active_days": h.last_active_days,
                "contribution_ratio": h.contribution_ratio,
                "diversity": h.diversity,
            }
            for h in health_list
        ]

    finally:
        close_db()