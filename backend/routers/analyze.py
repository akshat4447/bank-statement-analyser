import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, AnalysisRecord
from models.schemas import (
    AnalysisResponse, AnalysisStatus, AccountInfo,
    Transaction, AnalyticsResult, QAValidationResult, LoanAffordability,
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


class LoanSimRequest(BaseModel):
    proposed_emi: float


@router.post("/analysis/{analysis_id}/loan-simulator", response_model=LoanAffordability)
async def loan_simulator(analysis_id: str, req: LoanSimRequest, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record or not record.analytics:
        raise HTTPException(404, "Analysis not found or incomplete")

    an = record.analytics
    cw = an.get("creditworthiness", {})
    income = cw.get("average_monthly_income", 0)
    existing_emi = cw.get("average_monthly_emi", 0)
    current_foir = cw.get("foir")

    total_emi = existing_emi + req.proposed_emi
    new_foir = round(total_emi / income * 100, 1) if income > 0 else 0
    max_safe_emi = max(0, income * 0.5 - existing_emi)
    is_affordable = new_foir <= 50

    def stress_verdict(drop_pct: float) -> str:
        stressed_income = income * (1 - drop_pct / 100)
        stressed_foir = total_emi / stressed_income * 100 if stressed_income > 0 else 999
        return "✅ Affordable" if stressed_foir <= 50 else "⚠️ Borderline" if stressed_foir <= 65 else "❌ Unaffordable"

    return LoanAffordability(
        proposed_emi=req.proposed_emi,
        new_foir=new_foir,
        current_foir=current_foir,
        is_affordable=is_affordable,
        verdict="✅ Affordable — within safe limits" if is_affordable else "❌ Exceeds 50% FOIR threshold",
        stress_10pct=stress_verdict(10),
        stress_20pct=stress_verdict(20),
        stress_30pct=stress_verdict(30),
        max_safe_emi=round(max_safe_emi, 2),
    )


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
