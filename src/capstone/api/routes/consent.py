from fastapi import APIRouter
from pydantic import BaseModel
router = APIRouter(tags=["consent"])
class ConsentIn(BaseModel):
    consent: bool
@router.post("/privacy-consent")
def privacy_consent(payload: ConsentIn):
    return {"consent": payload.consent}
