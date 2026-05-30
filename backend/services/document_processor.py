"""
Document processor: handles digital PDFs, scanned PDFs, and passbook images.
Uses pdf2image to convert pages to images for Claude Vision extraction.
pdfplumber is kept as fallback for text extraction only.
"""
import os
import re
import base64
import tempfile
from pathlib import Path
from typing import Tuple
from io import BytesIO

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


KNOWN_BANKS = [
    "State Bank of India", "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank",
    "Kotak Mahindra", "Punjab National Bank", "PNB", "Bank of Baroda",
    "Canara Bank", "Union Bank", "IDFC First", "IndusInd Bank",
    "Yes Bank", "Federal Bank", "South Indian Bank", "Bandhan Bank",
    "RBL Bank", "Karnataka Bank", "UCO Bank", "Bank of India",
    "Indian Bank", "Central Bank", "Syndicate Bank", "Vijaya Bank",
]


def detect_bank_name(text: str) -> str:
    text_upper = text.upper()
    for bank in KNOWN_BANKS:
        if bank.upper() in text_upper:
            return bank
    return "Unknown Bank"


def is_scanned_pdf(pdf_path: str) -> bool:
    """Returns True if PDF has little/no extractable text (scanned)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_chars = 0
            pages_checked = min(3, len(pdf.pages))
            for page in pdf.pages[:pages_checked]:
                text = page.extract_text() or ""
                total_chars += len(text.strip())
            # If fewer than 100 chars across first 3 pages, treat as scanned
            return total_chars < 100
    except Exception:
        return True


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Enhance image quality before OCR for better accuracy."""
    # Convert to grayscale
    img = image.convert("L")

    if CV2_AVAILABLE:
        img_array = np.array(img)
        # Deskew using Hough transform approximation
        img_array = cv2.fastNlMeansDenoising(img_array, h=10)
        # Adaptive threshold for better text contrast
        img_array = cv2.adaptiveThreshold(
            img_array, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        img = Image.fromarray(img_array)
    else:
        # Fallback: PIL-based enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

    # Scale up for better OCR (300 DPI equivalent)
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)

    return img


def extract_text_from_digital_pdf(pdf_path: str) -> Tuple[str, list]:
    """
    Extract text from a digital (text-based) PDF using pdfplumber.
    Returns (full_text, list_of_tables_as_text).
    """
    full_text = []
    tables_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            full_text.append(f"--- Page {page_num + 1} ---\n{page_text}")

            # Try table extraction — bank statements are often tabular
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                table_rows = []
                for row in table:
                    cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                    table_rows.append(" | ".join(cleaned_row))
                tables_text.append("\n".join(table_rows))

    return "\n\n".join(full_text), tables_text


def extract_text_from_scanned_pdf(pdf_path: str) -> str:
    """
    Convert scanned PDF pages to images and run OCR on each.
    """
    texts = []
    try:
        images = convert_from_path(pdf_path, dpi=300, fmt="PNG")
        for i, image in enumerate(images):
            preprocessed = preprocess_image_for_ocr(image)
            # Use PSM 6: Assume uniform block of text (good for tables)
            custom_config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz /-.,:|()@"
            text = pytesseract.image_to_string(preprocessed, config=custom_config, lang="eng")
            texts.append(f"--- Page {i + 1} ---\n{text}")
    except Exception as e:
        raise RuntimeError(f"OCR failed: {str(e)}")

    return "\n\n".join(texts)


def extract_text_from_image(image_path: str) -> str:
    """Extract text from a single image file (JPG/PNG passbook photo)."""
    image = Image.open(image_path)
    preprocessed = preprocess_image_for_ocr(image)
    custom_config = r"--oem 3 --psm 6"
    return pytesseract.image_to_string(preprocessed, config=custom_config, lang="eng")


