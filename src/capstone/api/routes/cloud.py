from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

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


def _get_current_username(request: Request) -> str:
    username = auth_routes.get_authenticated_username(request)
    storage_user_key = auth_routes.get_authenticated_storage_user_key(request)
    if storage_user_key:
        storage.set_current_user(storage_user_key)
        print(
            "[cloud-route] "
            f"username={username!r} "
            f"user_id={storage_user_key!r} "
            f"local_db={str(storage.get_database_path())!r} "
            f"cloud_db_key={f'users/{storage_user_key}/capstone.db'!r} "
            f"project_prefix={f'users/{storage_user_key}/projects/'!r}",
            flush=True,
        )
        return storage_user_key

    raise HTTPException(status_code=401, detail="no authenticated user")


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
            "current_user": storage.get_current_user(),
            "db_path": str(storage.get_database_path()),
        }
    finally:
        conn.close()


@router.post("/db/upload")
def cloud_db_upload(request: Request):
    username = _get_current_username(request)
    return upload_database(username)


@router.post("/db/download")
def cloud_db_download(request: Request):
    username = _get_current_username(request)
    return download_database(username)


@router.post("/projects/download-all")
def cloud_projects_download_all(request: Request):
    username = _get_current_username(request)
    return download_all_project_zips(username)


@router.post("/project/upload")
def cloud_project_upload(payload: ProjectZipPayload, request: Request):
    username = _get_current_username(request)

    zip_path = Path(payload.zip_path)
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="zip file not found")

    return upload_project_zip(
        username,
        payload.project_id,
        zip_path,
        payload.filename,
    )


@router.post("/project/download")
def cloud_project_download(payload: ProjectZipPayload, request: Request):
    username = _get_current_username(request)

    target_path = Path(payload.zip_path)
    filename = payload.filename or "project.zip"

    return download_project_zip(
        username,
        payload.project_id,
        target_path,
        filename,
    )