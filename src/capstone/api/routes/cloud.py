from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError

import capstone.storage as storage
import capstone.api.routes.auth as auth_routes
from capstone.system.cloud_storage import (
    test_connection,
    test_upload,
    upload_database,
    download_database,
    upload_project_zip,
    download_project_zip,
    download_all_project_zips,
)

router = APIRouter(prefix="/cloud", tags=["cloud"])

class ProjectZipPayload(BaseModel):
    project_id: str
    zip_path: str
    filename: str | None = None
    
# auth lookup so all protected route use same session check
def get_current_username(request: Request) -> str:
    session = auth_routes._require_session(request)
    username = session["user"]["username"]
    storage.CURRENT_USER = username
    return username

def cloud_op(fn):
    try:
        return fn()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        raise HTTPException(status_code=502, detail=f"cloud storage error: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"unknown error: {str(e)}") from e

@router.get("/test")
def cloud_test():
    return cloud_op(lambda: {"status": "connected", "buckets": test_connection()}) # wrap in cloud_op to catch any unexpected cloud errors and return as HTTP errors instead

@router.get("/test-upload")
def cloud_test_upload():
    return cloud_op(test_upload)

@router.get("/db")
def debug_db():
    conn = storage.open_db()
    try:
        return {
            "current_user": getattr(storage, "CURRENT_USER", None),
            "db_path": str(storage.get_database_path())
        }
    finally:
        conn.close()

@router.post("/db/upload")
def cloud_db_upload(request: Request):
    curr_user = get_current_username(request)
    return cloud_op(lambda: upload_database(curr_user))

@router.post("/db/download")
def cloud_db_download(request: Request):
    curr_user = get_current_username(request)
    return cloud_op(lambda: download_database(curr_user))

@router.post("/projects/download-all")
def cloud_projects_download_all(request: Request):
    curr_user = get_current_username(request)
    return cloud_op(lambda: download_all_project_zips(curr_user))


@router.post("/project/upload")
def cloud_project_upload(payload: ProjectZipPayload, request: Request):
    curr_user = get_current_username(request)

    zip_path = Path(payload.zip_path)
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="zip file not found")

    return cloud_op(lambda: upload_project_zip(curr_user, payload.project_id, zip_path, payload.filename))


@router.post("/project/download")
def cloud_project_download(payload: ProjectZipPayload, request: Request):
    curr_user = get_current_username(request)
    target_path = Path(payload.zip_path)
    filename = payload.filename or "project.zip"

    return cloud_op(lambda: download_project_zip(
        curr_user,
        payload.project_id,
        target_path,
        filename,
    ))