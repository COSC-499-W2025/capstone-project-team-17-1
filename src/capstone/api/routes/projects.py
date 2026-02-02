from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import os
import shutil
import time

router = APIRouter(prefix="/projects", tags=["projects"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_project(file: UploadFile = File(...)):
    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    ts = int(time.time())
    safe_name = f"{ts}_{os.path.basename(filename)}"
    out_path = UPLOAD_DIR / safe_name

    with out_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    project_id = out_path.stem  # filename without .zip
    return {"project_id": project_id, "saved_as": str(out_path)}


@router.get("")
def list_projects():
    """
    Lists uploaded .zip projects.
    """
    zips = sorted(UPLOAD_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "count": len(zips),
        "projects": [
            {
                "project_id": p.stem,
                "filename": p.name,
                "saved_as": str(p),
                "size_bytes": p.stat().st_size,
                "modified": int(p.stat().st_mtime),
            }
            for p in zips
        ],
    }


@router.get("/{project_id}")
def get_project(project_id: str):
    """
    Returns info for a specific uploaded project zip.
    """
    # Find any zip whose stem matches the id
    matches = list(UPLOAD_DIR.glob(f"{project_id}.zip"))
    if not matches:
        # also allow partial match (in case you later change naming)
        matches = list(UPLOAD_DIR.glob(f"*{project_id}*.zip"))

    if not matches:
        raise HTTPException(status_code=404, detail="Project not found")

    p = matches[0]
    return {
        "project_id": p.stem,
        "filename": p.name,
        "saved_as": str(p),
        "size_bytes": p.stat().st_size,
        "modified": int(p.stat().st_mtime),
    }
