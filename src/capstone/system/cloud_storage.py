import boto3
import shutil
from pathlib import Path
from botocore.exceptions import ClientError

import capstone.storage as storage

ACCOUNT_ID = "86d88cc4dc44fe96fa122040e6eff0dd"
ACCESS_KEY = "6616152c724e55cca30ef9a406bb6085"
SECRET_KEY = "fe1279fca06338da7b60eecac66f9489b871d89076f9a296a1c0176be4235807"

BUCKET_NAME = "loom-storage"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)


# ------------------------------------------------
# BASIC CLOUD TESTING
# ------------------------------------------------

def test_connection():
    return s3.list_objects_v2(Bucket=BUCKET_NAME)


def test_upload():
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="test/connection_test.txt",
        Body=b"Cloudflare R2 connection successful",
    )
    return {"message": "upload success"}


# ------------------------------------------------
# GENERIC FILE OPERATIONS
# ------------------------------------------------

def delete_file(bucket: str, key: str):
    s3.delete_object(Bucket=bucket, Key=key)

def upload_file(bucket: str, key: str, local_path: Path):
    s3.upload_file(str(local_path), bucket, key)


def download_file(bucket: str, key: str, local_path: Path):
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(local_path))


def object_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


# ------------------------------------------------
# LOCAL PATH HELPERS
# ------------------------------------------------

def get_local_db_path(user_id: str) -> Path:
    previous_user = storage.CURRENT_USER
    try:
        storage.CURRENT_USER = user_id
        return storage.get_database_path()
    finally:
        storage.CURRENT_USER = previous_user


def get_cloud_db_key(user_id: str) -> str:
    return f"users/{user_id}/capstone.db"


def get_cloud_project_key(user_id: str, project_id: str, filename: str = "project.zip") -> str:
    return f"users/{user_id}/projects/{project_id}/{filename}"


# ------------------------------------------------
# DATABASE SYNC
# ------------------------------------------------

def delete_project_zip(user_id: str, project_id: str, filename: str = "project.zip"):
    key = get_cloud_project_key(user_id, project_id, filename)

    if not object_exists(BUCKET_NAME, key):
        return {"status": "no_cloud_zip"}

    delete_file(BUCKET_NAME, key)

    return {
        "status": "deleted",
        "key": key,
    }

def upload_database(user_id: str):
    local_db = get_local_db_path(user_id)

    if not local_db.exists():
        return {"status": "no_local_db"}

    key = get_cloud_db_key(user_id)
    upload_file(BUCKET_NAME, key, local_db)

    return {
        "status": "uploaded",
        "key": key,
        "local_db": str(local_db),
    }


def download_database(user_id: str):
    local_db = get_local_db_path(user_id)
    key = get_cloud_db_key(user_id)

    if not object_exists(BUCKET_NAME, key):
        return {"status": "no_cloud_db"}

    tmp_path = local_db.with_suffix(".tmp")
    download_file(BUCKET_NAME, key, tmp_path)
    shutil.move(tmp_path, local_db)

    return {
        "status": "downloaded",
        "key": key,
        "local_db": str(local_db),
    }


# ------------------------------------------------
# PROJECT ZIP SYNC
# ------------------------------------------------

def upload_project_zip(user_id: str, project_id: str, local_zip_path: Path, filename: str | None = None):
    local_zip_path = Path(local_zip_path)

    if not local_zip_path.exists():
        return {"status": "no_local_zip"}

    actual_filename = filename or local_zip_path.name
    key = get_cloud_project_key(user_id, project_id, actual_filename)

    upload_file(BUCKET_NAME, key, local_zip_path)

    return {
        "status": "uploaded",
        "key": key,
        "local_zip": str(local_zip_path),
    }


def download_project_zip(user_id: str, project_id: str, target_path: Path, filename: str = "project.zip"):
    target_path = Path(target_path)
    key = get_cloud_project_key(user_id, project_id, filename)

    if not object_exists(BUCKET_NAME, key):
        return {"status": "no_cloud_zip"}

    download_file(BUCKET_NAME, key, target_path)

    return {
        "status": "downloaded",
        "key": key,
        "target_path": str(target_path),
    }