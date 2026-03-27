import os
import sqlite3
import tempfile
from pathlib import Path
from contextlib import contextmanager

from capstone import storage


@contextmanager
def _open_isolated_db(db_dir: Path):
    original_base_dir = storage.BASE_DIR
    original_current_user = storage.CURRENT_USER
    original_loom_db_path = os.environ.pop("LOOM_DB_PATH", None)
    storage.close_db()
    storage.BASE_DIR = db_dir
    storage.CURRENT_USER = None
    conn = storage.open_db(db_dir)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
        storage.close_db()
        storage.BASE_DIR = original_base_dir
        storage.CURRENT_USER = original_current_user
        if original_loom_db_path is not None:
            os.environ["LOOM_DB_PATH"] = original_loom_db_path


def test_users_and_links_schema_and_fk():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            # Tables exist
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "contributors" in tables
            assert "user_projects" in tables
            assert "contributor_stats" in tables
            assert "resumes" in tables
            assert "resume_sections" in tables
            assert "resume_items" in tables
            user_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(contributors)").fetchall()
            }
            assert "full_name" in user_columns
            assert "phone_number" in user_columns
            assert "city" in user_columns
            assert "state_region" in user_columns
            assert "github_url" in user_columns
            assert "portfolio_url" in user_columns
            ordered_columns = [
                row[1] for row in conn.execute("PRAGMA table_info(contributors)").fetchall()
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
            user_id = storage.upsert_contributor(conn, "alice", email="alice@example.com")
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
            assert [tuple(row) for row in links] == [(user_id, "demo", "alice")]

            # FK points to contributors
            fk = conn.execute("PRAGMA foreign_key_list(user_projects)").fetchall()
            assert fk and fk[0][2] == "contributors"


def test_get_and_update_contributor_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            user_id = storage.upsert_contributor(conn, "alice", email="alice@example.com")
            storage.update_contributor_profile(
                conn,
                user_id,
                full_name="Alice Doe",
                phone_number="+1 111-222-3333",
                city="Seattle",
                state_region="WA",
                github_url="https://github.com/alice",
                portfolio_url="https://alice.dev",
            )
            profile = storage.get_contributor_profile(conn, user_id)
            assert profile is not None
            assert profile["full_name"] == "Alice Doe"
            assert profile["phone_number"] == "+1 111-222-3333"
            assert profile["city"] == "Seattle"
            assert profile["state_region"] == "WA"
            assert profile["github_url"] == "https://github.com/alice"
            assert profile["portfolio_url"] == "https://alice.dev"


def test_upsert_contributor_sets_default_github_url():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            user_id = storage.upsert_contributor(conn, "alice", email="alice@example.com")
            row = conn.execute(
                "SELECT github_url FROM contributors WHERE id = ?",
                (user_id,),
            ).fetchone()
            assert row and row[0] == "https://github.com/alice"


def test_upsert_default_resume_modules_creates_default_sections_and_templates():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            user_id = storage.upsert_contributor(conn, "alice", email="alice@example.com")
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
                    "start_date": "Jan 2025",
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
            assert [tuple(row) for row in placeholder_rows] == [("education", "University"), ("experience", "Event")]

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
            assert tuple(project_row) == ("Jan 2025", "Current")


def test_upsert_default_resume_modules_updates_existing_draft_title():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            user_id = storage.upsert_contributor(conn, "alice", email="alice@example.com")
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
        with _open_isolated_db(db_dir) as conn:

            user_id = storage.upsert_contributor(conn, "alice", email="alice@example.com")
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


def test_upsert_contributor_filters_noreply_and_sets_user_id_in_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            uid = storage.upsert_contributor(conn, "boty", email="noreply@github.com")
            assert uid > 0
            row = conn.execute("SELECT email FROM contributors WHERE id = ?", (uid,)).fetchone()
            assert row[0] is None  # noreply stripped

            uid2 = storage.upsert_contributor(conn, "alice", email="alice@example.com")
            storage.store_contributor_stats(
                conn,
                project_id="demo2",
                contributor="alice",
                user_id=uid2,
                commits=1,
            )
            rows = storage.fetch_latest_contributor_stats(conn, "demo2")
            assert rows and rows[0]["user_id"] == uid2


def test_bulk_upsert_contributors_links_projects_and_users():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            class Row:
                def __init__(self, contributor, email=None):
                    self.contributor = contributor
                    self.email = email

            contribs = [Row("alice", "alice@example.com"), Row("bob")]
            storage.bulk_upsert_contributors(conn, "demo-proj", contribs)

            users = conn.execute("SELECT username, email FROM contributors ORDER BY username").fetchall()
            user_rows = [tuple(row) for row in users]
            assert ("alice", "alice@example.com") in user_rows
            assert ("bob", None) in user_rows

            links = conn.execute("SELECT project_id, contributor_name FROM user_projects").fetchall()
            link_rows = [tuple(row) for row in links]
            assert ("demo-proj", "alice") in link_rows
            assert ("demo-proj", "bob") in link_rows


def test_store_contributor_stats_updates_latest_user_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_dir = Path(tmpdir)
        with _open_isolated_db(db_dir) as conn:

            uid1 = storage.upsert_contributor(conn, "alice", email="alice@example.com")
            storage.store_contributor_stats(conn, project_id="demo", contributor="alice", user_id=None, commits=1)
            storage.store_contributor_stats(conn, project_id="demo", contributor="alice", user_id=uid1, commits=2)

            latest = storage.fetch_latest_contributor_stats(conn, "demo")
            assert latest and latest[0]["user_id"] == uid1
            assert latest[0]["commits"] == 2

        conn.close()


# ---------------------------------------------------------------------------
# Education storage (get_user_education / replace_user_education)
# NOTE: storage.open_db() always opens the global production DB regardless of
# the path argument, so each test uses a unique username and clears its own
# data to stay idempotent across repeated runs.
# ---------------------------------------------------------------------------


def _edu_conn_and_uid(username: str, email: str):
    """Open DB, upsert user, clear their education, return (conn, uid)."""
    conn = storage.open_db()
    uid = storage.upsert_contributor(conn, username, email=email)
    storage.replace_user_education(conn, uid, [])  # ensure clean slate
    return conn, uid


def test_get_user_education_returns_empty_after_clear():
    conn, uid = _edu_conn_and_uid("edu_test_empty_user", "edu_empty@test.com")
    try:
        assert storage.get_user_education(conn, uid) == []
    finally:
        storage.replace_user_education(conn, uid, [])
        storage.close_db()


def test_replace_and_get_user_education_round_trip():
    conn, uid = _edu_conn_and_uid("edu_test_rt_user", "edu_rt@test.com")
    try:
        storage.replace_user_education(conn, uid, [{
            "university": "UBCO",
            "degree": "BSc Computer Science",
            "start_date": "2022",
            "end_date": "Present",
            "city": "Kelowna",
            "state": "BC",
        }])
        result = storage.get_user_education(conn, uid)

        assert len(result) == 1
        assert result[0]["university"] == "UBCO"
        assert result[0]["degree"] == "BSc Computer Science"
        assert result[0]["start_date"] == "2022"
        assert result[0]["end_date"] == "Present"
        assert result[0]["city"] == "Kelowna"
        assert result[0]["state"] == "BC"
    finally:
        storage.replace_user_education(conn, uid, [])
        storage.close_db()


def test_replace_user_education_replaces_previous_entries():
    conn, uid = _edu_conn_and_uid("edu_test_rpl_user", "edu_rpl@test.com")
    try:
        storage.replace_user_education(conn, uid, [{"university": "OldU", "degree": "BA Arts"}])
        storage.replace_user_education(conn, uid, [{"university": "NewU", "degree": "MSc CS"}])

        result = storage.get_user_education(conn, uid)
        assert len(result) == 1
        assert result[0]["university"] == "NewU"
    finally:
        storage.replace_user_education(conn, uid, [])
        storage.close_db()


def test_replace_user_education_multiple_entries_preserves_order():
    conn, uid = _edu_conn_and_uid("edu_test_ord_user", "edu_ord@test.com")
    try:
        storage.replace_user_education(conn, uid, [
            {"university": "First", "degree": "BSc"},
            {"university": "Second", "degree": "MSc"},
        ])
        result = storage.get_user_education(conn, uid)

        assert len(result) == 2
        assert result[0]["university"] == "First"
        assert result[1]["university"] == "Second"
    finally:
        storage.replace_user_education(conn, uid, [])
        storage.close_db()


def test_replace_user_education_empty_list_clears_entries():
    conn, uid = _edu_conn_and_uid("edu_test_clr_user", "edu_clr@test.com")
    try:
        storage.replace_user_education(conn, uid, [{"university": "SomeU", "degree": "BSc"}])
        storage.replace_user_education(conn, uid, [])
        assert storage.get_user_education(conn, uid) == []
    finally:
        storage.close_db()


def test_replace_user_education_partial_fields_stored_as_none():
    conn, uid = _edu_conn_and_uid("edu_test_partial_user", "edu_partial@test.com")
    try:
        storage.replace_user_education(conn, uid, [{"university": "UBC"}])
        result = storage.get_user_education(conn, uid)

        assert result[0]["university"] == "UBC"
        assert result[0]["degree"] is None
        assert result[0]["city"] is None
        assert result[0]["state"] is None
    finally:
        storage.replace_user_education(conn, uid, [])
        storage.close_db()


def test_user_education_table_has_required_columns():
    conn = storage.open_db()
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(user_education)").fetchall()}
        for col in ("id", "user_id", "university", "degree", "start_date", "end_date", "city", "state", "sort_order"):
            assert col in columns, f"Missing column: {col}"
    finally:
        storage.close_db()


# ---------------------------------------------------------------------------
# upsert_default_resume_modules — education and summary params
# ---------------------------------------------------------------------------

_HEADER = {
    "full_name": "ResumeTestUser",
    "email": "resume_test@example.com",
    "phone": "123",
    "location": "Kelowna, BC",
    "github_url": "",
    "portfolio_url": "",
}


def test_upsert_default_resume_modules_populates_summary_section():
    conn = storage.open_db()
    try:
        uid = storage.upsert_contributor(conn, "resume_summary_test_user", email="rs_test@example.com")
        resume_id = storage.upsert_default_resume_modules(
            conn,
            user_id=uid,
            header=_HEADER,
            core_skills=["Python"],
            projects=[],
            summary="Computer Science senior at UBCO. Skilled in Python.",
            create_new=True,
        )
        sec = conn.execute(
            "SELECT id FROM resume_sections WHERE resume_id = ? AND key = 'summary'",
            (resume_id,),
        ).fetchone()
        assert sec, "Summary section not created"
        item = conn.execute(
            "SELECT content FROM resume_items WHERE section_id = ?",
            (sec[0],),
        ).fetchone()
        assert item and "UBCO" in item[0]
    finally:
        storage.close_db()


def test_upsert_default_resume_modules_no_summary_uses_empty_template():
    conn = storage.open_db()
    try:
        uid = storage.upsert_contributor(conn, "resume_nosummary_test_user", email="rn_test@example.com")
        resume_id = storage.upsert_default_resume_modules(
            conn, user_id=uid, header=_HEADER, core_skills=[], projects=[],
            summary=None, create_new=True,
        )
        sec = conn.execute(
            "SELECT id FROM resume_sections WHERE resume_id = ? AND key = 'summary'",
            (resume_id,),
        ).fetchone()
        item = conn.execute(
            "SELECT title, content FROM resume_items WHERE section_id = ?",
            (sec[0],),
        ).fetchone()
        assert item is not None
        assert item[0] == "Summary"
    finally:
        storage.close_db()


def test_upsert_default_resume_modules_populates_education_section():
    conn = storage.open_db()
    try:
        uid = storage.upsert_contributor(conn, "resume_edu_test_user", email="re_test@example.com")
        edu = [{"university": "UBCO", "degree": "BSc CS", "start_date": "2022",
                "end_date": "Present", "city": "Kelowna", "state": "BC"}]
        resume_id = storage.upsert_default_resume_modules(
            conn, user_id=uid, header=_HEADER, core_skills=[], projects=[],
            education=edu, create_new=True,
        )
        sec = conn.execute(
            "SELECT id FROM resume_sections WHERE resume_id = ? AND key = 'education'",
            (resume_id,),
        ).fetchone()
        item = conn.execute(
            "SELECT title, subtitle, location FROM resume_items WHERE section_id = ?",
            (sec[0],),
        ).fetchone()
        assert item[0] == "UBCO"
        assert item[1] == "BSc CS"
        assert "Kelowna" in item[2] and "BC" in item[2]
    finally:
        storage.close_db()


def test_upsert_default_resume_modules_education_location_city_state():
    conn = storage.open_db()
    try:
        uid = storage.upsert_contributor(conn, "resume_loc_test_user", email="rl_test@example.com")
        edu = [{"university": "UBC", "degree": "BSc", "city": "Vancouver", "state": "BC"}]
        resume_id = storage.upsert_default_resume_modules(
            conn, user_id=uid, header=_HEADER, core_skills=[], projects=[],
            education=edu, create_new=True,
        )
        sec = conn.execute(
            "SELECT id FROM resume_sections WHERE resume_id = ? AND key = 'education'",
            (resume_id,),
        ).fetchone()
        item = conn.execute(
            "SELECT location FROM resume_items WHERE section_id = ?", (sec[0],)
        ).fetchone()
        assert item[0] == "Vancouver, BC"
    finally:
        storage.close_db()


def test_upsert_default_resume_modules_refreshes_summary_on_regenerate():
    conn = storage.open_db()
    try:
        uid = storage.upsert_contributor(conn, "resume_refresh_test_user", email="rr_test@example.com")
        resume_id = storage.upsert_default_resume_modules(
            conn, user_id=uid, header=_HEADER, core_skills=[], projects=[],
            summary="First summary.", create_new=True,
        )
        # Regenerate: re-uses same draft resume (create_new=False)
        storage.upsert_default_resume_modules(
            conn, user_id=uid, header=_HEADER, core_skills=[], projects=[],
            summary="Updated summary.", create_new=False,
        )
        sec = conn.execute(
            "SELECT id FROM resume_sections WHERE resume_id = ? AND key = 'summary'",
            (resume_id,),
        ).fetchone()
        item = conn.execute(
            "SELECT content FROM resume_items WHERE section_id = ?", (sec[0],)
        ).fetchone()
        assert item[0] == "Updated summary."
    finally:
        storage.close_db()