def pdf_pages_to_base64(pdf_path: str, max_pages: int = 15, dpi: int = 150) -> list[str]:
    """
    Convert PDF pages to base64-encoded PNG images for Claude Vision.
    Lower DPI (150) keeps image size manageable while remaining readable.
    Returns list of base64 strings, one per page.
    """
    images = convert_from_path(pdf_path, dpi=dpi, fmt="PNG")
    result = []
    for img in images[:max_pages]:
        # Resize if too large (max 1600px wide to stay within Claude vision limits)
        w, h = img.size
        if w > 1600:
            ratio = 1600 / w
            img = img.resize((1600, int(h * ratio)), Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
        result.append(b64)
    return result


def preprocess_icici_format(text: str) -> str:
    """
    ICICI Bank statements have merged Withdrawal/Deposit columns in extracted text.
    Pattern per transaction: S.No  DD.MM.YYYY  Amount  Balance  (then narration lines)
    We parse this and rebuild as a clean CSV with explicit Debit/Credit columns.
    """
    pattern = r'\d+\s+(\d{2}\.\d{2}\.\d{4})\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\n((?:(?!\d+\s+\d{2}\.\d{2}\.\d{4}).+\n?)*)'
    matches = re.findall(pattern, text)
    if len(matches) < 3:
        return text  # Not ICICI format, return as-is

    lines = ["Date,Debit,Credit,Balance,Narration"]
    prev_balance = None
    for date, amount, balance, remarks in matches:
        amount_f = float(amount.replace(",", ""))
        balance_f = float(balance.replace(",", ""))
        narration = " ".join(remarks.strip().split())[:100]
        # Determine debit vs credit by balance movement
        if prev_balance is not None:
            if balance_f < prev_balance:
                lines.append(f"{date},{amount_f},,{balance_f},{narration}")
            else:
                lines.append(f"{date},,{amount_f},{balance_f},{narration}")
        else:
            # First row — guess from balance
            lines.append(f"{date},{amount_f},,{balance_f},{narration}")
        prev_balance = balance_f

    return "\n".join(lines)


def clean_extracted_text(text: str) -> str:
    """Clean up OCR/extraction artifacts while preserving table structure."""
    # Remove excessive whitespace but keep newlines
    text = re.sub(r"[ \t]{3,}", "  ", text)
    # Remove form feed characters
    text = text.replace("\f", "\n--- New Page ---\n")
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize line endings
    text = re.sub(r"\r\n|\r", "\n", text)
    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def process_document(file_path: str) -> dict:
    """
    Main entry point. Accepts PDF or image, returns structured extraction result.
    Always converts pages to base64 images for Claude Vision extraction.
    Returns:
        {
            "raw_text": str,
            "page_images": list[str],  # base64 PNG per page for Claude Vision
            "tables": list[str],
            "bank_name": str,
            "extraction_method": str,
            "page_count": int,
        }
    """
    file_ext = Path(file_path).suffix.lower()
    result = {
        "raw_text": "",
        "page_images": [],
        "tables": [],
        "bank_name": "Unknown Bank",
        "extraction_method": "",
        "page_count": 0,
    }

    if file_ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"):
        # Single image — convert to base64 directly
        img = Image.open(file_path)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
        result["page_images"] = [b64]
        result["raw_text"] = extract_text_from_image(file_path)
        result["extraction_method"] = "vision_image"
        result["page_count"] = 1

    elif file_ext == ".pdf":
        # Always convert to images for Claude Vision (works for ANY bank format)
        try:
            result["page_images"] = pdf_pages_to_base64(file_path, max_pages=15, dpi=150)
            result["page_count"] = len(result["page_images"])
        except Exception:
            result["page_count"] = 1

        # Also extract text as fallback/for bank name detection
        if is_scanned_pdf(file_path):
            result["raw_text"] = clean_extracted_text(extract_text_from_scanned_pdf(file_path))
            result["extraction_method"] = "vision_scanned"
        else:
            raw_text, tables = extract_text_from_digital_pdf(file_path)
            result["raw_text"] = clean_extracted_text(raw_text)
            result["tables"] = tables
            result["extraction_method"] = "vision_pdf"
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

    result["bank_name"] = detect_bank_name(result["raw_text"])
    return result
