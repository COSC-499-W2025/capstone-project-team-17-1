import json
from pathlib import Path

import pytest

from capstone.api.portfolio_helpers import (
    ensure_indexes,
    ensure_portfolio_tables,
    get_latest_snapshot,
    get_portfolio_customization,
    list_portfolio_images,
    save_portfolio_image,
    set_cover_portfolio_image,
    delete_portfolio_image,
    upsert_portfolio_customization,
)
from capstone.storage import open_db, close_db, store_analysis_snapshot


@pytest.fixture()
def conn(tmp_path):
    database_dir = tmp_path / "db"
    connection = open_db(database_dir)
    ensure_portfolio_tables(connection)
    ensure_indexes(connection)
    yield connection
    close_db()


def test_get_latest_snapshot_returns_snapshot_dict(conn):
    snapshot = {
        "summary": "Portfolio ready summary",
        "collaboration": {"classification": "individual"},
        "languages": {"Python": 4},
    }

    store_analysis_snapshot(
        conn,
        project_id="demo-project",
        classification="individual",
        primary_contributor="Parsa",
        snapshot=snapshot,
    )

    latest = get_latest_snapshot(conn, "demo-project")

    assert isinstance(latest, dict)
    assert latest["summary"] == "Portfolio ready summary"
    assert latest["collaboration"]["classification"] == "individual"


def test_get_portfolio_customization_returns_defaults_when_missing(conn):
    customization = get_portfolio_customization(conn, "missing-project")

    assert customization["project_id"] == "missing-project"
    assert customization["template_id"] == "classic"
    assert customization["key_role"] == ""
    assert customization["evidence_of_success"] == ""
    assert customization["portfolio_blurb"] == ""


def test_upsert_portfolio_customization_round_trips(conn):
    saved = upsert_portfolio_customization(
        conn,
        "demo-project",
        template_id="case_study",
        key_role="Backend Developer",
        evidence_of_success="Built and tested API routes",
        portfolio_blurb="A backend heavy project for portfolio testing.",
    )

    fetched = get_portfolio_customization(conn, "demo-project")

    assert saved["template_id"] == "case_study"
    assert fetched["template_id"] == "case_study"
    assert fetched["key_role"] == "Backend Developer"
    assert fetched["evidence_of_success"] == "Built and tested API routes"
    assert fetched["portfolio_blurb"] == "A backend heavy project for portfolio testing."


def test_portfolio_image_save_cover_list_and_delete(conn, tmp_path):
    images_base_dir = tmp_path / "images"

    first = save_portfolio_image(
        conn,
        project_id="demo-project",
        filename="cover.png",
        file_bytes=b"fake-image-1",
        images_base_dir=images_base_dir,
        caption="Cover image",
        make_cover=True,
    )

    second = save_portfolio_image(
        conn,
        project_id="demo-project",
        filename="gallery.png",
        file_bytes=b"fake-image-2",
        images_base_dir=images_base_dir,
        caption="Gallery image",
        make_cover=False,
    )

    images = list_portfolio_images(conn, "demo-project")
    assert len(images) == 2
    assert images[0]["is_cover"] is True
    assert images[1]["is_cover"] is False

    updated = set_cover_portfolio_image(
        conn,
        project_id="demo-project",
        image_id=second["id"],
    )
    assert updated is True

    images = list_portfolio_images(conn, "demo-project")
    by_id = {image["id"]: image for image in images}
    assert by_id[first["id"]]["is_cover"] is False
    assert by_id[second["id"]]["is_cover"] is True

    image_path = Path(by_id[first["id"]]["image_path"])
    assert image_path.exists()

    deleted = delete_portfolio_image(
        conn,
        project_id="demo-project",
        image_id=first["id"],
    )
    assert deleted is True
    assert image_path.exists() is False

    remaining = list_portfolio_images(conn, "demo-project")
    assert [image["id"] for image in remaining] == [second["id"]]
