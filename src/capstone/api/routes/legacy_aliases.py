from __future__ import annotations

from fastapi import APIRouter, Request, Query

from capstone.api.routes.portfolio_showcase import (
    list_users as showcase_list_users,
    list_user_projects as showcase_list_user_projects,
    latest as showcase_latest,
    evidence_latest as showcase_evidence_latest,
)

router = APIRouter()

@router.get("/users")
def legacy_users(request: Request):
    return showcase_list_users(request=request)

@router.get("/users/{user}/projects")
def legacy_user_projects(user: str, request: Request):
    return showcase_list_user_projects(user=user, request=request)

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