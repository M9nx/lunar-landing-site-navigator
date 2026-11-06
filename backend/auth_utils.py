import base64
import hashlib
import hmac
import json
import secrets
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import ApiSession, utcnow

settings = get_settings()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _oauth_state_signature(payload_b64: str) -> str:
    digest = hmac.new(
        settings["session_secret"].encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return digest[:24]


def build_oauth_state(redirect_url: str) -> str:
    nonce = secrets.token_urlsafe(16)
    payload = json.dumps({"n": nonce, "r": redirect_url}, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{payload_b64}.{_oauth_state_signature(payload_b64)}"


def parse_oauth_state(state: str) -> tuple[str, str]:
    """Return (nonce, redirect_url). Verifies HMAC (cookie not required)."""
    if "." not in state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    payload_b64, sig = state.rsplit(".", 1)
    expected = _oauth_state_signature(payload_b64)
    if not secrets.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    pad = "=" * (-len(payload_b64) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload_b64 + pad))
        return str(data["n"]), str(data["r"])
    except (KeyError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc


def oauth_state_valid(state: str, cookie_state: str | None) -> bool:
    """True if signed state verifies, or legacy cookie matches."""
    if cookie_state and secrets.compare_digest(state, cookie_state):
        return True
    try:
        parse_oauth_state(state)
        return True
    except HTTPException:
        return False


def get_session_by_id(db: Session, session_id: str | None) -> ApiSession | None:
    if not session_id:
        return None
    return db.get(ApiSession, session_id)


def require_session(
    db: Annotated[Session, Depends(get_db)],
    signed: Annotated[str | None, Cookie(alias=settings["session_cookie_name"])] = None,
) -> ApiSession:
    session_id = unsign_session_id(signed) if signed else None
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    session.last_seen_at = utcnow()
    db.commit()
    return session


def verify_csrf(request: Request, session: ApiSession) -> None:
    token = request.headers.get("X-CSRF-Token")
    if not token or not secrets.compare_digest(token, session.csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def is_user_approved(login: str) -> bool:
    approved = settings["approved_github_users"]
    if not approved:
        return False
    return login.lower() in approved


def sign_session_id(session_id: str) -> str:
    digest = hashlib.sha256(f"{session_id}:{settings['session_secret']}".encode()).hexdigest()[:16]
    return f"{session_id}.{digest}"


def unsign_session_id(signed: str) -> str | None:
    if "." not in signed:
        return None
    session_id, _sig = signed.rsplit(".", 1)
    expected = sign_session_id(session_id)
    if not secrets.compare_digest(signed, expected):
        return None
    return session_id
