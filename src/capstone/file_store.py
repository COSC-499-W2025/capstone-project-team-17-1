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
from .storage import BASE_DIR  # <-- IMPORTANT

logger = get_logger(__name__)

# Production-safe files root (AppData when frozen)
DEFAULT_FILES_ROOT = BASE_DIR / "data" / "files"
DEFAULT_FILES_ROOT.mkdir(parents=True, exist_ok=True)


def hash_file_stream(path: Path | str, *, chunk_size: int = 64 * 1024) -> Tuple[str, int]:
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


def _storage_path(root: Path, file_hash: str, ext: str = "") -> Path:
    return root / f"{file_hash}{ext}"


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
    root = files_root or DEFAULT_FILES_ROOT
    root.mkdir(parents=True, exist_ok=True)

    file_hash, size_bytes = hash_file_stream(source_path)
    ext = Path(original_name or "").suffix.lower() if original_name else ""
    file_id = file_hash
    effective_upload_id = upload_id or str(uuid.uuid4())

    with conn:
        existing = conn.execute(
            "SELECT file_id, path, size_bytes FROM files WHERE hash = ?",
            (file_hash,),
        ).fetchone()

    if existing:
        existing_id, path_str, stored_size = existing

        if stored_size != size_bytes:
            raise ValueError("Hash collision detected: stored size differs")

        dest_path = Path(path_str) if path_str else _storage_path(root, file_hash, ext)

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

    # Store new blob
    dest_path = _storage_path(root, file_hash, ext)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(".tmp")

    with open(source_path, "rb") as src, open(tmp_path, "wb") as dst:
        shutil.copyfileobj(src, dst, length=64 * 1024)

    os.replace(tmp_path, dest_path)

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
    conn.execute(
        """
        INSERT INTO uploads (upload_id, original_name, uploader, source, hash, file_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (upload_id, original_name, uploader, source, file_hash, file_id),
    )


def open_file(conn: sqlite3.Connection, file_id: str, *, files_root: Path | None = None) -> BinaryIO:
    row = conn.execute(
        "SELECT path FROM files WHERE file_id = ?",
        (file_id,),
    ).fetchone()

    if not row:
        raise FileNotFoundError(f"file_id not found: {file_id}")

    path = Path(row[0])

    if files_root:
        alt_path = _storage_path(files_root, file_id)
        if alt_path.exists():
            path = alt_path

    return open(path, "rb")