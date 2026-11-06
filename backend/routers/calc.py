from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth_utils import require_session, verify_csrf
from config import get_settings
from models import ApiSession

router = APIRouter(prefix="/v1", tags=["calculations"])
settings = get_settings()


class CompareRequest(BaseModel):
    site_a: str = Field(..., description="Provisional site identifier")
    site_b: str = Field(..., description="Provisional site identifier")
    utc_time: str = Field(..., description="ISO-8601 UTC timestamp")
    inputs: dict[str, Any] = Field(default_factory=dict)


@router.post("/compare")
def compare_sites(
    request: Request,
    body: CompareRequest,
    session: Annotated[ApiSession, Depends(require_session)],
):
    verify_csrf(request, session)
    if not settings["science_calculations_ready"]:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Validated lunar calculations are not enabled.",
                "science_calculations_ready": False,
                "hint": "Site04 frame mapping and benchmark S04-01 must pass before enabling SCIENCE_CALCULATIONS_READY.",
            },
        )
    raise HTTPException(status_code=501, detail="Calculation pipeline scaffold only; not implemented.")
