import secrets
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth_utils import (
    build_oauth_state,
    is_user_approved,
    new_csrf_token,
    parse_oauth_state,
    require_session,
    sign_session_id,
    unsign_session_id,
    verify_csrf,
)
from config import get_settings
from database import get_db

settings = get_settings()
from models import ApiSession, utcnow

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "navigator_oauth_state"


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings["session_cookie_name"],
        value=sign_session_id(session_id),
        httponly=True,
        secure=settings["session_cookie_secure"],
        samesite=settings["session_cookie_samesite"],
        path="/",
        max_age=60 * 60 * 24 * 14,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings["session_cookie_name"], path="/")


@router.get("/github/login")
def github_login(
    response: Response,
    redirect: str = Query(default=""),
):
    if not settings["api_github_client_id"]:
        raise HTTPException(status_code=503, detail="API GitHub OAuth is not configured")
    target = redirect or settings["oauth_success_redirect"]
    state = build_oauth_state(target)
    params = {
        "client_id": settings["api_github_client_id"],
        "redirect_uri": f"{settings['api_public_url']}/auth/github/callback",
        "scope": "read:user",
        "state": state,
    }
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=settings["session_cookie_secure"],
        samesite="lax",
        max_age=600,
        path="/",
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{urlencode(params)}")


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
    oauth_state: Annotated[str | None, Cookie(alias=OAUTH_STATE_COOKIE)] = None,
    db: Session = Depends(get_db),
):
    if not code or not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
        raise HTTPException(status_code=400, detail="Invalid OAuth callback")
    if not settings["api_github_client_secret"]:
        raise HTTPException(status_code=503, detail="API GitHub OAuth is not configured")

    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings["api_github_client_id"],
                "client_secret": settings["api_github_client_secret"],
                "code": code,
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub token exchange failed")
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        user_resp.raise_for_status()
        user = user_resp.json()

    login = str(user.get("login", "")).lower()
    github_id = int(user["id"])
    if not is_user_approved(login):
        raise HTTPException(status_code=403, detail="GitHub user is not on the approved list")

    _, redirect_url = parse_oauth_state(state)
    session = ApiSession(
        user_github_id=github_id,
        user_login=login,
        csrf_token=new_csrf_token(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = RedirectResponse(url=redirect_url, status_code=302)
    _set_session_cookie(response, session.id)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return response


@router.get("/me")
def auth_me(session: ApiSession = Depends(require_session)):
    return {
        "user_login": session.user_login,
        "user_github_id": session.user_github_id,
        "authenticated": True,
        "hub_note": "JupyterHub uses a separate GitHub OAuth app and session—not SSO.",
    }


@router.get("/csrf")
def auth_csrf(session: ApiSession = Depends(require_session)):
    return {"csrf_token": session.csrf_token}


@router.post("/logout")
def auth_logout(
    request: Request,
    response: Response,
    session: ApiSession = Depends(require_session),
    db: Session = Depends(get_db),
):
    verify_csrf(request, session)
    db.delete(session)
    db.commit()
    _clear_session_cookie(response)
    return {"status": "logged_out"}


def get_optional_session(
    db: Annotated[Session, Depends(get_db)],
    signed: Annotated[str | None, Cookie(alias=settings["session_cookie_name"])] = None,
) -> ApiSession | None:
    session_id = unsign_session_id(signed) if signed else None
    if not session_id:
        return None
    session = db.get(ApiSession, session_id)
    if session:
        session.last_seen_at = utcnow()
        db.commit()
    return session
