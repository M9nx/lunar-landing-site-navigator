import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import ApiSession, CalculationRun

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    expected = settings.get("api_admin_token") or ""
    if not expected or not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Admin token required")


@router.delete("/sessions/{user_login}")
def revoke_api_sessions(
    user_login: str,
    _: None = Depends(require_admin_token),
    db: Session = Depends(get_db),
):
    login = user_login.strip().lower()
    stmt = select(ApiSession.id).where(ApiSession.user_login == login)
    session_ids = list(db.scalars(stmt).all())
    if not session_ids:
        return {"deleted_sessions": 0, "user_login": login}
    db.execute(delete(ApiSession).where(ApiSession.user_login == login))
    db.commit()
    return {"deleted_sessions": len(session_ids), "user_login": login}


@router.delete("/runs/{user_login}")
def purge_user_runs(
    user_login: str,
    _: None = Depends(require_admin_token),
    db: Session = Depends(get_db),
):
    login = user_login.strip().lower()
    stmt = select(CalculationRun.id).where(CalculationRun.user_login == login)
    run_ids = list(db.scalars(stmt).all())
    if not run_ids:
        return {"deleted_runs": 0, "user_login": login}
    db.execute(delete(CalculationRun).where(CalculationRun.user_login == login))
    db.commit()
    return {"deleted_runs": len(run_ids), "user_login": login}
