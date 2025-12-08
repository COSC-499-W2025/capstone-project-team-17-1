def test_pipeline_smoke():
    from capstone.pipeline import run_full_pipeline

    out = run_full_pipeline(
        company_name="TestCorp",
        company_url=None,
        projects_dir="demo/sample_projects"
    )

    assert "status" in out
    assert out["status"] == "stub"
