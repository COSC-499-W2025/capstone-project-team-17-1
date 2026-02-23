import sqlite3
import tempfile
from pathlib import Path

from capstone import storage


def test_users_and_links_schema_and_fk():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        # Tables exist
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "users" in tables
        assert "user_projects" in tables
        assert "contributor_stats" in tables
        assert "resumes" in tables
        assert "resume_sections" in tables
        assert "resume_items" in tables
        user_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        assert "full_name" in user_columns
        assert "phone_number" in user_columns
        assert "city" in user_columns
        assert "state_region" in user_columns
        assert "github_url" in user_columns
        assert "portfolio_url" in user_columns
        ordered_columns = [
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        ]
        assert ordered_columns == [
            "id",
            "username",
            "email",
            "full_name",
            "phone_number",
            "city",
            "state_region",
            "github_url",
            "portfolio_url",
            "created_at",
            "updated_at",
        ]
        for table_name in ("resumes", "resume_sections", "resume_items"):
            info = {
                row[1]: row
                for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            }
            assert info["created_at"][2] == "TIMESTAMP"
            assert info["updated_at"][2] == "TIMESTAMP"
            assert (info["created_at"][4] or "").upper() == "CURRENT_TIMESTAMP"
            assert (info["updated_at"][4] or "").upper() == "CURRENT_TIMESTAMP"

        # Insert user and contributor stats with user_id
        user_id = storage.upsert_user(conn, "alice", email="alice@example.com")
        storage.store_contributor_stats(
            conn,
            project_id="demo",
            contributor="alice",
            user_id=user_id,
            commits=3,
            pull_requests=1,
        )
        rows = storage.fetch_latest_contributor_stats(conn, "demo")
        assert len(rows) == 1
        assert rows[0]["user_id"] == user_id

        # Link user to project (idempotent)
        storage.link_user_to_project(conn, user_id, "demo", contributor_name="alice")
        storage.link_user_to_project(conn, user_id, "demo", contributor_name="alice")
        links = conn.execute(
            "SELECT user_id, project_id, contributor_name FROM user_projects"
        ).fetchall()
        assert links == [(user_id, "demo", "alice")]

        # FK points to users
        fk = conn.execute("PRAGMA foreign_key_list(user_projects)").fetchall()
        assert fk and fk[0][2] == "users"

        conn.close()


def test_get_and_update_user_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        user_id = storage.upsert_user(conn, "alice", email="alice@example.com")
        storage.update_user_profile(
            conn,
            user_id,
            full_name="Alice Doe",
            phone_number="+1 111-222-3333",
            city="Seattle",
            state_region="WA",
            github_url="https://github.com/alice",
            portfolio_url="https://alice.dev",
        )
        profile = storage.get_user_profile(conn, user_id)
        assert profile is not None
        assert profile["full_name"] == "Alice Doe"
        assert profile["phone_number"] == "+1 111-222-3333"
        assert profile["city"] == "Seattle"
        assert profile["state_region"] == "WA"
        assert profile["github_url"] == "https://github.com/alice"
        assert profile["portfolio_url"] == "https://alice.dev"

        conn.close()


def test_upsert_user_sets_default_github_url():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        user_id = storage.upsert_user(conn, "alice", email="alice@example.com")
        row = conn.execute(
            "SELECT github_url FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        assert row and row[0] == "https://github.com/alice"

        conn.close()


def test_upsert_default_resume_modules_creates_default_sections_and_templates():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        user_id = storage.upsert_user(conn, "alice", email="alice@example.com")
        resume_id = storage.upsert_default_resume_modules(
            conn,
            user_id=user_id,
            header={
                "full_name": "Alice",
                "email": "alice@example.com",
                "phone": "123",
                "location": "Victoria, BC",
                "github_url": "https://github.com/alice",
                "portfolio_url": "https://alice.dev",
            },
            core_skills=["Python", "SQL", "Python"],
            projects=[{
                "title": "Proj A",
                "content": "Built APIs",
                "stack": "Python, FastAPI",
                "start_date": "01 2025",
                "end_date": "Current",
            }],
            resume_title="Generated Resume",
        )
        assert resume_id

        section_rows = conn.execute(
            "SELECT key, sort_order FROM resume_sections WHERE resume_id = ? ORDER BY sort_order",
            (resume_id,),
        ).fetchall()
        assert [row[0] for row in section_rows] == [
            "header",
            "summary",
            "education",
            "experience",
            "core_skill",
            "project",
        ]

        summary_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM resume_items i
            JOIN resume_sections s ON s.id = i.section_id
            WHERE s.resume_id = ? AND s.key = 'summary'
            """,
            (resume_id,),
        ).fetchone()[0]
        assert summary_count == 1

        project_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM resume_items i
            JOIN resume_sections s ON s.id = i.section_id
            WHERE s.resume_id = ? AND s.key = 'project'
            """,
            (resume_id,),
        ).fetchone()[0]
        assert project_count == 1

        placeholder_rows = conn.execute(
            """
            SELECT s.key, i.title
            FROM resume_items i
            JOIN resume_sections s ON s.id = i.section_id
            WHERE s.resume_id = ? AND s.key IN ('education', 'experience')
            ORDER BY s.sort_order
            """,
            (resume_id,),
        ).fetchall()
        assert placeholder_rows == [("education", "University"), ("experience", "Event")]

        project_row = conn.execute(
            """
            SELECT i.start_date, i.end_date
            FROM resume_items i
            JOIN resume_sections s ON s.id = i.section_id
            WHERE s.resume_id = ? AND s.key = 'project'
            ORDER BY i.sort_order, i.id
            LIMIT 1
            """,
            (resume_id,),
        ).fetchone()
        assert project_row == ("01 2025", "Current")

        conn.close()


