from fastapi import APIRouter
from capstone.activity_log import activity_logs

router = APIRouter()

@router.get("/activity")
def get_activity(limit: int = 50):
    return {
        "count": len(activity_logs),
        "logs": activity_logs[:limit]
    }