from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Tuple, Dict, Any

from .storage import open_db, fetch_latest_snapshots


def _iter_snapshots(conn) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """
    Yield (project_id, snapshot_dict) using the storage API so we don't depend
    on internal table names or uncommitted transactions.
    """
    rows = fetch_latest_snapshots(conn)
    for rec in rows:
        if isinstance(rec, dict):
            pid = rec.get("project_id")
            snap = rec.get("snapshot")
        else:
            pid = getattr(rec, "project_id", None)
            snap = getattr(rec, "snapshot", None)
        if pid is None or snap is None:
            continue
        if isinstance(snap, str):
            try:
                snap = json.loads(snap)
            except json.JSONDecodeError:
                continue
        if isinstance(snap, dict):
            yield pid, snap


def write_projects_timeline(db_dir: Path | None, out_csv: Path) -> int:
    conn = open_db(db_dir)
    rows: list[Dict[str, Any]] = []
    for pid, snap in _iter_snapshots(conn):
        fs = snap.get("file_summary", {}) or {}
        langs = snap.get("languages", {}) or {}
        frameworks = snap.get("frameworks", []) or []
        collab = snap.get("collaboration", {}) or {}
        rows.append({
            "project_id": pid,
            "first_seen": fs.get("first_modified") or fs.get("earliest_modified") or "",
            "last_seen": fs.get("last_modified") or fs.get("latest_modified") or "",
            "classification": collab.get("classification", "unknown"),
            "primary_contributor": collab.get("primary_contributor") or "",
            "languages": ",".join(sorted(langs.keys())),
            "frameworks": ",".join(frameworks),
            "total_files": fs.get("total_files") or fs.get("count") or "",
            "total_bytes": fs.get("total_bytes") or fs.get("size_bytes") or "",
        })
    rows.sort(key=lambda r: (r["first_seen"], r["project_id"]))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["project_id","first_seen","last_seen","classification","primary_contributor",
                  "languages","frameworks","total_files","total_bytes"]
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    return len(rows)


def write_skills_timeline(db_dir: Path | None, out_csv: Path) -> int:
    conn = open_db(db_dir)
    agg: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for _, snap in _iter_snapshots(conn):
        fs = snap.get("file_summary", {}) or {}
        first = fs.get("first_modified") or fs.get("earliest_modified")
        last  = fs.get("last_modified") or fs.get("latest_modified")
        for s in snap.get("skills", []) or []:
            skill = s.get("skill")
            if not skill:
                continue
            cat = s.get("category", "unspecified")
            try:
                w = float(s.get("score", s.get("weight", 1.0)))
            except (TypeError, ValueError):
                w = 1.0
            key = (skill, cat)
            d = agg.setdefault(key, {
                "skill": skill, "category": cat,
                "first_seen": first or "", "last_seen": last or "",
                "total_weight": 0.0, "count": 0
            })
            if first:
                d["first_seen"] = (min(filter(None, [d["first_seen"], first]))
                                   if d["first_seen"] else first)
            if last:
                d["last_seen"] = (max(filter(None, [d["last_seen"], last]))
                                  if d["last_seen"] else last)
            d["total_weight"] += w
            d["count"] += 1
    rows = sorted(agg.values(), key=lambda r: (r["first_seen"], r["skill"]))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["skill","category","first_seen","last_seen","total_weight","count"])
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    return len(rows)
