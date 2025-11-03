# capstone/insight_store.py
from __future__ import annotations
import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

# ---------- Data classes ----------
@dataclass(frozen=True)
class Insight:
    id: str
    title: str
    owner: str
    artefact_uri: Optional[str]
    status: str
    created_at: str
    updated_at: str
    deleted_at: Optional[str]

# ---------- Store ----------
class InsightStore:
    """
    Lightweight SQLite-backed catalog + dependency graph + safe-delete workflow.
    No external libraries; good for unit tests and embedding into a bigger app.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ----- schema -----
    def _init_schema(self) -> None:
        c = self._conn.cursor()
        c.executescript(
            """
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS insights(
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              owner TEXT NOT NULL,
              artefact_uri TEXT,
              status TEXT NOT NULL DEFAULT 'active',
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              deleted_at TEXT
            );

            -- directed edge: from_insight -> to_(insight|file)
            CREATE TABLE IF NOT EXISTS deps(
              from_insight TEXT NOT NULL,
              to_kind TEXT NOT NULL CHECK (to_kind IN ('insight','file')),
              to_id TEXT NOT NULL,
              FOREIGN KEY(from_insight) REFERENCES insights(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_deps_to ON deps(to_kind, to_id);
            CREATE INDEX IF NOT EXISTS idx_deps_from ON deps(from_insight);

            -- optional registry of files we reference
            CREATE TABLE IF NOT EXISTS files(
              file_id TEXT PRIMARY KEY,
              path TEXT NOT NULL,
              hash TEXT
            );

            -- trash keeps a JSON snapshot to support restore
            CREATE TABLE IF NOT EXISTS trash(
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              deleted_at TEXT NOT NULL DEFAULT (datetime('now')),
              deleted_by TEXT
            );

            -- append-only audit log
            CREATE TABLE IF NOT EXISTS audit(
              event_id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL DEFAULT (datetime('now')),
              who TEXT,
              action TEXT NOT NULL,
              target_id TEXT,
              details TEXT
            );
            """
        )
        self._conn.commit()

    # ----- helpers -----
    def _log(self, who: str, action: str, target_id: Optional[str], details: Dict) -> None:
        self._conn.execute(
            "INSERT INTO audit(who, action, target_id, details) VALUES (?,?,?,?)",
            (who, action, target_id, json.dumps(details or {})),
        )
        self._conn.commit()

    # ----- catalog -----
    def create_insight(self, title: str, owner: str, artefact_uri: Optional[str] = None) -> str:
        iid = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO insights(id,title,owner,artefact_uri,status) VALUES (?,?,?,?, 'active')",
            (iid, title, owner, artefact_uri),
        )
        self._conn.commit()
        return iid

    def get_insight(self, iid: str) -> Optional[Insight]:
        r = self._conn.execute("SELECT * FROM insights WHERE id=?", (iid,)).fetchone()
        return Insight(**dict(r)) if r else None

    def list_insights(self, include_deleted: bool = False) -> List[Insight]:
        if include_deleted:
            q = "SELECT * FROM insights"
            rows = self._conn.execute(q).fetchall()
        else:
            q = "SELECT * FROM insights WHERE deleted_at IS NULL"
            rows = self._conn.execute(q).fetchall()
        return [Insight(**dict(r)) for r in rows]

    # ----- dependencies -----
    def add_dep_on_insight(self, from_id: str, to_insight_id: str) -> None:
        self._conn.execute(
            "INSERT INTO deps(from_insight,to_kind,to_id) VALUES (?,?,?)",
            (from_id, "insight", to_insight_id),
        )
        self._conn.commit()

    def add_dep_on_file(self, from_id: str, file_id: str) -> None:
        self._conn.execute(
            "INSERT INTO deps(from_insight,to_kind,to_id) VALUES (?,?,?)",
            (from_id, "file", file_id),
        )
        self._conn.commit()

    def get_dependencies(self, iid: str) -> Dict[str, List[str]]:
        """Return what iid uses."""
        ins = [r["to_id"] for r in self._conn.execute(
            "SELECT to_id FROM deps WHERE from_insight=? AND to_kind='insight'", (iid,)
        ).fetchall()]
        files = [r["to_id"] for r in self._conn.execute(
            "SELECT to_id FROM deps WHERE from_insight=? AND to_kind='file'", (iid,)
        ).fetchall()]
        return {"insights": ins, "files": files}

    def get_dependents(self, iid: str) -> List[str]:
        """Return who uses iid (incoming edges)."""
        rows = self._conn.execute(
            "SELECT from_insight FROM deps WHERE to_kind='insight' AND to_id=?", (iid,)
        ).fetchall()
        return [r["from_insight"] for r in rows]

    def refcount(self, iid: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) AS c FROM deps WHERE to_kind='insight' AND to_id=?", (iid,)
        ).fetchone()["c"]

    def _closure_over_dependents(self, roots: Iterable[str]) -> Set[str]:
        """BFS over incoming edges: everything that *depends on* these roots, including the roots."""
        q: List[str] = list(roots)
        seen: Set[str] = set(q)
        while q:
            x = q.pop(0)
            for d in self.get_dependents(x):
                if d not in seen:
                    seen.add(d)
                    q.append(d)
        return seen

    # ----- safe delete workflow -----
    def dry_run_delete(self, iid: str, strategy: str = "block") -> Dict:
        if self.get_insight(iid) is None:
            return {"ok": False, "reason": "not_found"}

        dependents = self.get_dependents(iid)
        refcount = len(dependents)

        if strategy not in ("block", "cascade"):
            return {"ok": False, "reason": "bad_strategy"}

        if strategy == "block" and refcount > 0:
            return {
                "ok": False,
                "reason": "in_use",
                "refcount": refcount,
                "dependents": dependents,
            }

        if strategy == "cascade":
            to_soft_delete = sorted(self._closure_over_dependents([iid]))
        else:
            to_soft_delete = [iid]

        # Size estimate hook: in a real system sum file sizes; here we just return count
        return {
            "ok": True,
            "plan": {
                "strategy": strategy,
                "targets": to_soft_delete,
                "estimate": {"insight_count": len(to_soft_delete)},
            },
        }

    def soft_delete(self, iid: str, who: str, strategy: str = "block") -> Dict:
        dr = self.dry_run_delete(iid, strategy)
        if not dr.get("ok"):
            return dr

        targets: List[str] = dr["plan"]["targets"]
        # Snapshot payload for each target and store in a single combined record keyed by root (iid)
        snapshot = {
            "insights": [],
            "deps": [],
        }

        # collect insights + deps
        for t in targets:
            r = self._conn.execute("SELECT * FROM insights WHERE id=?", (t,)).fetchone()
            if not r:
                continue
            snapshot["insights"].append(dict(r))

            # outgoing edges from t
            for dep in self._conn.execute("SELECT * FROM deps WHERE from_insight=?", (t,)).fetchall():
                snapshot["deps"].append(dict(dep))

        # write trash snapshot and mark deleted_at
        self._conn.execute(
            "INSERT OR REPLACE INTO trash(id, payload, deleted_by) VALUES (?,?,?)",
            (iid, json.dumps(snapshot), who),
        )
        self._conn.execute(
            "UPDATE insights SET deleted_at=datetime('now'), status='deleted', updated_at=datetime('now') WHERE id IN ({})"
            .format(",".join("?" * len(targets))),
            targets,
        )
        self._log(who, "soft_delete", iid, {"strategy": strategy, "targets": targets})
        self._conn.commit()
        return {"ok": True, "deleted": targets}

    def list_trash(self) -> List[Dict]:
        rows = self._conn.execute("SELECT * FROM trash ORDER BY deleted_at DESC").fetchall()
        return [dict(r) for r in rows]

    def restore(self, root_iid: str, who: str) -> Dict:
        row = self._conn.execute("SELECT * FROM trash WHERE id=?", (root_iid,)).fetchone()
        if not row:
            return {"ok": False, "reason": "not_in_trash"}

        payload = json.loads(row["payload"])
        # restore insights
        for ins in payload.get("insights", []):
            # if insight exists, just clear deleted_at; else recreate
            exists = self._conn.execute("SELECT 1 FROM insights WHERE id=?", (ins["id"],)).fetchone()
            if exists:
                self._conn.execute(
                    "UPDATE insights SET deleted_at=NULL, status='active', updated_at=datetime('now') WHERE id=?",
                    (ins["id"],),
                )
            else:
                self._conn.execute(
                    """INSERT INTO insights(id,title,owner,artefact_uri,status,created_at,updated_at,deleted_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        ins["id"], ins["title"], ins["owner"], ins["artefact_uri"],
                        "active", ins["created_at"], ins["updated_at"], None
                    ),
                )
        # restore deps (idempotent insert by ignoring duplicates)
        for dep in payload.get("deps", []):
            already = self._conn.execute(
                "SELECT 1 FROM deps WHERE from_insight=? AND to_kind=? AND to_id=?",
                (dep["from_insight"], dep["to_kind"], dep["to_id"]),
            ).fetchone()
            if not already:
                self._conn.execute(
                    "INSERT INTO deps(from_insight,to_kind,to_id) VALUES (?,?,?)",
                    (dep["from_insight"], dep["to_kind"], dep["to_id"]),
                )

        self._conn.execute("DELETE FROM trash WHERE id=?", (root_iid,))
        self._log(who, "restore", root_iid, {"restored": True})
        self._conn.commit()
        return {"ok": True, "restored_root": root_iid}

    def purge(self, iid: str, who: str) -> Dict:
        """Hard-delete a single insight (assumes already soft-deleted or truly free)."""
        # integrity: block if any dependents remain undeleted
        if self.refcount(iid) > 0:
            return {"ok": False, "reason": "in_use"}

        self._conn.execute("DELETE FROM deps WHERE from_insight=?", (iid,))
        self._conn.execute("DELETE FROM insights WHERE id=?", (iid,))
        # leave audit trail; trash entry may or may not exist
        self._conn.execute("DELETE FROM trash WHERE id=?", (iid,))
        self._log(who, "purge", iid, {})
        self._conn.commit()
        return {"ok": True}

    def get_audit(self, target_id: Optional[str] = None) -> List[Dict]:
        if target_id:
            rows = self._conn.execute("SELECT * FROM audit WHERE target_id=? ORDER BY event_id", (target_id,)).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM audit ORDER BY event_id").fetchall()
        return [dict(r) for r in rows]
