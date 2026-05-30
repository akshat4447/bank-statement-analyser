import os
import uuid
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from models.database import get_db, AnalysisRecord, SessionLocal
from models.schemas import UploadResponse, AnalysisStatus

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/jpg", "image/png",
    "image/tiff", "image/bmp", "image/webp",
}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", 50)) * 1024 * 1024
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Thread pool for parallel CPU-bound tasks
_executor = ThreadPoolExecutor(max_workers=4)


def _run_qa_background(analysis_id: str, raw_text: str, transactions, analytics, account_info):
    """Runs QA validation in a real background thread — reliable, non-blocking."""
    from services.qa_validator import run_qa_validation
    db = SessionLocal()
    try:
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
        if not record:
            return
        qa_result = run_qa_validation(raw_text, transactions, analytics, account_info)
        record.qa_result = qa_result.model_dump()
        db.commit()
    except Exception as e:
        # Store QA error in record so frontend knows it failed
        db2 = SessionLocal()
        try:
            r = db2.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
            if r:
                r.qa_result = {
                    "overall_confidence": 0, "extraction_accuracy": 0,
                    "calculation_accuracy": 0, "categorization_accuracy": 0,
                    "checks": [], "issues_found": [f"QA validation error: {str(e)}"],
                    "data_quality_grade": "F", "manual_review_required": True,
                    "validated_at": datetime.utcnow().isoformat(),
                }
                db2.commit()
        except Exception:
            pass
        finally:
            db2.close()
    finally:
        db.close()


async def run_full_analysis(analysis_id: str, file_path: str, bank_name: str):
    """
    Optimised pipeline:
    1. Document processing (convert to images)
    2. Parallel Vision extraction (all pages simultaneously)
    3. Gemini classification (single batch call)
    4. Analytics computation
    5. Mark COMPLETED → user sees results immediately
    6. QA validation runs in background (non-blocking)
    """
    from services.document_processor import process_document
    from services.ai_extractor import extract_transactions_vision, extract_transactions
    from services.analytics_engine import run_analytics
    from services.transaction_classifier import classify_transactions_hybrid

    db = SessionLocal()
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()

    try:
        # ── Step 1: Document Processing ──────────────────────────────────────
        record.status = AnalysisStatus.EXTRACTING.value
        db.commit()

        loop = asyncio.get_event_loop()
        doc_result = await loop.run_in_executor(_executor, process_document, file_path)

        raw_text = doc_result["raw_text"]
        page_images = doc_result.get("page_images", [])
        detected_bank = doc_result["bank_name"]
        record.raw_text = raw_text[:50000]

        # ── Step 2: Parallel Vision Extraction ───────────────────────────────
        # All pages processed simultaneously — ~10x faster than sequential
        if page_images:
            account_info, transactions = await loop.run_in_executor(
                _executor, extract_transactions_vision, page_images, detected_bank
            )
        else:
            account_info, transactions = await loop.run_in_executor(
                _executor, extract_transactions, raw_text, detected_bank
            )

        if not transactions:
            raise ValueError("No transactions could be extracted from this document")

        # ── Step 3: Gemini Classification (single batch call) ─────────────────
        record.status = AnalysisStatus.ANALYZING.value
        db.commit()

        transactions = await loop.run_in_executor(
            _executor, classify_transactions_hybrid, transactions
        )

        record.account_info = account_info.model_dump()
        record.transactions = [t.model_dump() for t in transactions]

        # ── Step 4: Analytics ─────────────────────────────────────────────────
        from services.analytics_engine import run_analytics
        analytics = await loop.run_in_executor(
            _executor, run_analytics, transactions, account_info
        )
        record.analytics = analytics.model_dump()

        # ── Step 5: Mark COMPLETED — user sees dashboard immediately ──────────
        record.status = AnalysisStatus.COMPLETED.value
        record.completed_at = datetime.utcnow()
        db.commit()

        # ── Step 6: QA runs in a real daemon thread (guaranteed to execute) ─────
        qa_thread = threading.Thread(
            target=_run_qa_background,
            args=(analysis_id, raw_text, transactions, analytics, account_info),
            daemon=True,
        )
        qa_thread.start()
        # Status stays COMPLETED — user sees dashboard immediately

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
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB")

    analysis_id = str(uuid.uuid4())
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{analysis_id}{ext}")

    with open(file_path, "wb") as f:
        f.write(content)

    record = AnalysisRecord(
        id=analysis_id,
        status=AnalysisStatus.PENDING.value,
        filename=file.filename,
        file_path=file_path,
    )
    db.add(record)
    db.commit()

    background_tasks.add_task(run_full_analysis, analysis_id, file_path, "Unknown")

    return UploadResponse(
        analysis_id=analysis_id,
        message="File uploaded. Analysis started.",
        status=AnalysisStatus.PENDING,
    )
