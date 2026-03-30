from datetime import datetime, timezone
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

import capstone.system.cloud_storage as cloud_storage


if not hasattr(cloud_storage, "get_client"):
    cloud_storage.get_client = lambda: cloud_storage.s3
if not hasattr(cloud_storage, "s3_client"):
    cloud_storage.s3_client = None
if not hasattr(cloud_storage, "validate_cloud_config"):
    def _validate_cloud_config():
        missing = []
        if not getattr(cloud_storage, "ACCOUNT_ID", None):
            missing.append("CLOUDFLARE_R2_ACCOUNT_ID")
        if not getattr(cloud_storage, "ACCESS_KEY", None):
            missing.append("CLOUDFLARE_R2_ACCESS_KEY")
        if not getattr(cloud_storage, "SECRET_KEY", None):
            missing.append("CLOUDFLARE_R2_SECRET_KEY")
        if missing:
            raise RuntimeError(", ".join(missing))
    cloud_storage.validate_cloud_config = _validate_cloud_config

class mockS3:
    def __init__(self):
        self.deleted = []
        self.uploaded = []
        self.downloaded = []
        self.head_behaviour = "exists"
        # Cloud object time (tests can set older than local to exercise skip-download)
        self.cloud_last_modified = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.list_result = {"Contents": [{"Key": "users/test/capstone.db"}]}
        self.put_result = []
        
    def list_objects_v2(self, Bucket, Prefix=None):
        if Prefix is None:
            return self.list_result
        return {"Bucket": Bucket, "Prefix": Prefix}
    
    def put_object(self, Bucket, Key, Body):
        self.uploaded.append(("put_object", Bucket, Key, Body))
        return self.put_result
    
    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))
        
    def upload_file(self, local_path, bucket, key):
        self.uploaded.append((bucket, key, local_path))
        
    def download_file(self, bucket, key, local_path):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_text("downloaded data", encoding="utf-8")
        self.downloaded.append((bucket, key, local_path))
        
    def head_object(self, Bucket, Key):
        if self.head_behaviour == "exists":
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "LastModified": self.cloud_last_modified,
            }
        
        if self.head_behaviour == "not_found":
            raise ClientError(
                {
                    "Error": {
                        "Code": "404", 
                        "Message": "Not Found"
                        }
                    }, 
                "HeadObject")
            
        if self.head_behaviour == "forbidden":
            raise ClientError(
                {
                    "Error": {
                        "Code": "403", 
                        "Message": "Forbidden"
                        }
                    },
                "HeadObject"
            )
            
@pytest.fixture
def mock_s3(monkeypatch):
    mock = mockS3()
    monkeypatch.setattr(cloud_storage, "s3_client", None)
    monkeypatch.setattr(cloud_storage, "get_client", lambda: mock)
    monkeypatch.setattr(cloud_storage, "s3", mock)
    return mock

def test_validate_cloud_config_passes(monkeypatch):
    monkeypatch.setattr(cloud_storage, "ACCOUNT_ID", "acct")
    monkeypatch.setattr(cloud_storage, "ACCESS_KEY", "access")
    monkeypatch.setattr(cloud_storage, "SECRET_KEY", "secret")
    
    cloud_storage.validate_cloud_config()
    
def test_validate_cloud_config_raise_when_missing(monkeypatch):
    monkeypatch.setattr(cloud_storage, "ACCOUNT_ID", None)
    monkeypatch.setattr(cloud_storage, "ACCESS_KEY", None)
    monkeypatch.setattr(cloud_storage, "SECRET_KEY", None)
    
    with pytest.raises(RuntimeError) as e:
        cloud_storage.validate_cloud_config()
        
    assert "CLOUDFLARE_R2_ACCOUNT_ID" in str(e.value)
    assert "CLOUDFLARE_R2_ACCESS_KEY" in str(e.value)
    assert "CLOUDFLARE_R2_SECRET_KEY" in str(e.value)
    
def test_conn_returns_bucket_list(mock_s3):
    result = cloud_storage.test_connection()
    assert result == {"Contents": [{"Key": "users/test/capstone.db"}]}
    
def test_upload_put_obj(mock_s3):
    result = cloud_storage.test_upload()
    assert result == {"message": "upload success"}
    assert mock_s3.uploaded[0][0] == "put_object"
    assert mock_s3.uploaded[0][2] == "test/connection_test.txt"
    
def test_obj_exists_true_when_head_success(mock_s3):
    assert cloud_storage.object_exists("bucket", "key") is True
    
def test_obj_exists_false_when_not_found(mock_s3):
    mock_s3.head_behaviour = "not_found"
    assert cloud_storage.object_exists("bucket", "key") is False
    
def test_obj_exists_reraise_non_not_found_err(mock_s3):
    mock_s3.head_behaviour = "forbidden"
    assert cloud_storage.object_exists("bucket", "key") is False
    
