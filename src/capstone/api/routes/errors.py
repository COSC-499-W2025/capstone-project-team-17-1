from fastapi import APIRouter, Request
from typing import Dict, Any
import capstone.storage as _storage

from capstone.storage import (
    fetch_latest_snapshots_with_zip,
    save_error_results,
    fetch_error_results,
)
from capstone.portfolio_retrieval import _db_session
from capstone.consent import (
    ensure_local_consent,
    ConsentError,
    ensure_external_permission,
    ExternalPermissionDenied,
)
from capstone.error_analysis import run_ai_error_analysis
from capstone.activity_log import log_event

router = APIRouter(tags=["errors"])


def _restore_user_from_request(request: Request) -> None:
    """
    Restore storage.CURRENT_USER from the session Bearer token if present.
    Called at the top of every errors endpoint so the correct per-user DB is
    used even after a server restart (where the global CURRENT_USER is None).
    """
    try:
        from capstone.api.routes.auth import get_authenticated_username
        username = get_authenticated_username(request)
        if username:
            _storage.CURRENT_USER = username
            print(f"[errors] Restored CURRENT_USER = {username!r} from Bearer token", flush=True)
        else:
            print(f"[errors] No Bearer token — CURRENT_USER stays as {_storage.CURRENT_USER!r}", flush=True)
    except Exception as exc:
        print(f"[errors] Could not restore user from token: {exc}", flush=True)


# ---------------------------------------------------------
# POST /errors/analyze
# Trigger AI error analysis
# ---------------------------------------------------------
@router.post("/errors/analyze")
def analyze_errors(request: Request) -> Dict[str, Any]:
    try:
        _restore_user_from_request(request)

        db_path = _storage.get_database_path()
        print(f"[errors/analyze] CURRENT_USER = {_storage.CURRENT_USER!r}", flush=True)
        print(f"[errors/analyze] DB path       = {db_path}", flush=True)
        print(f"[errors/analyze] DB exists?    = {db_path.exists()}", flush=True)

        try:
            ensure_local_consent()
        except ConsentError:
            log_event(
                "ERROR",
                "AI error analysis failed: Local consent required",
            )
            return {"status": "local_consent_required"}

        with _db_session(None) as conn:
            raw_rows = conn.execute(
                "SELECT project_id, created_at, zip_path FROM project_analysis ORDER BY id DESC LIMIT 10"
            ).fetchall()
            print(f"[errors/analyze] project_analysis rows ({len(raw_rows)}):", flush=True)
            for r in raw_rows:
                print(f"  project_id={r[0]!r}  created_at={r[1]!r}  zip_path={r[2]!r}", flush=True)

            snapshots = fetch_latest_snapshots_with_zip(conn)
            print(f"[errors/analyze] fetch_latest_snapshots_with_zip -> {len(snapshots)} row(s)", flush=True)

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

    except Exception as exc:
        import traceback
        print(f"[errors/analyze] EXCEPTION: {exc}", flush=True)
        traceback.print_exc()
        log_event("ERROR", f"AI error analysis failed: {exc}")
        raise


# ---------------------------------------------------------
# GET /errors
# Fetch stored AI results only (NO AI CALL HERE)
# ---------------------------------------------------------
@router.get("/errors")
def get_error_analysis(request: Request) -> Dict[str, Any]:
    _restore_user_from_request(request)

    with _db_session(None) as conn:
        results = fetch_error_results(conn)

        if results is None:
            return {"status": "not_analyzed"}

        if not results:
            return {"status": "ok", "errors": []}
        
        return {
            "status": "ok",
            "errors": results,
        }
