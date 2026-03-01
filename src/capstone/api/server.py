import os
import traceback
from importlib import import_module
from typing import Any

from fastapi import FastAPI

from capstone.api.routes.consent import router as consent_router
from capstone.api.routes.projects import router as projects_router
from capstone.api.routes.skills import router as skills_router
from capstone.api.routes.legacy_aliases import router as legacy_aliases_router
from capstone.api.middleware.request_id import RequestIdMiddleware


def _safe_import(module_path: str, router_attr: str = "router", configure_attr: str = "configure"):
    """
    Safely import a router module that may not exist on all branches.

    Returns:
        (router, configure, error_str)
    """
    try:
        mod = import_module(module_path)
        router = getattr(mod, router_attr, None)
        configure = getattr(mod, configure_attr, None)
        return router, configure, None
    except Exception:
        return None, None, traceback.format_exc()


def _mount_optional_router(
    app: FastAPI,
    *,
    module_path: str,
    state_prefix: str,
    db_dir: str | None,
    auth_token: str | None,
) -> None:
    """
    Import a router module and mount it on the app.
    If a configure(db_dir, auth_token) exists, call it before mounting.
    Records any import/mount error on app.state.<...>.
    """
    router, configure, err = _safe_import(module_path)

    if err is not None:
        setattr(app.state, f"{state_prefix}_import_error", err)
        return

    if router is None:
        setattr(app.state, f"{state_prefix}_import_error", f"Module imported but '{module_path}.router' was not found.")
        return

    # Configure if present
    if callable(configure):
        try:
            configure(db_dir, auth_token)
        except Exception:
            setattr(app.state, f"{state_prefix}_mount_error", traceback.format_exc())
            return

    # Mount router
    try:
        app.include_router(router)
    except Exception:
        setattr(app.state, f"{state_prefix}_mount_error", traceback.format_exc())


def create_app(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    app = FastAPI(title="Capstone API")
    app.add_middleware(RequestIdMiddleware)
    app.state.auth_token = auth_token

    @app.get("/")
    def root():
        return {"message": "Capstone API is running"}

    @app.get("/health")
    def health():
        # If you want, you can surface partial-mount errors here too.
        return {"status": "ok"}

    # Always-available routers
    app.include_router(consent_router)
    app.include_router(projects_router)
    app.include_router(skills_router)
    

    # Optional routers (safe import + configure + mount)
    _mount_optional_router(
        app,
        module_path="capstone.api.routes.job_match",
        state_prefix="job_match",
        db_dir=db_dir,
        auth_token=auth_token,
    )

    _mount_optional_router(
        app,
        module_path="capstone.api.routes.portfolio",
        state_prefix="portfolio",
        db_dir=db_dir,
        auth_token=auth_token,
    )

    _mount_optional_router(
        app,
        module_path="capstone.api.routes.portfolio_showcase",
        state_prefix="showcase",
        db_dir=db_dir,
        auth_token=auth_token,
    )

    _mount_optional_router(
        app,
        module_path="capstone.api.routes.resume",
        state_prefix="resume",
        db_dir=db_dir,
        auth_token=auth_token,
    )

    # Legacy aliases (old endpoints like /portfolios/* and /users/*)
    app.include_router(legacy_aliases_router)

    # Debug endpoint (gated)
    if os.getenv("CAPSTONE_DEBUG_ROUTES") == "1":
        @app.get("/__debug/routers")
        def debug_routers():
            routes = sorted({getattr(r, "path", str(r)) for r in app.router.routes})
            return {
                "routes": routes,
                "job_match_import_error": getattr(app.state, "job_match_import_error", None),
                "job_match_mount_error": getattr(app.state, "job_match_mount_error", None),
                "portfolio_import_error": getattr(app.state, "portfolio_import_error", None),
                "portfolio_mount_error": getattr(app.state, "portfolio_mount_error", None),
                "showcase_import_error": getattr(app.state, "showcase_import_error", None),
                "showcase_mount_error": getattr(app.state, "showcase_mount_error", None),
                "resume_import_error": getattr(app.state, "resume_import_error", None),
                "resume_mount_error": getattr(app.state, "resume_mount_error", None),
            }

    return app


def get_app_for_tests(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    return create_app(db_dir=db_dir, auth_token=auth_token)


DB_DIR = os.getenv("CAPSTONE_DB_DIR")
AUTH_TOKEN = os.getenv("CAPSTONE_AUTH_TOKEN")

app = create_app(db_dir=DB_DIR, auth_token=AUTH_TOKEN)