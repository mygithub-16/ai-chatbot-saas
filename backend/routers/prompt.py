from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.auth import get_request_user
from backend.models import User
from backend.prompt_architect import architect as prompt_architect

router = APIRouter(tags=["Prompt Architect"])


class RefinePromptPayload(BaseModel):
    user_raw_input: Optional[str] = Field(
        default=None,
        description="Raw instruction from the business owner. Omit or leave blank to receive default template.",
    )
    business_type: str = Field(
        default="default",
        description="Type of business (e.g. barber, dentist, salon, spa, gym).",
    )
    business_name: Optional[str] = Field(
        default=None,
        description="Trading name of the business — embedded in the output prompt.",
    )


@router.post("/api/refine-prompt")
async def refine_prompt(
    payload: RefinePromptPayload,
    _user: User = Depends(get_request_user),
) -> Dict[str, Any]:
    """
    Convert raw business-owner instructions into a structured system prompt.
    """
    result = await prompt_architect.arefine(
        user_raw_input=payload.user_raw_input,
        business_type=payload.business_type or "default",
        business_name=payload.business_name or "",
    )
    return {
        "ok": True,
        **result.to_dict(),
    }


@router.post("/api/refine-prompt/preview")
async def refine_prompt_preview(
    payload: RefinePromptPayload,
) -> Dict[str, Any]:
    """
    Public preview endpoint — returns structured template.
    """
    result = prompt_architect.build_default(
        business_type=payload.business_type or "default",
        business_name=payload.business_name or "",
    )
    return {
        "ok": True,
        **result.to_dict(),
    }
