import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from models.database import get_db, AnalysisRecord
from models.schemas import (
    AnalysisResponse, AnalysisStatus, AccountInfo,
    Transaction, AnalyticsResult, QAValidationResult,
)

router = APIRouter()


def _record_to_response(record: AnalysisRecord) -> AnalysisResponse:
    account_info = AccountInfo(**record.account_info) if record.account_info else None

    transactions = None
    if record.transactions:
        transactions = [Transaction(**t) for t in record.transactions]

    analytics = None
    if record.analytics:
        analytics = AnalyticsResult(**record.analytics)

    qa_result = None
    if record.qa_result:
        qa_result = QAValidationResult(**record.qa_result)

    return AnalysisResponse(
        analysis_id=record.id,
        status=AnalysisStatus(record.status),
        account_info=account_info,
        transactions=transactions,
        analytics=analytics,
        qa_result=qa_result,
        error=record.error,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(404, "Analysis not found")
    return _record_to_response(record)


@router.get("/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(404, "Analysis not found")
    return {
        "analysis_id": analysis_id,
        "status": record.status,
        "error": record.error,
        "created_at": record.created_at,
        "completed_at": record.completed_at,
    }
