"""PDF export endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from database import get_db
from dependencies import get_current_user
from models.auth import User
from models.report_record import ReportRecord
from services.pdf_generator import generate_pdf

router = APIRouter(tags=["exports"])


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.exec(
        select(ReportRecord).where(ReportRecord.id == report_id, ReportRecord.user_id == current_user.id)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden.")

    content = json.loads(record.content_json)
    pdf_bytes = generate_pdf(content)

    filename = f"bericht_{record.pseudonym}_{record.report_type}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
