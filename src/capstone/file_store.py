"""Content-addressable file storage utilities for deduped uploads."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import BinaryIO, Tuple

from .logging_utils import get_logger

logger = get_logger(__name__)

# Default root where file blobs are stored when no bucketed subdirectories are used.
DEFAULT_FILES_ROOT = Path("data") / "files"


def hash_file_stream(path: Path | str, *, chunk_size: int = 64 * 1024) -> Tuple[str, int]:
    """Stream a file to compute sha256 hex digest and size."""
    hasher = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def _storage_path(root: Path, file_hash: str) -> Path:
    """Return flat storage path for a given hash."""
    return root / file_hash


def ensure_file(
    conn: sqlite3.Connection,
    source_path: Path | str,
    *,
    mime: str | None = None,
    original_name: str | None = None,
    uploader: str | None = None,
    source: str | None = None,
    files_root: Path | None = None,
    upload_id: str | None = None,
) -> dict:
    """Ingest a file with deduplication. Returns metadata dict."""
    root = files_root or DEFAULT_FILES_ROOT
    root.mkdir(parents=True, exist_ok=True)

    file_hash, size_bytes = hash_file_stream(source_path)
    file_id = file_hash  # content-addressable

    # Reuse provided upload_id for incremental uploads; otherwise create new
    effective_upload_id = upload_id or str(uuid.uuid4())

    with conn:  # ensures transactional behavior
        existing = conn.execute(
            "SELECT file_id, path, size_bytes FROM files WHERE hash = ?",
            (file_hash,),
        ).fetchone()

    if existing:
        existing_id, path_str, stored_size = existing
        if stored_size != size_bytes:
            raise ValueError("Hash collision detected: stored size differs")

        dest_path = Path(path_str or _storage_path(root, file_hash))

        # If the DB says it exists but file missing, restore it
        if not dest_path.exists():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = dest_path.with_suffix(".tmp")
            with open(source_path, "rb") as src, open(tmp_path, "wb") as dst:
                shutil.copyfileobj(src, dst, length=64 * 1024)
            os.replace(tmp_path, dest_path)

            conn.execute(
                """
                UPDATE files
                SET path = ?, size_bytes = ?, mime = ?, ref_count = ref_count + 1
                WHERE file_id = ?
                """,
                (str(dest_path), size_bytes, mime, existing_id),
            )
        else:
            conn.execute(
                "UPDATE files SET ref_count = ref_count + 1 WHERE file_id = ?",
                (existing_id,),
            )

        _record_upload(
            conn,
            upload_id=effective_upload_id,
            original_name=original_name,
            uploader=uploader,
            source=source,
            file_hash=file_hash,
            file_id=existing_id,
        )

        return {
            "file_id": existing_id,
            "hash": file_hash,
            "path": str(dest_path),
            "size_bytes": size_bytes,
            "dedup": True,
            "upload_id": effective_upload_id,
        }

    # Not deduped: store new blob and insert file row
    dest_path = _storage_path(root, file_hash)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(".tmp")

    with open(source_path, "rb") as src, open(tmp_path, "wb") as dst:
        shutil.copyfileobj(src, dst, length=64 * 1024)
    os.replace(tmp_path, dest_path)  # atomic move

    conn.execute(
        """
        INSERT INTO files (file_id, hash, size_bytes, mime, path, ref_count)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (file_id, file_hash, size_bytes, mime, str(dest_path)),
    )

    _record_upload(
        conn,
        upload_id=effective_upload_id,
        original_name=original_name,
        uploader=uploader,
        source=source,
        file_hash=file_hash,
        file_id=file_id,
    )

    return {
        "file_id": file_id,
        "hash": file_hash,
        "path": str(dest_path),
        "size_bytes": size_bytes,
        "dedup": False,
        "upload_id": effective_upload_id,
    }


def _record_upload(
    conn: sqlite3.Connection,
    *,
    upload_id: str,
    original_name: str | None,
    uploader: str | None,
    source: str | None,
    file_hash: str,
    file_id: str,
) -> None:
    """Insert an upload record (non-destructive)."""
    conn.execute(
        """
        INSERT INTO uploads (upload_id, original_name, uploader, source, hash, file_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (upload_id, original_name, uploader, source, file_hash, file_id),
    )


def open_file(conn: sqlite3.Connection, file_id: str, *, files_root: Path | None = None) -> BinaryIO:
    """Open a stored file by id and return a binary handle."""
    row = conn.execute(
        "SELECT path FROM files WHERE file_id = ?",
        (file_id,),
    ).fetchone()
    if not row:
        raise FileNotFoundError(f"file_id not found: {file_id}")
    path = Path(row[0])
    # allow overriding root to facilitate tests or relocation
    if files_root:
        dest_path = _storage_path(files_root, file_id)
        if dest_path.exists():
            path = dest_path
    return open(path, "rb")


def cleanup_orphans(
    conn: sqlite3.Connection,
    *,
    files_root: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Remove file blobs and DB rows that are no longer referenced.

    Orphan criteria:
      - files.ref_count <= 0, or
      - no matching uploads rows for the file_id.
    Returns {"checked": n, "deleted_rows": x, "deleted_files": y}.
    """
    root = files_root or DEFAULT_FILES_ROOT
    stats = {"checked": 0, "deleted_rows": 0, "deleted_files": 0}

    rows = conn.execute(
        """
        SELECT f.file_id, f.path, f.ref_count,
               (SELECT COUNT(1) FROM uploads u WHERE u.file_id = f.file_id) AS upload_refs
        FROM files f
        """
    ).fetchall()

    for file_id, path_str, ref_count, upload_refs in rows:
        stats["checked"] += 1
        is_orphan = (ref_count or 0) <= 0 or (upload_refs or 0) == 0
        if not is_orphan:
            continue

        dest_path = Path(path_str or _storage_path(root, file_id))
        if not dry_run and dest_path.exists():
            try:
                dest_path.unlink()
                stats["deleted_files"] += 1
            except Exception:
                logger.warning("Failed to delete orphan file %s", dest_path, exc_info=True)

        if not dry_run:
            conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
            stats["deleted_rows"] += 1

    if not dry_run:
        conn.commit()
    return stats