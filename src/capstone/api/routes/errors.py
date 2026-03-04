from fastapi import APIRouter
from typing import Dict, Any

from capstone.storage import (
    open_db,
    close_db,
    fetch_latest_snapshots_with_zip,
    save_error_results,
    fetch_error_results,
)
from capstone.consent import (
    ensure_external_permission,
    ExternalPermissionDenied,
)
from capstone.error_analysis import run_ai_error_analysis
from capstone.activity_log import log_event

router = APIRouter(tags=["errors"])


# ---------------------------------------------------------
# POST /errors/analyze
# Trigger AI error analysis
# ---------------------------------------------------------
@router.post("/errors/analyze")
def analyze_errors() -> Dict[str, Any]:
    conn = open_db()

    try:
        # 🔥 Use the NEW function that returns snapshot + zip_path
        snapshots = fetch_latest_snapshots_with_zip(conn)

        if not snapshots:
            return {"status": "no_projects"}

        # 🔒 Check external AI permission
        try:
            ensure_external_permission("capstone.external.error_analysis")
        except ExternalPermissionDenied:
            log_event(
                "ERROR",
                "AI error analysis failed: Consent required",
            )
            return {"status": "consent_required"}

        for row in snapshots:
            project_id = row.get("project_id")
            snapshot = row.get("snapshot")
            zip_path = row.get("zip_path")

            # Safety guard
            if not project_id or not snapshot or not zip_path:
                continue

            errors = run_ai_error_analysis(
                project_id=project_id,
                snapshot=snapshot,
                zip_path=zip_path,
            )

            save_error_results(conn, project_id, errors)
            log_event(
                "SUCCESS",
                "AI error analysis completed Successfully",
            )

        return {"status": "analysis_complete"}

    finally:
        close_db()


# ---------------------------------------------------------
# GET /errors
# Fetch stored AI results only (NO AI CALL HERE)
# ---------------------------------------------------------
@router.get("/errors")
def get_error_analysis() -> Dict[str, Any]:
    conn = open_db()

    try:
        results = fetch_error_results(conn)

        if results is None:
            return {"status": "not_analyzed"}

        if not results:
            return {"status": "ok", "errors": []}
        
        return {
            "status": "ok",
            "errors": results,
        }

    finally:
        close_db()