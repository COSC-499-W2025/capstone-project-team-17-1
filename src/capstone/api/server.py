import os
import traceback
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from capstone.api.middleware.request_id import RequestIdMiddleware
from capstone.api.routes import (
    consent,
    projects,
    skills,
    resume,
    job_match,
    portfolio,
    portfolio_showcase,
    legacy_aliases,
)


def _configure_module(module, db_dir: Optional[str], auth_token: Optional[str], app: FastAPI, name: str) -> None:
    """
    If a routes module exposes `configure(db_dir, auth_token)`, call it.
    Store any configure error on app.state.<name>_configure_error for debugging.
    """
    cfg = getattr(module, "configure", None)
    if callable(cfg):
        try:
            cfg(db_dir=db_dir, auth_token=auth_token)
        except Exception:
            setattr(app.state, f"{name}_configure_error", traceback.format_exc())


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

    return app


def get_app_for_tests(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    return create_app(db_dir=db_dir, auth_token=auth_token)


DB_DIR = os.getenv("CAPSTONE_DB_DIR")
AUTH_TOKEN = os.getenv("CAPSTONE_AUTH_TOKEN")

app = create_app(db_dir=DB_DIR, auth_token=AUTH_TOKEN)