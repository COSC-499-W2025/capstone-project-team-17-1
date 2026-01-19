import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
    
from capstone.consent import grant_consent
try:
    from capstone.consent import revoke_consent, export_consent 
except Exception:
    revoke_consent = None
    export_consent = None

from capstone.metrics_extractor import chronological_proj, metrics_api
from capstone.project_ranking import rank_projects_from_snapshots
from capstone.resume_retrieval import build_resume_preview, ensure_resume_schema, query_resume_entries
from capstone.storage import fetch_latest_snapshots, open_db, store_analysis_snapshot
from capstone.top_project_summaries import create_summary_template

def _row_to_dict(row):
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if hasattr(row, "to_dict"):
        try:
            return row.to_dict()
        except Exception:
            pass
    if hasattr(row, "__dict__"):
        return dict(row.__dict__)
    return {"value": row}

def _parse_snapshot_field(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {"raw_snapshot": value}
    return {"raw_snapshot": value}

def _normalize_snapshot(rows):
    normalized = []
    for r in rows or []:
        row_dict = _row_to_dict(r)
        
        pid = (
            row_dict.get("project_id")
            or row_dict.get("projectId")
            or row_dict.get("project")
            or row_dict.get("id_project")
        )
        
        rid = row_dict.get("id") or row_dict.get("row_id") or row_dict.get("snapshot_id")
        uploaded_on = row_dict.get("uploaded_on") or row_dict.get("analyzed_date") or row_dict.get("date")
        snap = row_dict.get("snapshot")
        
        if snap is None and "data" in row_dict and isinstance(row_dict["data"], (dict, str)):
            snap = row_dict["data"]
        snapshot_dict = _parse_snapshot_field(snap)
        
        if pid and "project_id" not in snapshot_dict and "projectId" not in snapshot_dict:
            snapshot_dict["project_id"] = pid
            
        normalized.append({
            "id": rid,
            "project_id": pid,
            "uploaded_on": uploaded_on,
            "snapshot": snapshot_dict,
            "raw": row_dict
         })
    return normalized

def _display_name(item):
    snap = item.get("snapshot") or {}
    pid = item.get("project_id") or snap.get("project_id") or snap.get("projectId")
    
    name = (
        snap.get("project_name")
        or snap.get("projectName")
        or snap.get("name")
        or (snap.get("meta") or {}).get("name")
    )
    return name or pid or "Misc Project"

def _pick_project(normalized, user_input):
    p = (user_input or "").strip().lower()
    if not p:
        return None
    
    # match by project id
    for item in normalized:
        if str(item.get("project_id")) == p:
            return item
    
    return None

def app_main():
    # main entry point for user
    print("=" * 60)
    print("     Data and Artifact Mining Application")
    print("     Portfolio & Resume Generator")
    print("=" * 60)
    print()
    
    if not grant_consent():
        print("Consent is required to proceed. Exiting application.")
        print("Please run program again and provide consent to continue.")
        return
    print("\n Consent granted. Proceeding with analysis...\n")
    
    # main menu loop
    while True:
        print("\n" + "=" * 40)
        print("Main Menu")
        print("=" * 40)
        print("1. Analyze new project archive (ZIP)")
        print("2. View all projects")
        print("3. Vew project details")
        print("4. Generate portfolio summary")
        print("5. Generate resume preview")
        print("6. View chronological project timeline")
        print("7. View skills timeline")
        print("8. Delete project insights")
        print("9. Manage consent")
        print("10. Exit")
        print()
        
        choice = input("Please select an option (1-10): ").strip()
        
        if choice == "1":
            zip_path = input("Please enter the path to the project ZIP archive: ").strip()
            if not zip_path or not os.path.isfile(zip_path):
                print("Invalid file path. Please try again.")
                continue
            with open_db() as conn:
                store_analysis_snapshot(conn, zip_path)
            print("Project analysis completed and stored.")
        elif choice == "2":
            with open_db() as conn:
                rows = fetch_latest_snapshots(conn)
            projects = _normalize_snapshot(rows)
            if not projects:
                print("No projects found. Feel free to upload one!")
                continue
            print("\nProjects:")
            for item in projects:
                name = _display_name(item)
                pid = item.get("project_id") or "N/A"
                rid = item.get("id") or "N/A"
                uploaded = item.get("uploaded_on") or "N/A"
                if rid is not None:
                    print(f"- {name} (project_id: {pid}, row_id: {rid}, uploaded_on: {uploaded}")
                else:
                    print(f"- {name}, (project_id): {pid}, uploaded_on: {uploaded}")
        elif choice == "3":
            to_view = input("Please enter the project_id: ").strip()
            with open_db() as conn:
                rows = fetch_latest_snapshots(conn)
            projects = _normalize_snapshot(rows)
            
            item = _pick_project(projects, to_view)
            if not item:
                print("Project not found :( Please pick option 2 tocheck the project_id and try again.")
                continue
            
            payload = {
                "project_id": item.get("project_id"),
                "row_id": item.get("id"),
                "uploaded_on": item.get("uploaded_on"),
                "snapshot": item.get("snapshot")
            }
            print(json.dumps(payload, indent=4))
        elif choice == "4":
            with open_db() as conn:
                rows = fetch_latest_snapshots(conn)
            projects = _normalize_snapshot(rows)
            
            if not projects:
                print("No projects found to summarize. Please upload some projects first.")
                continue

            snapshot_map = {}
            for item in projects:
                snap = dict(item.get("snapshot") or {})
                pid = (
                    item.get("project_id")
                    or snap.get("project_id")
                    or snap.get("projectId")
                    or f"row_{item.get("id", "unknown")}"
                )
                
                snap.setdefault("project_id", pid)
                
                ts = item.get("uploaded_on") or item.get("uploaded_on")
                if ts:
                    snap.setdefault("analyzed_date", ts)
                    
                old = snapshot_map.get(pid)
                if old is None:
                    snapshot_map[pid] = snap
                else:
                    if (snap.get("analyzed_date") or "") >= (old.get("uploaded_on") or ""):
                        snapshot_map[pid] = snap

            ranked = rank_projects_from_snapshots(snapshot_map)
            
            if not ranked:
                print("No rankable projects found.")
                continue
            
            top = ranked[0]
            top_id = getattr(top, "project_id", None) or top.get("project_id")
            top_snapshot = snapshot_map.get(top_id)
            
            if not top_snapshot:
                print("Could not find snapshot for top project.")
                continue
            
            summary = create_summary_template(top, top_snapshot)

            print("\nPortfolio Summary:\n")
            print(summary)
            
        elif choice == "5":
            with open_db() as conn:
                try:
                    ensure_resume_schema(conn)
                except Exception:
                    pass
                
                # query to build preview similar to what we did in cli.py
                preview_obj = None
                try:
                    result = query_resume_entries(
                        conn, sections=None,
                        keywords=None,
                        start_date=None,
                        end_date=None,
                        include_outdated=False,
                        limit=20,
                        offset=0
                    )
                    preview_obj = build_resume_preview(result, conn=conn)
                except TypeError:
                    preview_obj = build_resume_preview(conn=conn)
                except Exception as e:
                    print(f"Something went wrong when generating resume preview: {e}")
                    continue
                
            print("\nResume Preview:\n")
            if isinstance(preview_obj, (dict, list)):
                print(json.dumps(preview_obj, indent=4))
            else:
                print(preview_obj)
        elif choice == "6":
            with open_db() as conn:
                rows = fetch_latest_snapshots(conn)
            projects = _normalize_snapshot(rows)
            
            if not projects:
                print("No projects found to summarize. Please upload some projects first.")
                continue
            
            all_proj = {}
            
            for item in projects:
                snap = dict(item.get("snapshot") or {})
                pid = (
                       item.get("project_id")
                       or snap.get("project_id")
                       or snap.get("projectId")
                       or f"row_{item.get('id', 'unknown')}"
                )
                ts = item.get("uploaded_on") or item.get("created_at") or snap.get("analyzed_date")
                if ts:
                    snap.setdefault("created_at", ts)
                    
                all_proj[pid] = snap
            
            timeline = chronological_proj(all_proj)
            
            print("\nChronological Project Timeline:\n")
            for proj in timeline:
                name = proj.get("project_name") or "Misc Project"
                start = proj.get("start") or "N/A"
                end = proj.get("end") or "N/A"
                
                if hasattr(start, "isoformat"):
                    start = start.isoformat()
                if hasattr(end, "isoformat"):
                    end = end.isoformat()
                    
                start = start or "N/A"
                end = end or "Present"
                
                print(f"- {name}: {start} to {end}")
        elif choice == "7":
            with open_db() as conn:
                rows = fetch_latest_snapshots(conn)
            projects = _normalize_snapshot(rows)
            
            if not projects:
                print("No projects found to summarize. Please upload some projects first.")
                continue
            
            snapshot_dicts = []
            for item in projects:
                snap = dict(item.get("snapshot") or {})
                snap.setdefault("project_id", item.get("project_id"))
                snap.setdefault("uploaded_on", item.get("uploaded_on"))
                snapshot_dicts.append(snap)
            
            skills = metrics_api(snapshot_dicts)
            
            print("\nSkills Timeline:\n")
            for item in skills or []:
                date = item.get("date") or item.get("uploaded_on") or "N/A"
                name = item.get("skill_name") or item.get("skill") or "Unnamed Skill"
                level = item.get("level")
                if level is None:
                    print(f"- {date}: {name}")
                else:
                    print(f"- {date}: {name} ({level})")
        elif choice == "8":
            to_view = input("Please enter the project_id to delete: ").strip()
            if not to_view:
                print("Invalid project_id. Please try again.")
                continue
            
            confirm_del = input(f"Are you sure you want to delete insights for project_id '{to_view}'? (y/n): ").strip().lower()
            if confirm_del != "y":
                print("Deletion cancelled.")
                continue
            
            deletion = False
            with open_db() as conn:
                cur = conn.cursor()
                
                for table, id_col, pid_col in [
                    ("project_analysis", "id", "project_id"),
                    ("analysis_snapshots", "id", "project_id")
                ]:
                    try:
                        # delete by project_id
                        cur.execute(f"DELETE FROM {table} WHERE {pid_col} = ?", (to_view,))
                        if cur.rowcount:
                            deletion = True
                        conn.commit()
                    except Exception:
                        pass
            if deletion:
                print("Project insights deleted successfully.")
            else:
                print("No insights found for the given project_id. Nothing was deleted.")
        elif choice == "9":
            print("\nConsent Menu:")
            print("1. View Consent Status")
            print("2. Grant Consent")
            print("3. Revoke Consent")
            choice_consent = input("Please select an option (1-3): ").strip()
            
            if choice_consent == "1":
                if export_consent is None:
                    print("Consent functions not available or does not exist.")
                else:
                    try:
                        print(json.dumps(export_consent(), indent=4))
                    except Exception as e:
                        print(f"Could not read consent status: {e}")
            elif choice_consent == "2":
                grant_consent()
                print("Consent granted!")
            elif choice_consent == "3":
                if revoke_consent is None:
                    print("Revoke consent function not available.")
                else:
                    revoke_consent()
                    print("Consent revoked successfully.")
            else:
                print("Invalid choice. Please enter a number between 1 and 3.")
        elif choice == "10":
            print("Good luck with everything! Exiting application.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 10.")
    
if __name__ == "__main__":
    app_main()
    