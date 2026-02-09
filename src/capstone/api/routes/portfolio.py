from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from enum import Enum

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

class PortfolioProject(BaseModel):
    project_id: str
    title: str
    summary: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    
class Portfolio(BaseModel):
    id: str
    owner: Optional[str] = None
    projects: List[PortfolioProject]
    created_at: datetime
    updated_at: datetime
    
class GeneratePortfolioRequest(BaseModel):
    project_ids: List[str] = Field(..., min_length=1)
    owner: Optional[str] = None
    style: Optional[str] = "default"
    
class EditPortfolioRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    projects: Optional[List[PortfolioProject]] = None
    
class PortfolioResponse(BaseModel):
    portfolio: Portfolio
    
class ExportFormat(str, Enum):
    json = "json"
    markdown = "markdown"
    pdf = "pdf"
    
def require_demo_portfolio(portfolio_id: str):
    if portfolio_id != "demo":
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
def build_portfolio(portfolio_id: str, owner: Optional[str], projects: List[PortfolioProject]) -> Portfolio:
    now = datetime.now(UTC)
    
    return Portfolio(
        id = portfolio_id,
        owner = owner,
        projects = projects,
        created_at = now,
        updated_at = now
    )
    
# Endpoints    

# GET /portfolio/{id} for fetching existing portfolio
@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(portfolio_id: str):
    require_demo_portfolio(portfolio_id)
    
    portfolio = build_portfolio(
        portfolio_id = portfolio_id,
        owner = "user123",
        projects = []
    )
    
    return {"portfolio": portfolio}

# POST /portfolio/generate to create portfolio from newly analyzed projects
# pulls project snapshots from db
# ranks and generates project summaries
@router.post("/generate", response_model=PortfolioResponse)
def generate_portfolio(payload: GeneratePortfolioRequest):
        projects=[
            PortfolioProject(
                project_id=pid, 
                title=f"Project_{pid}"
            ) 
            for pid in payload.project_ids
        ]
        
        portfolio = build_portfolio(
            portfolio_id = "portfolio_001",
            owner = payload.owner,
            projects = projects
        )
    
        return {"portfolio": portfolio}

# POST /portfolio/{id}/edit to modify existing portfolio contents
@router.post("/{portfolio_id}/edit", response_model=PortfolioResponse)
def edit_portfolio(portfolio_id: str, payload: EditPortfolioRequest):
    require_demo_portfolio(portfolio_id)
    
    portfolio = build_portfolio(
        portfolio_id = portfolio_id,
        owner = "user123",
        projects = payload.projects or []
    )
    
    return {"portfolio": portfolio}

# GET /portfolio/{id}/export to return exportable portfolio
@router.get("/{portfolio_id}/export")
def export_portfolio(portfolio_id: str, format: ExportFormat = ExportFormat.json):
    require_demo_portfolio(portfolio_id)
    
    if format == "json":
        return {
            "portfolio_id": portfolio_id,
            "exported_at": datetime.now(UTC).isoformat()
        }
    
    if format == "markdown":
        return {
            "content": "# Portfolio\n\nGenerated portfolio content here"
        }
        
    if format == "pdf":
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<<>>\n"
            b"trailer<<>>\n"
            b"%%EOF"
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="portfolio_{portfolio_id}.pdf"'
            }
        )
        
    raise HTTPException(status_code=400, detail="Unsupported format")