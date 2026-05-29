import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from models.database import get_db, AnalysisRecord
from models.schemas import AnalysisStatus
from routers.analyze import _record_to_response

router = APIRouter()

REPORTS_DIR = os.getenv("REPORTS_DIR", "./reports")


@router.get("/report/{analysis_id}/pdf")
async def download_pdf_report(analysis_id: str, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(404, "Analysis not found")
    if record.status != AnalysisStatus.COMPLETED.value:
        raise HTTPException(400, f"Analysis not complete yet. Status: {record.status}")

    analysis = _record_to_response(record)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, f"{analysis_id}_report.pdf")

    from services.report_generator import generate_pdf_report
    generate_pdf_report(analysis, output_path)

    filename = f"bank_statement_report_{analysis_id[:8]}.pdf"
    return FileResponse(output_path, media_type="application/pdf", filename=filename)


@router.get("/report/{analysis_id}/excel")
async def download_excel_report(analysis_id: str, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(404, "Analysis not found")
    if record.status != AnalysisStatus.COMPLETED.value:
        raise HTTPException(400, f"Analysis not complete yet. Status: {record.status}")

    analysis = _record_to_response(record)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, f"{analysis_id}_report.xlsx")

    from services.report_generator import generate_excel_report
    generate_excel_report(analysis, output_path)

    filename = f"bank_statement_{analysis_id[:8]}.xlsx"
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
