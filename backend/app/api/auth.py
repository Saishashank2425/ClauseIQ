"""Google Identity Services token verification for ClauseIQ."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class GoogleCredential(BaseModel):
    credential: str


def _client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def verify_google_credential(credential: str) -> dict[str, Any]:
    client_id = _client_id()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured. Set GOOGLE_CLIENT_ID on the server.")
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        payload = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            audience=client_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google credential is invalid or expired.") from exc

    if not payload.get("email") or not payload.get("email_verified"):
        raise HTTPException(status_code=401, detail="A verified Google email is required.")
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name") or payload.get("email", "").split("@")[0],
        "picture": payload.get("picture"),
        "email_verified": True,
    }


@router.get("/config")
def auth_config():
    return {"google_client_id": _client_id(), "google_enabled": bool(_client_id())}


@router.post("/google")
def google_login(body: GoogleCredential):
    return {"user": verify_google_credential(body.credential)}


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in with Google to use this feature.")
    return verify_google_credential(authorization.split(" ", 1)[1].strip())
