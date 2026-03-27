import sqlite3
from unittest.mock import patch

from fastapi.testclient import TestClient

from capstone.api.server import create_app
from capstone import storage
from capstone.api.routes import auth as auth_routes
from capstone.api.server import create_app, get_app_for_tests
from capstone import storage


def _client(tmp_path) -> TestClient:
    storage.close_db()
    storage.BASE_DIR = tmp_path
    storage.CURRENT_USER = None
    auth_routes._SESSIONS.clear()
    app = create_app(db_dir=str(tmp_path), auth_token=None)
    return TestClient(app)


def _isolated_client(tmp_path) -> TestClient:
    """Use get_app_for_tests for proper DB isolation in pytest tmp_path fixtures."""
    app = get_app_for_tests(db_dir=str(tmp_path))
    return TestClient(app)


def test_auth_bootstrap_register_login_logout_flow(tmp_path):
    with patch.object(
        auth_routes,
        "_post_to_auth",
        side_effect=[
            {"user": {"username": "alice", "email": "alice@example.com"}},
            {"user": {"username": "alice", "email": "alice@example.com"}},
        ],
    ):
        client = _client(tmp_path)

        boot = client.get("/auth/bootstrap")
        assert boot.status_code == 200
        assert boot.json()["has_users"] is True
        assert boot.json()["authenticated"] is False

        reg = client.post(
            "/auth/register",
            json={"username": "alice", "password": "secret123", "email": "alice@example.com"},
        )
        assert reg.status_code == 200
        token = reg.json()["token"]
        assert token
        assert reg.json()["user"]["username"] == "alice"

        boot2 = client.get("/auth/bootstrap", headers={"Authorization": f"Bearer {token}"})
        assert boot2.status_code == 200
        assert boot2.json()["has_users"] is True
        assert boot2.json()["authenticated"] is True
        assert boot2.json()["user"]["username"] == "alice"

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["user"]["username"] == "alice"

        out = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert out.status_code == 200

        me_after = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_after.status_code == 401

        login = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
        assert login.status_code == 200
        assert login.json()["user"]["username"] == "alice"


def test_auth_profile_update_and_password_change_persist_to_db(tmp_path):
    post_effects = [
        {"user": {"username": "bob", "email": None}},
        auth_routes.HTTPException(status_code=401, detail="invalid credentials"),
        {"detail": "password updated successfully"},
        {"user": {"username": "bob", "email": "bob@example.com"}},
    ]
    put_response = {
        "user": {
            "username": "bob",
            "email": "bob@example.com",
            "full_name": "Bob Stone",
            "phone_number": "+1-555-000-1111",
            "city": "Seattle",
            "state_region": "WA",
            "github_url": "https://github.com/bob",
            "portfolio_url": "https://bob.dev",
        }
    }

    with patch.object(auth_routes, "_post_to_auth", side_effect=post_effects), patch.object(
        auth_routes, "_put_to_auth", return_value=put_response
    ):
        client = _client(tmp_path)
        reg = client.post("/auth/register", json={"username": "bob", "password": "oldpass1"})
        assert reg.status_code == 200
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        update = client.put(
            "/auth/me",
            headers=headers,
            json={
                "email": "bob@example.com",
                "full_name": "Bob Stone",
                "phone_number": "+1-555-000-1111",
                "city": "Seattle",
                "state_region": "WA",
                "github_url": "https://github.com/bob",
                "portfolio_url": "https://bob.dev",
            },
        )
        assert update.status_code == 200
        body = update.json()["user"]
        assert body["email"] == "bob@example.com"
        assert body["full_name"] == "Bob Stone"
        assert body["city"] == "Seattle"

        bad_pw = client.post(
            "/auth/password",
            headers=headers,
            json={"current_password": "wrong", "new_password": "newpass1"},
        )
        assert bad_pw.status_code == 401

        change_pw = client.post(
            "/auth/password",
            headers=headers,
            json={"current_password": "oldpass1", "new_password": "newpass1"},
        )
        assert change_pw.status_code == 200
        assert change_pw.json()["ok"] is True

        new_login = client.post("/auth/login", json={"username": "bob", "password": "newpass1"})
        assert new_login.status_code == 200
        assert new_login.json()["user"]["username"] == "bob"


def test_auth_me_requires_token(tmp_path):
    client = _client(tmp_path)
    assert client.get("/auth/me").status_code == 401
    assert client.put("/auth/me", json={"full_name": "X"}).status_code == 401
    assert client.post("/auth/password", json={"current_password": "a", "new_password": "b"}).status_code == 401


# ---------------------------------------------------------------------------
# Education API — GET /auth/me/education  &  PUT /auth/me/education
# ---------------------------------------------------------------------------


def _register_and_token(client, username="alice", password="pass1234"):
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["token"]


def test_education_get_requires_auth(tmp_path):
    client = _isolated_client(tmp_path)
    storage.close_db()
    assert client.get("/auth/me/education").status_code == 401


def test_education_put_requires_auth(tmp_path):
    client = _isolated_client(tmp_path)
    storage.close_db()
    assert client.put("/auth/me/education", json=[]).status_code == 401



def test_education_get_and_put_endpoints_return_correct_shape(tmp_path):
    """Smoke-test that get/replace_user_education return the expected field shape.
    Full persistence and ordering is covered in test_storage_users.py.
    """
    from pathlib import Path as _Path
    from capstone import storage as _st

    conn = _st.open_db()
    try:
        uid = _st.upsert_contributor(conn, "edu_shape_smoke_user", email="edu_smoke@example.com")
        # Reset education so the test is idempotent against prior runs
        _st.replace_user_education(conn, uid, [])

        _st.replace_user_education(conn, uid, [{
            "university": "UBCO",
            "degree": "BSc Computer Science",
            "start_date": "2022",
            "end_date": "Present",
            "city": "Kelowna",
            "state": "BC",
        }])
        result = _st.get_user_education(conn, uid)
        assert len(result) == 1
        assert set(result[0].keys()) >= {"id", "university", "degree", "start_date", "end_date", "city", "state"}
        assert result[0]["university"] == "UBCO"
        assert result[0]["city"] == "Kelowna"

        # Cleanup
        _st.replace_user_education(conn, uid, [])
    finally:
        _st.close_db()
