"""Text suggestion endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import get_current_user, text_suggester
from middleware.rate_limiter import SUGGEST_LIMIT, limiter
from models.auth import User
from models.schemas import SuggestRequest, TextSuggestion

logger = logging.getLogger(__name__)

router = APIRouter(tags=["suggestions"])


@router.post("/suggest")
@limiter.limit(SUGGEST_LIMIT)
async def suggest_text(
    request: Request,
    req: SuggestRequest,
    _: User = Depends(get_current_user),
) -> TextSuggestion:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text darf nicht leer sein.")

    return await text_suggester.suggest(req.text, req.report_type, req.disorder, req.section)
