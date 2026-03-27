import gc
import os
import tempfile
from pathlib import Path

import pytest

from capstone import storage

collect_ignore_glob = [
    "frontend/node_modules/*",
    "node_modules/*",
]

# On Windows, SQLite files can remain locked briefly after conn.close() because
# Python hasn't GC'd the connection object yet.  Setting ignore_cleanup_errors
# globally prevents PermissionError [WinError 32] during temp-dir teardown.
_OriginalTemporaryDirectory = tempfile.TemporaryDirectory

class _WindowsSafeTemporaryDirectory(_OriginalTemporaryDirectory):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("ignore_cleanup_errors", True)
        super().__init__(*args, **kwargs)

tempfile.TemporaryDirectory = _WindowsSafeTemporaryDirectory


@pytest.fixture(autouse=True)
def isolated_db():
    """Redirect every test to a fresh isolated temp database.

    Clears LOOM_DB_PATH so get_database_path() doesn't return the debug_db,
    and points storage.BASE_DIR at a per-test temp directory.  Everything is
    restored after the test, regardless of how the test tears itself down.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        original_base_dir = storage.BASE_DIR
        original_current_user = storage.CURRENT_USER
        original_loom_db_path = os.environ.pop("LOOM_DB_PATH", None)

        storage.close_db()
        storage.BASE_DIR = Path(tmpdir)
        storage.CURRENT_USER = None

        yield

        storage.close_db()
        gc.collect()  # ensure SQLite connection objects are released before temp dir cleanup
        storage.BASE_DIR = original_base_dir
        storage.CURRENT_USER = original_current_user
        if original_loom_db_path is not None:
            os.environ["LOOM_DB_PATH"] = original_loom_db_path
