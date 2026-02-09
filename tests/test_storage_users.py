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
