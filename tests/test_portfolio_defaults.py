from types import SimpleNamespace

import pytest

from capstone.api.routes import portfolio as portfolio_route


@pytest.fixture(autouse=True)
def no_auth(monkeypatch):
    monkeypatch.setattr(portfolio_route, "_check_auth", lambda request: None)
    monkeypatch.setattr(portfolio_route, "_bind_current_user_from_session", lambda request: None)


@pytest.fixture()
def fake_request(tmp_path):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_dir=str(tmp_path), auth_token=None)))


def test_build_portfolio_blurb_uses_individual_wording():
    snapshot = {
        "title": "Demo Project",
        "frameworks": ["React", "FastAPI"],
        "languages": {"TypeScript": 3, "Python": 4},
        "collaboration": {"classification": "individual"},
    }

    blurb = portfolio_route._build_portfolio_blurb(
        "demo-project",
        snapshot,
        "Full Stack Developer",
    )

    assert "individual" in blurb.lower()
    assert "collaborative" not in blurb.lower()
    assert "react" in blurb.lower() or "fastapi" in blurb.lower()


def test_build_portfolio_blurb_uses_collaborative_wording():
    snapshot = {
        "title": "Team Project",
        "frameworks": ["React"],
        "languages": {"TypeScript": 3},
        "collaboration": {"classification": "collaborative"},
    }

    blurb = portfolio_route._build_portfolio_blurb(
        "team-project",
        snapshot,
        "Frontend Developer",
    )

    assert "collaborative" in blurb.lower()


def test_collect_portfolio_evidence_lines_prefers_structured_and_generated_evidence(monkeypatch):
    monkeypatch.setattr(
        portfolio_route,
        "_extract_evidence",
        lambda snapshot: {
            "items": [
                {"label": "Metric", "value": "95% test pass rate"},
                {"label": "Feedback", "value": "Positive peer review"},
            ]
        },
    )
    monkeypatch.setattr(
        portfolio_route,
        "gather_evidence",
        lambda snapshot: [SimpleNamespace(detail="Merged PR #42 into main")],
    )

    lines = portfolio_route._collect_portfolio_evidence_lines({"title": "Demo"}, limit=4)

    assert lines[0] == "Metric: 95% test pass rate"
    assert lines[1] == "Feedback: Positive peer review"
    assert "Merged PR #42 into main" in lines


def test_build_analysis_defaults_uses_project_role_and_generated_content(monkeypatch):
    monkeypatch.setattr(
        portfolio_route,
        "_extract_evidence",
        lambda snapshot: {"items": [{"label": "Metric", "value": "100 files analyzed"}]},
    )
    monkeypatch.setattr(portfolio_route, "gather_evidence", lambda snapshot: [])

    snapshot = {
        "title": "Capstone",
        "project_role": "Backend Developer",
        "frameworks": ["FastAPI"],
        "languages": {"Python": 10},
        "collaboration": {"classification": "individual", "primary_contributor": "Parsa"},
    }

    defaults = portfolio_route._build_analysis_defaults("capstone", snapshot)

    assert defaults["key_role"] == "Backend Developer"
    assert "Metric: 100 files analyzed" in defaults["evidence_of_success"]
    assert "Capstone" in defaults["portfolio_blurb"]
    assert defaults["portfolio_blurb"]


def test_read_portfolio_entry_prefers_overrides_but_exposes_analysis_defaults(monkeypatch, fake_request):
    monkeypatch.setattr(
        portfolio_route,
        "_resolve_db_dir",
        lambda request: request.app.state.db_dir,
    )

    snapshot = {
        "title": "Capstone",
        "project_role": "Frontend Developer",
        "frameworks": ["React"],
        "languages": {"TypeScript": 8},
        "collaboration": {"classification": "individual"},
    }

    customization = {
        "project_id": "capstone",
        "template_id": "gallery",
        "key_role": "Custom Role",
        "evidence_of_success": "Custom evidence",
        "portfolio_blurb": "Custom blurb",
    }

    class DummySession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(portfolio_route, "_db_session", lambda db_dir: DummySession())
    monkeypatch.setattr(portfolio_route, "ensure_portfolio_tables", lambda conn: None)
    monkeypatch.setattr(portfolio_route, "ensure_indexes", lambda conn: None)
    monkeypatch.setattr(portfolio_route, "helper_get_latest_snapshot", lambda conn, project_id: snapshot)
    monkeypatch.setattr(portfolio_route, "get_portfolio_customization", lambda conn, project_id: customization)
    monkeypatch.setattr(portfolio_route, "list_portfolio_images", lambda conn, project_id: [])

    response = portfolio_route.read_portfolio_entry("capstone", fake_request)
    payload = response["data"]

    assert payload["template_id"] == "gallery"
    assert payload["analysis_defaults"]["key_role"] == "Frontend Developer"
    assert payload["resolved"]["key_role"] == "Custom Role"
    assert payload["resolved"]["evidence_of_success"] == "Custom evidence"
    assert payload["resolved"]["portfolio_blurb"] == "Custom blurb"
