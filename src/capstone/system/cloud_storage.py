import boto3
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from botocore.exceptions import ClientError

import capstone.storage as storage
from capstone import file_store
def _is_sync_allowed_user(user_id: str | None) -> bool:
    return storage.resolve_storage_user_key(user_id) is not None


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
    canonical_user = storage.resolve_storage_user_key(user_id)
    if canonical_user is None:
        raise ValueError("guest mode must not resolve a cloud-backed local user DB")
    previous_user = storage.get_current_user()
    try:
        storage.set_current_user(canonical_user)
        return storage.get_database_path()
    finally:
        storage.set_current_user(previous_user)


def get_cloud_db_key(user_id: str) -> str:
    canonical_user = storage.resolve_storage_user_key(user_id)
    if canonical_user is None:
        raise ValueError("guest mode has no cloud DB key")
    return f"users/{canonical_user}/capstone.db"


def get_cloud_project_key(user_id: str, project_id: str, filename: str = "project.zip") -> str:
    canonical_user = storage.resolve_storage_user_key(user_id)
    if canonical_user is None:
        raise ValueError("guest mode has no cloud project key")
    return f"users/{canonical_user}/projects/{project_id}/{filename}"


def _log_sync_resolution(action: str, *, username: str | None, storage_user_key: str | None) -> None:
    local_db = storage.get_database_path()
    cloud_db = (
        f"users/{storage_user_key}/capstone.db"
        if storage_user_key
        else "(guest-no-cloud)"
    )
    project_prefix = (
        f"users/{storage_user_key}/projects/"
        if storage_user_key
        else "(guest-no-cloud)"
    )
    print(
        "[cloud-sync] "
        f"action={action} "
        f"username={username!r} "
        f"user_id={storage_user_key!r} "
        f"local_db={str(local_db)!r} "
        f"cloud_db_key={cloud_db!r} "
        f"project_prefix={project_prefix!r}",
        flush=True,
    )


def _assert_private_db_path(local_db: Path) -> None:
    normalized = str(local_db).replace("\\", "/").lower()
    if "/data/guest/" in normalized:
        raise RuntimeError(f"authenticated cloud sync resolved guest DB path: {local_db}")


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
    canonical_user = storage.resolve_storage_user_key(user_id)
    if not canonical_user:
        return {"status": "skipped_guest"}
    _log_sync_resolution("upload_database", username=user_id, storage_user_key=canonical_user)
    local_db = get_local_db_path(canonical_user)
    _assert_private_db_path(local_db)

    if not local_db.exists():
        return {"status": "no_local_db"}

    key = get_cloud_db_key(canonical_user)
    upload_file(BUCKET_NAME, key, local_db)

    return {
        "status": "uploaded",
        "key": key,
        "local_db": str(local_db),
    }


def download_database(user_id: str):
    canonical_user = storage.resolve_storage_user_key(user_id)
    if not canonical_user:
        return {"status": "skipped_guest"}
    _log_sync_resolution("download_database", username=user_id, storage_user_key=canonical_user)
    local_db = get_local_db_path(canonical_user)
    _assert_private_db_path(local_db)
    key = get_cloud_db_key(canonical_user)

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
    canonical_user = storage.resolve_storage_user_key(user_id)
    if not canonical_user:
        return {"status": "skipped_guest"}
    _log_sync_resolution("upload_project_zip", username=user_id, storage_user_key=canonical_user)
    local_zip_path = Path(local_zip_path)

    if not local_zip_path.exists():
        return {"status": "no_local_zip"}

    actual_filename = filename or local_zip_path.name
    key = get_cloud_project_key(canonical_user, project_id, actual_filename)

    upload_file(BUCKET_NAME, key, local_zip_path)

    return {
        "status": "uploaded",
        "key": key,
        "local_zip": str(local_zip_path),
    }


