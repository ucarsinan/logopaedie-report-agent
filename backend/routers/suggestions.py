"""Text suggestion endpoint."""

from fastapi import APIRouter, HTTPException

from models.schemas import SuggestRequest, TextSuggestion
from dependencies import text_suggester

router = APIRouter(tags=["suggestions"])


@router.post("/suggest")
async def suggest_text(req: SuggestRequest) -> TextSuggestion:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text darf nicht leer sein.")

    try:
        return await text_suggester.suggest(
            req.text, req.report_type, req.disorder, req.section
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
