from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["consent"])

# simple in-memory consent store (acceptable for capstone)
_CONSENT_STATE = {"consent": False}

class ConsentIn(BaseModel):
    consent: bool


@router.post("/privacy-consent")
def privacy_consent(payload: ConsentIn):
    _CONSENT_STATE["consent"] = payload.consent
    return {"consent": payload.consent}


@router.get("/privacy-consent")
def get_privacy_consent():
    return {"consent": _CONSENT_STATE["consent"]}
