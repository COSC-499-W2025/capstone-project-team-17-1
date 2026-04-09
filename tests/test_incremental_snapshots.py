import time
import unittest

from capstone import storage


class TestIncrementalSnapshots(unittest.TestCase):
    def test_same_project_multiple_snapshots_are_preserved(self):
        conn = storage.open_db()

        try:
            project_id = "p1"

            # Store two snapshots for same project (incremental uploads)
            storage.store_analysis_snapshot(
                conn,
                project_id=project_id,
                classification="unknown",
                primary_contributor=None,
                snapshot={"version": 1, "files": ["a.py"]},
            )

            # ensure created_at difference (sqlite timestamp resolution can be 1s)
            time.sleep(1)

            storage.store_analysis_snapshot(
                conn,
                project_id=project_id,
                classification="unknown",
                primary_contributor=None,
                snapshot={"version": 2, "files": ["a.py", "b.py"]},
            )

            history = storage.fetch_project_snapshot_history(conn, project_id)

            self.assertEqual(len(history), 2)

            # newest-first ordering
            self.assertEqual(history[0]["snapshot"]["version"], 2)
            self.assertEqual(history[1]["snapshot"]["version"], 1)
        finally:
            storage.close_db()
