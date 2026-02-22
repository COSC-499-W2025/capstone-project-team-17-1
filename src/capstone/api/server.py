from fastapi import FastAPI
from capstone.api.routes.consent import router as consent_router
from capstone.api.routes.projects import router as projects_router
from capstone.api.routes.skills import router as skills_router
from capstone.api.routes.portfolio import router as portfolio_router, configure as configure_portfolio
from capstone.api.routes.resume import router as resume_router, configure as configure_resume

def create_app(db_dir: str | None = None, auth_token: str | None = None) -> FastAPI:
    app = FastAPI(title="Capstone API")
    app.state.auth_token = auth_token

    @app.get("/")
    def root():
        return {"message": "Capstone API is running"}

    @app.get("/health")
    def health():
        return {"status": "ok"}
    
    configure_portfolio(db_dir, auth_token)
    configure_resume(db_dir, auth_token)

    app.include_router(consent_router)
    app.include_router(projects_router)
    app.include_router(skills_router)
    app.include_router(portfolio_router)
    app.include_router(resume_router)
    
    return app

# no functional change, just clarity for tests
def get_app_for_tests(tmp_db_dir: str) -> FastAPI:
    return create_app(db_dir=tmp_db_dir, auth_token=None)

app = create_app()