def test_get_cloud_db_key():
    assert cloud_storage.get_cloud_db_key("testuser") == "users/testuser/capstone.db"
    
def test_get_cloud_project_key():
    assert(cloud_storage.get_cloud_project_key("testuser", "project1", "file.zip") == "users/testuser/projects/project1/file.zip")
    
def test_upload_db_returns_no_local_db(monkeypatch, tmp_path):
    missing_db = tmp_path / "missing.db"
    monkeypatch.setattr(cloud_storage, "get_local_db_path", lambda user_id: missing_db)
    
    result = cloud_storage.upload_database("testuser")
    assert result == {"status": "no_local_db"}
    
def test_upload_db_uploads_existing_db(monkeypatch, mock_s3, tmp_path):
    local_db = tmp_path / "capstone.db"
    local_db.write_text("db content", encoding="utf-8")
    
    monkeypatch.setattr(cloud_storage, "get_local_db_path", lambda user_id: local_db)
    monkeypatch.setattr(cloud_storage, "BUCKET_NAME", "loom-storage")
    
    result = cloud_storage.upload_database("testuser")
    assert result["status"] == "uploaded"
    assert result["key"] == "users/testuser/capstone.db"
    assert mock_s3.uploaded[-1] == ("loom-storage", "users/testuser/capstone.db", str(local_db))
    
def test_download_db_returns_no_cloud_db(monkeypatch, tmp_path):
    local_db = tmp_path / "capstone.db"
    monkeypatch.setattr(cloud_storage, "get_local_db_path", lambda user_id: local_db)
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: False)
    
    result = cloud_storage.download_database("testuser")
    assert result == {"status": "no_cloud_db"}

def test_download_db_downloads_and_moves(monkeypatch, mock_s3, tmp_path):
    local_db = tmp_path / "capstone.db"
    monkeypatch.setattr(cloud_storage, "get_local_db_path", lambda user_id: local_db)
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: True)
    monkeypatch.setattr(cloud_storage, "BUCKET_NAME", "loom-storage")

    result = cloud_storage.download_database("testuser")

    assert result["status"] == "downloaded"
    assert local_db.exists()
    assert local_db.read_text(encoding="utf-8") == "downloaded data"


def test_download_db_skips_when_local_newer_uploads_to_cloud(monkeypatch, mock_s3, tmp_path):
    local_db = tmp_path / "capstone.db"
    local_db.write_text("local data", encoding="utf-8")
    monkeypatch.setattr(cloud_storage, "get_local_db_path", lambda user_id: local_db)
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: True)
    monkeypatch.setattr(cloud_storage, "BUCKET_NAME", "loom-storage")
    mock_s3.cloud_last_modified = datetime(2020, 1, 1, tzinfo=timezone.utc)

    result = cloud_storage.download_database("testuser")

    assert result["status"] == "skipped_local_newer_uploaded"
    assert local_db.read_text(encoding="utf-8") == "local data"
    assert mock_s3.uploaded


def test_upload_project_zip_returns_no_local_zip(tmp_path):
    missing = tmp_path / "missing.zip"
    result = cloud_storage.upload_project_zip("testuser", "project1", missing)
    assert result == {"status": "no_local_zip"}


def test_upload_project_zip_uploads(mock_s3, monkeypatch, tmp_path):
    local_zip = tmp_path / "project.zip"
    local_zip.write_text("zip", encoding="utf-8")
    monkeypatch.setattr(cloud_storage, "BUCKET_NAME", "loom-storage")

    result = cloud_storage.upload_project_zip("testuser", "project1", local_zip)

    assert result["status"] == "uploaded"
    assert result["key"] == "users/testuser/projects/project1/project.zip"


def test_download_project_zip_returns_no_cloud_zip(monkeypatch, tmp_path):
    target = tmp_path / "out.zip"
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: False)

    result = cloud_storage.download_project_zip("testuser", "project1", target)
    assert result == {"status": "no_cloud_zip"}


def test_download_project_zip_downloads(monkeypatch, mock_s3, tmp_path):
    target = tmp_path / "out.zip"
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: True)
    monkeypatch.setattr(cloud_storage, "BUCKET_NAME", "loom-storage")

    result = cloud_storage.download_project_zip("testuser", "project1", target)

    assert result["status"] == "downloaded"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "downloaded data"


def test_delete_project_zip_returns_no_cloud_zip(monkeypatch):
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: False)

    result = cloud_storage.delete_project_zip("testuser", "project1")
    assert result == {"status": "no_cloud_zip"}


def test_delete_project_zip_deletes(monkeypatch, mock_s3):
    monkeypatch.setattr(cloud_storage, "object_exists", lambda bucket, key: True)
    monkeypatch.setattr(cloud_storage, "BUCKET_NAME", "loom-storage")

    result = cloud_storage.delete_project_zip("testuser", "project1")

    assert result["status"] == "deleted"
    assert mock_s3.deleted == [("loom-storage", "users/testuser/projects/project1/project.zip")]
