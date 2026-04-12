"""Text suggestion endpoint."""

import logging

from fastapi import APIRouter, HTTPException, Request

from dependencies import text_suggester
from middleware.rate_limiter import SUGGEST_LIMIT, limiter
from models.schemas import SuggestRequest, TextSuggestion

logger = logging.getLogger(__name__)

router = APIRouter(tags=["suggestions"])


@router.post("/suggest")
@limiter.limit(SUGGEST_LIMIT)
async def suggest_text(request: Request, req: SuggestRequest) -> TextSuggestion:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text darf nicht leer sein.")

    return await text_suggester.suggest(req.text, req.report_type, req.disorder, req.section)
