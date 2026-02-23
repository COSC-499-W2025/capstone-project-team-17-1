import os
from fastapi import FastAPI
from capstone.api.routes.consent import router as consent_router
from capstone.api.routes.projects import router as projects_router
from capstone.api.routes.skills import router as skills_router

try:
    from capstone.api.routes.portfolio import router as portfolio_router, configure as configure_portfolio
except ImportError:
    portfolio_router = None
    configure_portfolio = None
try:
    from capstone.api.routes.portfolio_showcase import router as showcase_router, configure as configure_showcase
except ImportError:
    showcase_router = None
    configure_showcase = None

def create_app(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    app = FastAPI(title="Capstone API")
    app.state.auth_token = auth_token

    @app.get("/")
    def root():
        return {"message": "Capstone API is running"}

    @app.get("/health")
    def health():
        return {"status": "ok"}
    
    app.include_router(consent_router)
    app.include_router(projects_router)
    app.include_router(skills_router)
    

    if configure_portfolio and portfolio_router:
        configure_portfolio(db_dir, auth_token)
        app.include_router(portfolio_router)
        
    if configure_showcase and showcase_router:
        configure_showcase(db_dir, auth_token)
        app.include_router(showcase_router)

    return app

DB_DIR = os.getenv("CAPSTONE_DB_DIR")
AUTH_TOKEN = os.getenv("CAPSTONE_AUTH_TOKEN")

app = create_app(db_dir=DB_DIR, auth_token=AUTH_TOKEN)
