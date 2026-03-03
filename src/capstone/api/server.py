import os
import traceback
from fastapi import FastAPI

from capstone.api.routes.consent import router as consent_router
from capstone.api.routes.projects import router as projects_router
from capstone.api.routes.skills import router as skills_router
from capstone.api.routes.legacy_aliases import router as legacy_aliases_router


def _safe_import_job_match():
    """Attempt to import job_match router (optional)."""
    try:
        from capstone.api.routes.job_match import router  # type: ignore
        return router, None
    except Exception:
        return None, traceback.format_exc()


def _safe_import_portfolio():
    """Attempt to import portfolio router + configure."""
    try:
        from capstone.api.routes.portfolio import router, configure  # type: ignore
        return router, configure, None
    except Exception:
        return None, None, traceback.format_exc()


def _safe_import_showcase():
    """Attempt to import showcase router + configure."""
    try:
        from capstone.api.routes.portfolio_showcase import router, configure  # type: ignore
        return router, configure, None
    except Exception:
        return None, None, traceback.format_exc()


def _safe_import_resumes():
    """Attempt to import new modular resumes router + configure."""
    try:
        from capstone.api.routes.resumes import router, configure  # type: ignore
        return router, configure, None
    except Exception:
        return None, None, traceback.format_exc()


def create_app(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    app = FastAPI(title="Capstone API")
    app.state.auth_token = auth_token

    @app.get("/")
    def root():
        return {"message": "Capstone API is running"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Always-available routers
    app.include_router(consent_router)
    app.include_router(projects_router)
    app.include_router(skills_router)

    # Optional job-match routes (since routes/job_match.py may not exist in this branch)
    job_match_router, job_match_err = _safe_import_job_match()
    if job_match_router is not None:
        app.include_router(job_match_router)
    else:
        app.state.job_match_import_error = job_match_err

    # Optional portfolio routes
    portfolio_router, configure_portfolio, portfolio_err = _safe_import_portfolio()
    if portfolio_err is None and portfolio_router is not None and configure_portfolio is not None:
        try:
            configure_portfolio(db_dir, auth_token)
            app.include_router(portfolio_router)
        except Exception:
            app.state.portfolio_mount_error = traceback.format_exc()
    else:
        app.state.portfolio_import_error = portfolio_err

    # Optional showcase routes
    showcase_router, configure_showcase, showcase_err = _safe_import_showcase()
    if showcase_err is None and showcase_router is not None and configure_showcase is not None:
        try:
            configure_showcase(db_dir, auth_token)
            app.include_router(showcase_router)
        except Exception:
            app.state.showcase_mount_error = traceback.format_exc()
    else:
        app.state.showcase_import_error = showcase_err

    # Modular resume routes (/resumes/*)
    resumes_router, configure_resumes, resumes_err = _safe_import_resumes()
    if resumes_err is None and resumes_router is not None and configure_resumes is not None:
        try:
            configure_resumes(db_dir, auth_token)
            app.include_router(resumes_router)
        except Exception:
            app.state.resume_mount_error = traceback.format_exc()
    else:
        app.state.resume_import_error = resumes_err

    # Legacy aliases (old endpoints like /portfolios/* and /users/*)
    app.include_router(legacy_aliases_router)

    # Debug endpoint
    @app.get("/__debug/routers")
    def debug_routers():
        routes = sorted({getattr(r, "path", str(r)) for r in app.router.routes})
        return {
            "routes": routes,
            "job_match_import_error": getattr(app.state, "job_match_import_error", None),
            "portfolio_import_error": getattr(app.state, "portfolio_import_error", None),
            "portfolio_mount_error": getattr(app.state, "portfolio_mount_error", None),
            "showcase_import_error": getattr(app.state, "showcase_import_error", None),
            "showcase_mount_error": getattr(app.state, "showcase_mount_error", None),
            "resumes_import_error": getattr(app.state, "resume_import_error", None),
            "resumes_mount_error": getattr(app.state, "resume_mount_error", None),
        }

    return app


def get_app_for_tests(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    return create_app(db_dir=db_dir, auth_token=auth_token)


DB_DIR = os.getenv("CAPSTONE_DB_DIR")
AUTH_TOKEN = os.getenv("CAPSTONE_AUTH_TOKEN")

app = create_app(db_dir=DB_DIR, auth_token=AUTH_TOKEN)