def test_upsert_default_resume_modules_updates_existing_draft_title():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        user_id = storage.upsert_user(conn, "alice", email="alice@example.com")
        first_id = storage.upsert_default_resume_modules(
            conn,
            user_id=user_id,
            header={
                "full_name": "Alice Doe",
                "email": "alice@example.com",
                "phone": "123",
                "location": "Victoria, BC",
                "github_url": "https://github.com/alice",
                "portfolio_url": "https://alice.dev",
            },
            core_skills=["Python"],
            projects=[{"title": "Proj A", "content": "Built APIs", "stack": "Python"}],
            resume_title="Alice Doe_20260215020305",
        )
        second_id = storage.upsert_default_resume_modules(
            conn,
            user_id=user_id,
            header={
                "full_name": "Alice Doe",
                "email": "alice@example.com",
                "phone": "123",
                "location": "Victoria, BC",
                "github_url": "https://github.com/alice",
                "portfolio_url": "https://alice.dev",
            },
            core_skills=["Python"],
            projects=[{"title": "Proj A", "content": "Built APIs", "stack": "Python"}],
            resume_title="Alice Doe_20260215020406",
        )

        assert first_id == second_id
        row = conn.execute("SELECT title FROM resumes WHERE id = ?", (first_id,)).fetchone()
        assert row and row[0] == "Alice Doe_20260215020406"

        conn.close()


def test_upsert_default_resume_modules_create_new_for_same_user():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        user_id = storage.upsert_user(conn, "alice", email="alice@example.com")
        first_id = storage.upsert_default_resume_modules(
            conn,
            user_id=user_id,
            header={
                "full_name": "Alice Doe",
                "email": "alice@example.com",
                "phone": "123",
                "location": "Victoria, BC",
                "github_url": "https://github.com/alice",
                "portfolio_url": "https://alice.dev",
            },
            core_skills=["Python"],
            projects=[{"title": "Proj A", "content": "Built APIs", "stack": "Python"}],
            resume_title="Alice Doe_20260215020507",
            create_new=True,
        )
        second_id = storage.upsert_default_resume_modules(
            conn,
            user_id=user_id,
            header={
                "full_name": "Alice Doe",
                "email": "alice@example.com",
                "phone": "123",
                "location": "Victoria, BC",
                "github_url": "https://github.com/alice",
                "portfolio_url": "https://alice.dev",
            },
            core_skills=["Python"],
            projects=[{"title": "Proj B", "content": "Built APIs", "stack": "Python"}],
            resume_title="Alice Doe_20260215020608",
            create_new=True,
        )

        assert first_id != second_id
        count = conn.execute(
            "SELECT COUNT(*) FROM resumes WHERE user_id = ? AND status = 'draft'",
            (user_id,),
        ).fetchone()[0]
        assert int(count) == 2

        conn.close()


def test_upsert_user_filters_noreply_and_sets_user_id_in_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        uid = storage.upsert_user(conn, "boty", email="noreply@github.com")
        assert uid > 0
        row = conn.execute("SELECT email FROM users WHERE id = ?", (uid,)).fetchone()
        assert row[0] is None  # noreply stripped

        uid2 = storage.upsert_user(conn, "alice", email="alice@example.com")
        storage.store_contributor_stats(
            conn,
            project_id="demo2",
            contributor="alice",
            user_id=uid2,
            commits=1,
        )
        rows = storage.fetch_latest_contributor_stats(conn, "demo2")
        assert rows and rows[0]["user_id"] == uid2

        conn.close()


def test_upsert_users_from_contributors_links_projects_and_users():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        class Row:
            def __init__(self, contributor, email=None):
                self.contributor = contributor
                self.email = email

        contribs = [Row("alice", "alice@example.com"), Row("bob")]
        storage.upsert_users_from_contributors(conn, "demo-proj", contribs)

        users = conn.execute("SELECT username, email FROM users ORDER BY username").fetchall()
        assert ("alice", "alice@example.com") in users
        assert ("bob", None) in users

        links = conn.execute("SELECT project_id, contributor_name FROM user_projects").fetchall()
        assert ("demo-proj", "alice") in links
        assert ("demo-proj", "bob") in links

        conn.close()


def test_store_contributor_stats_updates_latest_user_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        conn = storage.open_db(db_dir)

        uid1 = storage.upsert_user(conn, "alice", email="alice@example.com")
        storage.store_contributor_stats(conn, project_id="demo", contributor="alice", user_id=None, commits=1)
        storage.store_contributor_stats(conn, project_id="demo", contributor="alice", user_id=uid1, commits=2)

        latest = storage.fetch_latest_contributor_stats(conn, "demo")
        assert latest and latest[0]["user_id"] == uid1
        assert latest[0]["commits"] == 2

        conn.close()
