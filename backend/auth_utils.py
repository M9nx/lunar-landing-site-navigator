import hashlib
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


def parse_oauth_state(state: str) -> tuple[str, str]:
    """Return (nonce, redirect_url)."""
    if ":" not in state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    nonce, redirect = state.split(":", 1)
    return nonce, redirect


def build_oauth_state(redirect_url: str) -> str:
    nonce = secrets.token_urlsafe(16)
    return f"{nonce}:{redirect_url}"


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
