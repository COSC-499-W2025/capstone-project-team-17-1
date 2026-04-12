import tempfile
from pathlib import Path

from capstone import storage
from capstone.storage import open_db, close_db, store_uploaded_file_bytes


def test_duplicate_upload_reuses_file_and_increments_refcount():
    with tempfile.TemporaryDirectory() as tmp:
        db_dir = Path(tmp) / "db"
        original_base_dir = storage.BASE_DIR
        original_current_user = storage.current_storage_user()
        storage.BASE_DIR = Path(tmp)
        storage._bind_storage_user(None)
        conn = open_db()

        try:
            data = b"same content every time"

            r1 = store_uploaded_file_bytes(
                conn,
                data=data,
                original_name="demo.zip",
                uploader="alice",
                source="api",
                base_dir=db_dir,
                mime="application/zip",
            )
            r2 = store_uploaded_file_bytes(
                conn,
                data=data,
                original_name="demo.zip",
                uploader="alice",
                source="api",
                base_dir=db_dir,
                mime="application/zip",
            )

            # Same hash and same stored file_id => dedup works
            assert r1["hash"] == r2["hash"]
            assert r1["file_id"] == r2["file_id"]

            # Only ONE file row exists
            files_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            assert files_count == 1

            # ref_count increments
            ref_count = conn.execute("SELECT ref_count FROM files WHERE file_id = ?", (r1["file_id"],)).fetchone()[0]
            assert ref_count == 2

            # uploads are recorded twice
            uploads_count = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
            assert uploads_count == 2

        finally:
            close_db()
            storage.BASE_DIR = original_base_dir
            storage._bind_storage_user(original_current_user)
