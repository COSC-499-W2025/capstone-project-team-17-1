from fastapi import APIRouter, HTTPException
from pathlib import Path
import zipfile

router = APIRouter(tags=["skills"])

UPLOAD_DIR = Path("uploads")

EXT_TO_SKILL = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".cpp": "c++",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".md": "markdown",
}

@router.get("/projects/{project_id}/skills")
def skills_for_project(project_id: str):
    # find zip
    matches = list(UPLOAD_DIR.glob(f"{project_id}.zip"))
    if not matches:
        matches = list(UPLOAD_DIR.glob(f"*{project_id}*.zip"))
    if not matches:
        raise HTTPException(status_code=404, detail="Project not found")

    zip_path = matches[0]

    skills = {}
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            suffix = Path(name).suffix.lower()
            if suffix in EXT_TO_SKILL:
                skill = EXT_TO_SKILL[suffix]
                skills[skill] = skills.get(skill, 0) + 1

    return {
        "project_id": zip_path.stem,
        "skills": [{"name": k, "evidence": f"{v} file(s) detected"} for k, v in skills.items()],
    }
