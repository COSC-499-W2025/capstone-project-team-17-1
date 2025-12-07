"""
Simple preview runner that shows the same pretty analysis output
as sample_project.py, but without running the full demo suite.
"""

import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from capstone.cli import main
from capstone.config import reset_config
from capstone.consent import grant_consent
from capstone.storage import open_db, close_db
# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sample_project import (
    _banner,
    _section,
    _print_project_summary,
    create_sample_zip,
)

def run_preview(zip_path=None):
    """Generate a pretty analysis preview identical to sample_project.py."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # If user didn't pass a project, create a sample project
        if zip_path is None:
            zip_path = create_sample_zip(tmp)
        else:
            zip_path = Path(zip_path)

        metadata_output = tmp / "meta.jsonl"
        summary_output = tmp / "summary.json"

        _banner("Capstone Analysis Preview")

        print("Input Setup")
        print(f"Zip archive   : {zip_path}")
        print(f"Metadata path : {metadata_output}")
        print(f"Summary path  : {summary_output}")

        # ensure config & consent
        reset_config()
        grant_consent()

        # Run analyzer
        args = [
            "analyze",
            str(zip_path),
            "--metadata-output", str(metadata_output),
            "--summary-output", str(summary_output),
            "--project-id", "preview-project",
            "--db-dir", str(tmp / "db"),
        ]
        rc = main(args)

        if rc != 0:
            print(f"Error running analysis (exit={rc})")
            return

        print("\n--- metadata.jsonl ---")
        print(metadata_output.read_text())

        summary = json.loads(summary_output.read_text())
        summary["project_id"] = "preview-project"

        print()
        _print_project_summary(summary)
        print(f"\nRaw summary JSON written to: {summary_output}")
