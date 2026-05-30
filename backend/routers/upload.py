import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from models.database import get_db, AnalysisRecord
from models.schemas import UploadResponse, AnalysisStatus

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/jpg", "image/png",
    "image/tiff", "image/bmp", "image/webp",
}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 50)) * 1024 * 1024
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


async def run_full_analysis(analysis_id: str, file_path: str, bank_name: str):
    """Background task: runs the full 3-pass pipeline."""
    from models.database import SessionLocal
    from services.document_processor import process_document
    from services.ai_extractor import extract_transactions, classify_transactions
    from services.analytics_engine import run_analytics
    from services.qa_validator import run_qa_validation

    db = SessionLocal()
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()

    try:
        # Step 1: Document processing
        record.status = AnalysisStatus.EXTRACTING.value
        db.commit()

        doc_result = process_document(file_path)
        raw_text = doc_result["raw_text"]
        detected_bank = doc_result["bank_name"]
        page_images = doc_result.get("page_images", [])
        record.raw_text = raw_text[:50000]  # Store first 50k chars

        # Step 2: AI extraction — use Vision if images available, else text fallback
        from services.ai_extractor import extract_transactions_vision
        if page_images:
            account_info, transactions = extract_transactions_vision(page_images, detected_bank)
        else:
            account_info, transactions = extract_transactions(raw_text, detected_bank)
        if not transactions:
            raise ValueError("No transactions could be extracted from this document")

        # Two-tier classification: regex (free) + Gemini Flash (free tier)
        # Claude is NOT used here — saved for QA and chatbot only
        from services.transaction_classifier import classify_transactions_hybrid
        transactions = classify_transactions_hybrid(transactions)

        record.account_info = account_info.model_dump()
        record.transactions = [t.model_dump() for t in transactions]

        # Step 3: Analytics
        record.status = AnalysisStatus.ANALYZING.value
        db.commit()

        analytics = run_analytics(transactions, account_info)
        record.analytics = analytics.model_dump()

        # Step 4: QA Validation
        record.status = AnalysisStatus.VALIDATING.value
        db.commit()

        qa_result = run_qa_validation(raw_text, transactions, analytics, account_info)
        record.qa_result = qa_result.model_dump()

        # Done
        record.status = AnalysisStatus.COMPLETED.value
        record.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        record.status = AnalysisStatus.FAILED.value
        record.error = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse)
async def upload_bank_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Validate file type
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB")

    # Save file
    analysis_id = str(uuid.uuid4())
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{analysis_id}{ext}")

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    record = AnalysisRecord(
        id=analysis_id,
        status=AnalysisStatus.PENDING.value,
        filename=file.filename,
        file_path=file_path,
    )
    db.add(record)
    db.commit()

    # Kick off background analysis
    background_tasks.add_task(run_full_analysis, analysis_id, file_path, "Unknown")

    return UploadResponse(
        analysis_id=analysis_id,
        message="File uploaded successfully. Analysis started.",
        status=AnalysisStatus.PENDING,
    )
