import os
import boto3
import shutil
from pathlib import Path
from botocore.exceptions import ClientError

import capstone.storage as storage
from capstone import file_store

# credentials set via environment variables for security
ACCOUNT_ID = os.getenv("CLOUDFLARE_R2_ACCOUNT_ID")
ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY")
SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY")

# bucket name set via CLOUDFLARE_R2_BUCKET env var, defaults to "loom-storage" for easier setup
BUCKET_NAME = os.getenv("CLOUDFLARE_R2_BUCKET", "loom-storage")

s3_client = None
# check all required secrets exist before cloud ops to prevent error later
def validate_cloud_config() -> None:
    missing = []
    if not ACCOUNT_ID:
        missing.append("CLOUDFLARE_R2_ACCOUNT_ID")
    if not ACCESS_KEY:
        missing.append("CLOUDFLARE_R2_ACCESS_KEY")
    if not SECRET_KEY:
        missing.append("CLOUDFLARE_R2_SECRET_KEY")
    
    if missing:
        raise RuntimeError(f"Missing required environment variables for cloud storage: {', '.join(missing)}")

# initialize S3 client after validation
def create_client():
    validate_cloud_config()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

# reduce repeat set up 
def get_client():
    global s3_client
    if s3_client is None:
        s3_client = create_client()
    return s3_client

# ------------------------------------------------
# BASIC CLOUD TESTING
# ------------------------------------------------

def test_connection():
    s3 = get_client()
    return s3.list_objects_v2(Bucket=BUCKET_NAME)

def test_upload():
    s3 = get_client()
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
    s3 = get_client()
    s3.delete_object(Bucket=bucket, Key=key)


def upload_file(bucket: str, key: str, local_path: Path):
    s3 = get_client()
    s3.upload_file(str(local_path), bucket, key)


def download_file(bucket: str, key: str, local_path: Path):
    s3 = get_client()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(local_path))


def object_exists(bucket: str, key: str) -> bool:
    s3 = get_client()
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        err_code = e.response.get("Error", {}).get("Code", "")
        if err_code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise   # reraise if unexpected cloud err

def list_objects(bucket: str, prefix: str):
    s3 = get_client()
    return s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

# ------------------------------------------------
# LOCAL PATH HELPERS
# ------------------------------------------------

def get_local_db_path(user_id: str) -> Path:
    previous_user = getattr(storage, "CURRENT_USER", None) # getattr won't assume CURRENT_USER always exists -> returns None if not set
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
    try: 
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
    finally:
        conn.close()
