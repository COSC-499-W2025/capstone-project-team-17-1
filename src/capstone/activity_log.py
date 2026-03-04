from datetime import datetime

activity_logs = []

def log_event(level: str, message: str):
    activity_logs.insert(0, {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "level": level,
        "message": message
    })

    # keep only last 200 logs
    if len(activity_logs) > 200:
        activity_logs.pop()