def download_project_zip(user_id: str, project_id: str, target_path: Path, filename: str = "project.zip"):
    canonical_user = storage.resolve_storage_user_key(user_id)
    if not canonical_user:
        return {"status": "skipped_guest"}
    _log_sync_resolution("download_project_zip", username=user_id, storage_user_key=canonical_user)
    target_path = Path(target_path)
    key = get_cloud_project_key(canonical_user, project_id, filename)

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
    canonical_user = storage.resolve_storage_user_key(user_id)
    if not canonical_user:
        return {
            "status": "skipped_guest",
            "downloaded_count": 0,
            "skipped_count": 0,
            "downloaded": [],
            "skipped": [],
        }

    _log_sync_resolution("download_all_project_zips", username=user_id, storage_user_key=canonical_user)
    previous_user = storage.get_current_user()
    try:
        storage.set_current_user(canonical_user)
        _assert_private_db_path(storage.get_database_path())
        conn = storage.open_db()
    except Exception:
        storage.set_current_user(previous_user)
        raise

    try:
        return _download_all_project_zips_with_conn(canonical_user, conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        storage.set_current_user(previous_user)


def _download_all_project_zips_with_conn(user_id: str, conn):

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
    existing_upload_ids = {str(row[0]) for row in rows if row and row[0]}

    for upload_id, original_name, file_id, _old_path in rows:
        filename = original_name or "project.zip"
        key = get_cloud_project_key(user_id, upload_id, filename)

        if not object_exists(BUCKET_NAME, key):
            prefix = f"users/{user_id}/projects/{upload_id}/"
            listing = list_objects(BUCKET_NAME, prefix) or {}
            candidates = listing.get("Contents") or []
            if not candidates:
                skipped.append({"project_id": upload_id, "reason": "missing in cloud"})
                continue
            key = str(candidates[0].get("Key") or "")
            if not key:
                skipped.append({"project_id": upload_id, "reason": "invalid cloud key"})
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

    # If cloud has projects not present in local uploads, hydrate them into local DB/files.
    cloud_prefix = f"users/{user_id}/projects/"
    listing = list_objects(BUCKET_NAME, cloud_prefix) or {}
    cloud_objects = listing.get("Contents") or []
    by_project: dict[str, str] = {}
    for obj in cloud_objects:
        key = str(obj.get("Key") or "")
        if not key.startswith(cloud_prefix):
            continue
        suffix = key[len(cloud_prefix):]
        project_id = suffix.split("/", 1)[0].strip()
        if not project_id or project_id in existing_upload_ids:
            continue
        by_project.setdefault(project_id, key)

    for project_id, key in by_project.items():
        filename = Path(key).name or "project.zip"
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            download_file(BUCKET_NAME, key, tmp_path)
            stored = file_store.ensure_file(
                conn,
                tmp_path,
                original_name=filename,
                source="cloud_download_all_recovery",
                upload_id=project_id,
                mime="application/zip",
            )
            downloaded.append(
                {
                    "project_id": project_id,
                    "file_id": stored.get("file_id"),
                    "path": str(stored.get("path") or ""),
                }
            )
            # Run analysis if no snapshot exists yet so the project shows real stats
            existing = conn.execute(
                "SELECT 1 FROM project_analysis WHERE project_id = ? LIMIT 1",
                (project_id,),
            ).fetchone()
            if not existing and stored.get("path"):
                try:
                    from capstone.zip_analyzer import ZipAnalyzer
                    from capstone.config import Preferences
                    from capstone.modes import ModeResolution
                    ZipAnalyzer().analyze(
                        zip_path=Path(stored["path"]),
                        metadata_path=Path("data") / f"{project_id}_metadata.jsonl",
                        summary_path=Path("data") / f"{project_id}_summary.json",
                        mode=ModeResolution(requested="local", resolved="local", reason="cloud_hydrate"),
                        preferences=Preferences(),
                        project_id=project_id,
                        conn=conn,
                    )
                except Exception:
                    pass  # non-fatal; project still shows without stats
        except Exception as exc:
            skipped.append({"project_id": project_id, "reason": f"hydrate_failed:{exc}"})
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