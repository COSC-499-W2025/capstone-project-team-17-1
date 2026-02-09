from fastapi import FastAPI
from capstone.api.routes.consent import router as consent_router
from capstone.api.routes.projects import router as projects_router
from capstone.api.routes.skills import router as skills_router
from capstone.api.routes.portfolio import router as portfolio_router

app = FastAPI(title="Capstone API")

@app.get("/")
def root():
    return {"message": "Capstone API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(consent_router)
app.include_router(projects_router)
app.include_router(skills_router)
app.include_router(portfolio_router)