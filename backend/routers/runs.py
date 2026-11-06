import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_utils import require_session, verify_csrf
from config import get_settings
from database import get_db
from models import ApiSession, CalculationRun

router = APIRouter(prefix="/runs", tags=["runs"])
settings = get_settings()


class RunCreate(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None


def _serialize(run: CalculationRun) -> dict:
    return {
        "id": run.id,
        "user_login": run.user_login,
        "user_github_id": run.user_github_id,
        "created_at": run.created_at.isoformat(),
        "status": run.status,
        "inputs": run.inputs,
        "result": run.result,
        "uncertainty": run.uncertainty,
        "data_version": run.data_version,
        "calculation_version": run.calculation_version,
        "provenance": run.provenance,
        "error": run.error,
        "duration_ms": run.duration_ms,
    }


@router.get("")
def list_runs(
    session: ApiSession = Depends(require_session),
    db: Session = Depends(get_db),
):
    stmt = (
        select(CalculationRun)
        .where(CalculationRun.user_github_id == session.user_github_id)
        .order_by(CalculationRun.created_at.desc())
        .limit(100)
    )
    rows = db.scalars(stmt).all()
    return {"runs": [_serialize(r) for r in rows]}


@router.get("/{run_id}")
def get_run(
    run_id: str,
    session: ApiSession = Depends(require_session),
    db: Session = Depends(get_db),
):
    run = db.get(CalculationRun, run_id)
    if not run or run.user_github_id != session.user_github_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize(run)


@router.post("")
def create_run(
    request: Request,
    body: RunCreate,
    session: Annotated[ApiSession, Depends(require_session)],
    db: Annotated[Session, Depends(get_db)],
):
    verify_csrf(request, session)
    started = time.perf_counter()
    status_value = body.status or (
        "rejected_not_ready" if not settings["science_calculations_ready"] else "queued"
    )
    run = CalculationRun(
        user_github_id=session.user_github_id,
        user_login=session.user_login,
        status=status_value,
        inputs=body.inputs,
        result=None,
        uncertainty=None,
        data_version=body.inputs.get("data_version"),
        calculation_version=settings["calculation_version"],
        provenance={"note": "stub run; validated geometry not implemented"},
        error=None if status_value != "failed" else "Not implemented",
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return _serialize(run)
