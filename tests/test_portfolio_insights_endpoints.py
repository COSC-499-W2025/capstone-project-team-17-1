import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from capstone.api.server import create_app
import capstone.storage as storage


def _create_project_analysis_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            classification TEXT,
            primary_contributor TEXT,
            snapshot TEXT NOT NULL,
            zip_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _insert_snapshot(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    snapshot: dict,
    created_at: str,
    classification: str = "individual",
    primary_contributor: str = "alice",
    zip_path: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO project_analysis(project_id, classification, primary_contributor, snapshot, zip_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            classification,
            primary_contributor,
            json.dumps(snapshot),
            zip_path,
            created_at,
        ),
    )
    conn.commit()


@pytest.fixture()
def insights_client(tmp_path: Path):
    db_dir = str(tmp_path)
    original_base_dir = storage.BASE_DIR
    original_current_user = storage.CURRENT_USER
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None

    db_path = tmp_path / "data" / "guest" / "capstone.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        _create_project_analysis_table(conn)

        _insert_snapshot(
            conn,
            project_id="alpha",
            created_at="2026-01-10T00:00:00Z",
            snapshot={
                "summary": "Initial alpha snapshot",
                "skills": [{"skill": "Python", "weight": 0.6}],
                "highlights": ["Initial ingestion flow"],
                "file_summary": {
                    "file_count": 3,
                    "active_days": 2,
                    "daily_timeline": {
                        "2026-01-01": 2,
                        "2026-01-03": 1,
                    },
                },
            },
        )
        _insert_snapshot(
            conn,
            project_id="alpha",
            created_at="2026-02-10T00:00:00Z",
            snapshot={
                "summary": "Expanded alpha snapshot",
                "skills": [{"skill": "Python", "weight": 0.8}, {"skill": "FastAPI", "weight": 0.7}],
                "highlights": ["Added API layer"],
                "file_summary": {
                    "file_count": 9,
                    "active_days": 5,
                    "daily_timeline": {
                        "2026-02-02": 4,
                        "2026-02-04": 3,
                    },
                },
            },
        )
        _insert_snapshot(
            conn,
            project_id="beta",
            created_at="2026-02-12T00:00:00Z",
            snapshot={
                "summary": "Beta snapshot",
                "skills": [{"skill": "SQL", "weight": 0.5}],
                "highlights": ["Reporting support"],
                "file_summary": {
                    "file_count": 4,
                    "active_days": 1,
                    "daily_timeline": {
                        "2026-02-04": 2,
                    },
                },
            },
        )
    finally:
        conn.close()

    app = create_app(db_dir=db_dir, auth_token=None)
    client = TestClient(app)
    try:
        yield client
    finally:
        storage.BASE_DIR = original_base_dir
        storage.CURRENT_USER = original_current_user


def test_portfolio_activity_heatmap_supports_project_and_granularity_filters(insights_client: TestClient):
    response = insights_client.get("/portfolio/activity-heatmap?granularity=month&project_id=alpha")

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None

    data = body["data"]
    assert data["granularity"] == "month"
    assert data["selectedProjectId"] == "alpha"
    assert data["projects"] == ["alpha", "beta"]
    assert [cell["period"] for cell in data["cells"]] == ["2026-02"]
    assert data["projectCount"] == 1
    assert data["cells"][0]["count"] == 7


def test_portfolio_project_evolution_returns_change_focused_steps(insights_client: TestClient):
    response = insights_client.get("/portfolio/project-evolution?project_ids=alpha")

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None

    data = body["data"]["alpha"]
    assert data["snapshotCount"] == 2
    steps = data["steps"]
    assert [step["label"] for step in steps] == ["Baseline", "Current State"]
    assert steps[0]["changeSummary"].startswith("Added 3 files")
    assert "Introduced FastAPI" in steps[1]["changeSummary"]
    assert steps[1]["delta"]["files"] == 6
    assert steps[1]["metrics"]["skills"] == 2


def test_skills_timeline_includes_project_metrics_for_growth_logic(insights_client: TestClient):
    response = insights_client.get("/skills/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3

    first_alpha = next(item for item in body["timeline"] if item["project_id"] == "alpha")
    assert first_alpha["project_metrics"]["file_count"] == 3
    assert first_alpha["project_metrics"]["active_days"] == 2
    assert first_alpha["project_metrics"]["skill_count"] == 1
    assert first_alpha["project_metrics"]["complexity_score"] > 0


def test_skills_timeline_uses_zip_files_and_preserves_unmapped_files(insights_client: TestClient, tmp_path: Path):
    zip_path = tmp_path / "gamma.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("gamma/src/app.py", "print('hello')")
        zf.writestr("gamma/src/routes.ts", "export const routes = [];")
        zf.writestr("gamma/docs/notes.txt", "notes")
        zf.writestr("gamma/assets/logo.bin", "0101")

    conn = storage.open_db()
    try:
        _insert_snapshot(
            conn,
            project_id="gamma",
            created_at="2026-02-15T00:00:00Z",
            snapshot={
                "summary": "Gamma snapshot",
                "skills": [
                    {"skill": "TypeScript", "weight": 0.9},
                ],
                "file_summary": {
                    "file_count": 4,
                    "active_days": 3,
                },
            },
            zip_path=str(zip_path),
        )
    finally:
        conn.close()

    response = insights_client.get("/skills/timeline")

    assert response.status_code == 200
    body = response.json()
    gamma = next(item for item in body["timeline"] if item["project_id"] == "gamma")
    assert gamma["project_metrics"]["skill_count"] == 3
    assert gamma["skills"] == [
        {"skill": "0", "weight": 2.0},
        {"skill": "python", "weight": 1.0},
        {"skill": "typescript", "weight": 1.0},
    ]
