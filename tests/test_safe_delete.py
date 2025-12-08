# tests/test_safe_delete_unittest.py
import os
import tempfile
import unittest

from capstone.insight_store import InsightStore


class SafeDeleteTests(unittest.TestCase):
    def setUp(self):
        # each test gets its own temp sqlite file
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        self.store = InsightStore(self.db_path)

    def tearDown(self):
        # close DB so Windows can delete the temp file
        try:
            self.store.close()
        finally:
            self.tmpdir.cleanup()


    def test_block_delete_when_in_use(self):
        a = self.store.create_insight("A", "u")
        b = self.store.create_insight("B", "u")
        self.store.add_dep_on_insight(b, a)  # B -> A (A has an incoming edge)

        dr = self.store.dry_run_delete(a, strategy="block")
        self.assertFalse(dr["ok"])
        self.assertEqual(dr["reason"], "in_use")
        self.assertEqual(dr["refcount"], 1)
        self.assertEqual(dr["dependents"], [b])

    def test_cascade_dry_run_lists_closure(self):
        a = self.store.create_insight("A", "u")
        b = self.store.create_insight("B", "u")
        c = self.store.create_insight("C", "u")
        d = self.store.create_insight("D", "u")
        # D -> C -> B -> A (so deleting A with cascade should remove all four)
        self.store.add_dep_on_insight(c, b)
        self.store.add_dep_on_insight(b, a)
        self.store.add_dep_on_insight(d, c)

        dr = self.store.dry_run_delete(a, strategy="cascade")
        self.assertTrue(dr["ok"])
        targets = set(dr["plan"]["targets"])
        self.assertSetEqual(targets, {a, b, c, d})

    def test_soft_delete_and_restore_roundtrip(self):
        root = self.store.create_insight("Root", "me")
        x = self.store.create_insight("X", "me")
        y = self.store.create_insight("Y", "me")
        # X -> Root, Y independent
        self.store.add_dep_on_insight(x, root)

        res = self.store.soft_delete(root, who="tester", strategy="cascade")
        self.assertTrue(res["ok"])
        trash = self.store.list_trash()
        self.assertEqual(len(trash), 1)
        self.assertEqual(trash[0]["id"], root)

        # both root and X should be marked deleted
        for iid in (root, x):
            ins = self.store.get_insight(iid)
            self.assertIsNotNone(ins)
            self.assertIsNotNone(ins.deleted_at)

        rr = self.store.restore(root, who="tester")
        self.assertTrue(rr["ok"])
        self.assertEqual(self.store.list_trash(), [])
        for iid in (root, x):
            ins = self.store.get_insight(iid)
            self.assertIsNotNone(ins)
            self.assertIsNone(ins.deleted_at)

    def test_purge_requires_no_dependents(self):
        a = self.store.create_insight("A", "u")
        b = self.store.create_insight("B", "u")
        self.store.add_dep_on_insight(b, a)

        blocked = self.store.purge(a, who="tester")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["reason"], "in_use")

        # remove dependent first
        self.store.soft_delete(b, who="tester", strategy="block")
        ok = self.store.purge(a, who="tester")
        self.assertTrue(ok["ok"])

    def test_audit_trail(self):
        a = self.store.create_insight("A", "u")
        self.store.soft_delete(a, who="alice", strategy="block")
        self.store.restore(a, who="bob")
        events = self.store.get_audit(target_id=a)
        actions = [e["action"] for e in events]
        self.assertEqual(actions, ["soft_delete", "restore"])


if __name__ == "__main__":
    unittest.main()
