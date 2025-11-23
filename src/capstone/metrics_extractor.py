import os
from pathlib import Path 
from datetime import datetime, timedelta
import sqlite3 


# normalizes file so we can summarize project contribution types
def classify_extensions(ext: str) -> str:
    if not ext:
        return "other"
    ext = ext.lower()
    
    if ext in [".js", ".ts", ".py", ".java", ".cpp", ".c", ".rb", ".go", ".php", ".cs"]:
        return "code"
    if ext in [".md", ".txt", ".rst"]:
        return "doc"
    if ext in [".csv", ".json", ".xml", ".yaml", ".yml"]:
        return "text"
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
        return "graphic"
    return "other"

# calculates time of project
def build_timeline(dates):
    if not dates:
        return {"activityTimeline": [], "periods": {"active": [], "inactive": []}}
    
    days = sorted({d.date() for d in dates})
    first = days[0]
    last = days[-1]
    diff_days = (last - first).days + 1
    
    # store num of contributions for each day
    date_map = {}
    for d in dates:
        key = d.date()
        date_map[key] = date_map.get(key, 0) + 1
    
    # build timeline
    timeline = []
    for i in range(diff_days):
        day = first + timedelta(days = i)
        timeline.append({"date": str(day), "count": date_map.get(day, 0)})
    
    # check for activity periods
    periods = {"active": [], "inactive": []}
    curr_period = None
    for day in timeline:
        is_active = day["count"] > 0
        if not curr_period:
            curr_period = {"type": "active" if is_active else "inactive", "start": day["date"], "end": day["date"]}
            continue
        if (is_active and curr_period["type"] == "active") or (not is_active and curr_period["type"] == "inactive"):
            curr_period["end"] = day["date"]
        else:
            periods[curr_period["type"]].append({"start": curr_period["start"], "end": curr_period["end"]})
            curr_period = {"type": "active" if is_active else "inactive", "start": day["date"], "end": day["date"]}
    
    if curr_period:
        periods[curr_period["type"]].append({"start": curr_period["start"], "end": curr_period["end"]})
        
    return {"activityTimeline": timeline, "periods": periods}
    
# helper to handle invalid int inputs
def handle_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

# helps handle empty contributors
def analyze_metrics(details):
    contributors = details.get("contributorDetails", [])
    ongoing = details.get("ongoing", False) # to check if project is still being worked on
    if not contributors:
        return {
            "summary": {"durationDays": 1, "frequency": 1, "volume": 1},
            "contributionTypes": {},
            "primaryContributors": [],
            "timeLine": {"activityTimeline": [], "periods": {"active": [], "inactive": []}},
            "startDate": None,
            "endDate": None
        }
    
    # loops to process contributors
    all_dates = []
    contribution_types = {"code": 0, "doc": 0, "text": 0, "graphic": 0, "other": 0}
    total_files = 0
    contributor_summary = []
    
    for c in contributors:
        total_files += len(c.get("files", []))
        
        for f in c.get("files", []):
            ext = f.get("extension") or Path(f.get("name", "")).suffix
            f_type = classify_extensions(ext)
            contribution_types[f_type] = contribution_types.get(f_type, 0) + 1
            
            last_modified = f.get("lastModified")
            if isinstance(last_modified, datetime):
                all_dates.append(last_modified)
            
            f["duration"] = handle_int(f.get('duration'))
            f["activity"] = handle_int(f.get('activity'))
            f["contributions"] = handle_int(f.get('contributions'))
                
        contributor_summary.append({"name": c.get("name"), "count": len(c.get("files", []))})
    
    # calculates summary
    if not all_dates:
        return {
            "summary": {"durationDays": 1, "frequency": total_files, "volume": total_files},
            "contributionTypes": contribution_types,
            "primaryContributors": contributor_summary,
            "timeLine": {"activityTimeline": [], "periods": {"active": [], "inactive": []}},
            "start": None,
            "end": None
        }
        
    first = min(all_dates)
    last = max(all_dates)
    duration_days = max(1, (last - first).days + 1)
    frequency = round(total_files / duration_days, 3)
    time_line = build_timeline(all_dates)
    primary_contributors = sorted(contributor_summary, key=lambda x: x["count"], reverse=True)[:5]
    
    end_value = None if ongoing else last
    
    return {
            "summary": {"durationDays": duration_days, "frequency": frequency, "volume": total_files},
            "contributionTypes": contribution_types,
            "primaryContributors": primary_contributors,
            "timeLine": time_line,
            "start": first,
            "end": end_value
    }
        
# initialize db tables
def init_db(db_path = "metrics.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.executescript("""
                         CREATE TABLE IF NOT EXISTS metrics_summary (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             proj_name TEXT,
                             duration_days INTEGER,
                             frequency REAL,
                             volume INTEGER,
                             create_time TEXT DEFAULT CURRENT_TIMESTAMP
                         );
                         CREATE TABLE IF NOT EXISTS metrics_types (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             proj_name TEXT,
                             type TEXT,
                             count INTEGER
                         );
                         CREATE TABLE IF NOT EXISTS metrics_timeline (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             proj_name TEXT,
                             date TEXT,
                             count INTEGER
                         );
                         """)
    conn.commit()
    return conn
    
# insert and save metrics into db
def save_metrics(conn, proj_name, metrics):
    if not conn or not metrics:
        return
    
    summary = metrics["summary"]
    contribution_types = metrics["contributionTypes"]
    timeline = metrics["timeLine"]["activityTimeline"]
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO metrics_summary (proj_name, duration_days, frequency, volume) VALUES (?, ?, ?, ?)",
                   (proj_name, summary["durationDays"], summary["frequency"], summary["volume"]))
    
    for f_type, count in contribution_types.items():
        cursor.execute("INSERT INTO metrics_types (proj_name, type, count) VALUES (?, ?, ?)",
                       (proj_name, f_type, count))
        
    for t in timeline:
        cursor.execute("INSERT INTO metrics_timeline (proj_name, date, count) VALUES (?, ?, ?)",
                       (proj_name, t["date"], t["count"]))
        
    conn.commit()
    
# sort multiple projects by start date and output them in chronological order
def chronological_proj(all_proj: dict) -> list:
    projects = []
    
    # get output info for each proj
    for proj_name, details in all_proj.items():
        metrics = metrics_api(details, proj_name)
        
        # scenario for explicit start/end dates
        start = metrics.get("start")
        end = metrics.get('end')
        
        # scenario for missing date info/ongoing projects
        if start is None:
            time_line = metrics.get("timeLine", {}).get("activityTimeline", [])
            if time_line:
                try:
                    parsed_dates = [
                        datetime.fromisoformat(entry["date"])
                        for entry in time_line
                    ]
                    if parsed_dates:
                        start = min(parsed_dates)
                except Exception:
                    pass # leave start/end as it
        
        projects.append({
            "name": proj_name,
            "start": metrics.get("start"),
            "end": metrics.get("end") # if None prints Present
        })
    
    # sort in order
    projects.sort(key=lambda x: x["start"] if x["start"] else datetime.min, reverse=True) # reverse must be True for latest-oldest
    
    return projects
    
# metrics API
def metrics_api(details, proj_name="UnknownProject", db_path=None):
    metrics = analyze_metrics(details)
    if db_path:
        conn = init_db(db_path)
        save_metrics(conn, proj_name, metrics)
        conn.close()
    return metrics
    
