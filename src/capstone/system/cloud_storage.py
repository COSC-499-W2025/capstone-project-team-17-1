import boto3
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from botocore.exceptions import ClientError

import capstone.storage as storage
from capstone import file_store

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


def list_objects(bucket: str, prefix: str):
    return s3.list_objects_v2(Bucket=bucket, Prefix=prefix)


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


def get_local_blob_path(file_id: str, original_name: str | None = None) -> Path:
    ext = Path(original_name or "").suffix.lower()
    return file_store.DEFAULT_FILES_ROOT / f"{file_id}{ext}"


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

    head = s3.head_object(Bucket=BUCKET_NAME, Key=key)
    cloud_modified = head["LastModified"]
    if getattr(cloud_modified, "tzinfo", None) is None:
        cloud_modified = cloud_modified.replace(tzinfo=timezone.utc)

    if local_db.exists():
        local_mtime = datetime.fromtimestamp(local_db.stat().st_mtime, tz=timezone.utc)
        # Local database is newer than cloud backup — do not clobber fresh local data
        # (e.g. new resumes created since last upload). Push local to cloud instead.
        if local_mtime > cloud_modified:
            upload_database(user_id)
            return {
                "status": "skipped_local_newer_uploaded",
                "key": key,
                "local_db": str(local_db),
            }

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


def download_all_project_zips(user_id: str):
    """
    Downloads all project blobs referenced by the user's local capstone.db
    into the current machine's local file store and rewrites files.path.
    """
    conn = storage.open_db()

    rows = conn.execute(
        """
        SELECT u.upload_id, u.original_name, u.file_id, f.path
        FROM uploads u
        JOIN files f ON f.file_id = u.file_id
        ORDER BY datetime(u.created_at) DESC
        """
    ).fetchall()

    downloaded = []
    skipped = []

    for upload_id, original_name, file_id, _old_path in rows:
        filename = original_name or "project.zip"
        key = get_cloud_project_key(user_id, upload_id, filename)

        if not object_exists(BUCKET_NAME, key):
            skipped.append({"project_id": upload_id, "reason": "missing in cloud"})
            continue

        local_blob_path = get_local_blob_path(file_id, filename)
        tmp_path = local_blob_path.with_suffix(local_blob_path.suffix + ".tmp")

        try:
            download_file(BUCKET_NAME, key, tmp_path)
            local_blob_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp_path, local_blob_path)

            conn.execute(
                """
                UPDATE files
                SET path = ?
                WHERE file_id = ?
                """,
                (str(local_blob_path), file_id),
            )

            downloaded.append(
                {
                    "project_id": upload_id,
                    "file_id": file_id,
                    "path": str(local_blob_path),
                }
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    conn.commit()

    return {
        "status": "ok",
        "downloaded_count": len(downloaded),
        "skipped_count": len(skipped),
        "downloaded": downloaded,
        "skipped": skipped,
    }