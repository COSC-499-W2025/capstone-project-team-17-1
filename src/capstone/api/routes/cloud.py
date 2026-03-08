from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import capstone.storage as storage
from capstone.system.cloud_storage import (
    test_connection,
    test_upload,
    upload_database,
    download_database,
    upload_project_zip,
    download_project_zip,
)

router = APIRouter(prefix="/cloud", tags=["cloud"])


class ProjectZipPayload(BaseModel):
    project_id: str
    zip_path: str
    filename: str | None = None


@router.get("/test")
def cloud_test():
    result = test_connection()
    return {"status": "connected", "buckets": result}


@router.get("/test-upload")
def cloud_test_upload():
    return test_upload()


@router.get("/db")
def debug_db():
    conn = storage.open_db()
    try:
        return {
            "current_user": storage.CURRENT_USER,
            "db_path": str(storage.get_database_path()),
        }
    finally:
        conn.close()


@router.post("/db/upload")
def cloud_db_upload():
    if not storage.CURRENT_USER:
        raise HTTPException(status_code=400, detail="no logged in user")

    return upload_database(storage.CURRENT_USER)


@router.post("/db/download")
def cloud_db_download():
    if not storage.CURRENT_USER:
        raise HTTPException(status_code=400, detail="no logged in user")

    return download_database(storage.CURRENT_USER)


@router.post("/project/upload")
def cloud_project_upload(payload: ProjectZipPayload):
    if not storage.CURRENT_USER:
        raise HTTPException(status_code=400, detail="no logged in user")

    zip_path = Path(payload.zip_path)
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="zip file not found")

    return upload_project_zip(
        storage.CURRENT_USER,
        payload.project_id,
        zip_path,
        payload.filename,
    )


@router.post("/project/download")
def cloud_project_download(payload: ProjectZipPayload):
    if not storage.CURRENT_USER:
        raise HTTPException(status_code=400, detail="no logged in user")

    target_path = Path(payload.zip_path)

    filename = payload.filename or "project.zip"

    return download_project_zip(
        storage.CURRENT_USER,
        payload.project_id,
        target_path,
        filename,
    )