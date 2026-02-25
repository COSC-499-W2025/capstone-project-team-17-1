from __future__ import annotations

from fastapi import APIRouter, Request, Query

from capstone.api.routes.portfolio_showcase import (
    list_users as showcase_list_users,
    list_user_projects as showcase_list_user_projects,
    portfolio_summary as showcase_portfolio_summary,
    latest as showcase_latest,
    evidence_latest as showcase_evidence_latest,
    list_ as showcase_portfolios_list,
    get_portfolio_showcase as showcase_get_portfolio_showcase,
    get_portfolio_showcase_query as showcase_get_portfolio_showcase_query,
)

router = APIRouter()

@router.get("/users")
def legacy_users(request: Request):
    return showcase_list_users(request=request)

@router.get("/users/{user}/projects")
def legacy_user_projects(user: str, request: Request):
    return showcase_list_user_projects(user=user, request=request)

@router.get("/portfolio/summary")
def legacy_portfolio_summary(user: str, request: Request, limit: int = 3):
    return showcase_portfolio_summary(user=user, request=request, limit=limit)

@router.get("/portfolio/showcase")
def legacy_portfolio_showcase_query(request: Request, projectId: str, user: str | None = None):
    return showcase_get_portfolio_showcase_query(request=request, projectId=projectId, user=user)

@router.get("/portfolio/{project_id}")
def legacy_portfolio_showcase(project_id: str, request: Request, user: str | None = None):
    return showcase_get_portfolio_showcase(project_id=project_id, request=request, user=user)

@router.get("/portfolios/latest")
def legacy_portfolios_latest(
    request: Request,
    projectId: str = Query(...),
    view: str | None = None,
    user: str | None = None,
):
    return showcase_latest(request=request, projectId=projectId, view=view, user=user)

@router.get("/portfolios/evidence")
def legacy_portfolios_evidence(request: Request, projectId: str = Query(...)):
    return showcase_evidence_latest(request=request, projectId=projectId)

@router.get("/portfolios")
def legacy_portfolios_list(
    request: Request,
    projectId: str = Query(...),
    page: int = Query(1),
    pageSize: int = Query(20),
    sort: str = Query("created_at:desc"),
):
    return showcase_portfolios_list(
        request=request,
        projectId=projectId,
        page=page,
        pageSize=pageSize,
        sort=sort,
    )
