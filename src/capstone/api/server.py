import os
import traceback
from typing import Optional


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

    # State (some deps look here)
    app.state.db_dir = db_dir
    app.state.auth_token = auth_token

    # Middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # dev-friendly; adjust in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure route modules (if they support it)
    # Do this BEFORE including routers so dependency wiring is ready.
    _configure_module(projects, db_dir, auth_token, app, "projects")
    _configure_module(skills, db_dir, auth_token, app, "skills")
    _configure_module(resume, db_dir, auth_token, app, "resume")
    _configure_module(job_match, db_dir, auth_token, app, "job_match")
    _configure_module(portfolio, db_dir, auth_token, app, "portfolio")
    _configure_module(portfolio_showcase, db_dir, auth_token, app, "portfolio_showcase")
    _configure_module(legacy_aliases, db_dir, auth_token, app, "legacy_aliases")
    _configure_module(consent, db_dir, auth_token, app, "consent")

    # Routers (include ONCE)
    app.include_router(consent.router)
    app.include_router(projects.router)
    app.include_router(skills.router)
    app.include_router(resume.router)
    app.include_router(job_match.router)
    app.include_router(portfolio.router)
    app.include_router(portfolio_showcase.router)
    app.include_router(legacy_aliases.router)

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