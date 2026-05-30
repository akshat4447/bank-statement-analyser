"""
Transaction classifier — Gemini Flash single batch call.
Pre-processes UPI narrations to extract merchant names before classifying.
"""
import os
import re
import json
from collections import Counter

from models.schemas import Transaction, TransactionCategory


def extract_merchant(narration: str) -> str:
    """
    Extract meaningful merchant name from bank narration.
    UPI/SWIGGY/upiswiggy@icic/... → SWIGGY
    NEFT/CR/HDFC BANK/SALARY → HDFC BANK SALARY
    """
    narration = narration.strip()

    # UPI format: UPI/MERCHANT NAME/upi@id/...
    upi_match = re.match(r'(?i)UPI[/-]([^/]+)/', narration)
    if upi_match:
        return upi_match.group(1).strip()

    # NEFT/RTGS/IMPS format
    neft_match = re.match(r'(?i)(NEFT|RTGS|IMPS)[/-](?:CR[/-]|DR[/-])?(.+?)(?:/|$)', narration)
    if neft_match:
        return neft_match.group(2).strip()[:60]

    return narration[:80]


def classify_transactions_hybrid(transactions: list[Transaction]) -> list[Transaction]:
    """
    Classify all transactions with Gemini Flash in one batch call.
    Extracts clean merchant names before sending — much more accurate.
    """
    if not transactions:
        return transactions

    # Build batch with clean merchant names
    lines = []
    for i, txn in enumerate(transactions):
        merchant = extract_merchant(txn.narration)
        amt_type = "CR" if txn.credit else "DR"
        lines.append(f"{i}|{merchant}|{amt_type}")

    gemini_results = _call_gemini_all(lines)

    for i, txn in enumerate(transactions):
        cat = gemini_results.get(i, TransactionCategory.OTHER)
        txn.category = cat
        txn.is_bounce = cat == TransactionCategory.BOUNCE
        txn.is_emi = cat == TransactionCategory.EMI
        # Salary only if it's NOT a personal name transfer
        if cat == TransactionCategory.SALARY:
            merchant = extract_merchant(txn.narration)
            # Personal names are usually 2 words, company names are longer/different
            if _is_personal_name(merchant) and txn.credit:
                txn.category = TransactionCategory.TRANSFER  # Reclassify as transfer
                txn.is_salary = False
            else:
                txn.is_salary = True
        else:
            txn.is_salary = False

    # Recurring: group by extracted merchant name, flag if 2+ times
    merchant_counts = Counter(extract_merchant(t.narration) for t in transactions)
    for txn in transactions:
        merchant = extract_merchant(txn.narration)
        if merchant_counts[merchant] >= 2:
            txn.is_recurring = True

    return transactions


def _is_personal_name(merchant: str) -> bool:
    """
    Heuristic: if merchant looks like a personal name (2 words, proper case),
    it's likely a P2P transfer, not a company salary.
    """
    words = merchant.strip().split()
    if len(words) == 2 and all(w[0].isupper() if w else False for w in words):
        return True
    # All caps short name like "ANAMIKA KU" or "BOBBA NAGA"
    if len(words) <= 3 and merchant.replace(" ", "").isalpha():
        return True
    return False


def _call_gemini_all(lines: list[str]) -> dict[int, TransactionCategory]:
    """Single Gemini Flash call for all transactions."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Chunk if >500 transactions
    if len(lines) > 500:
        result = {}
        for start in range(0, len(lines), 500):
            chunk = lines[start:start + 500]
            partial = _gemini_request(model, chunk, offset=start)
            result.update(partial)
        return result

    return _gemini_request(model, lines, offset=0)


def _gemini_request(model, lines: list[str], offset: int = 0) -> dict[int, TransactionCategory]:
    batch_text = "\n".join(lines)
    prompt = f"""Classify each Indian bank transaction into exactly one category.
Input format: index|merchant_name|CR(incoming money) or DR(outgoing money)

Rules:
- "Transfer" = generic P2P UPI payment to a PERSON (individual name, phone number)
- "Salary" = ONLY use if clearly from a company/employer via NEFT, never for person-to-person UPI
- Food & Grocery = Swiggy, Zomato, Blinkit, Zepto, restaurants, cafes, food shops
- Travel & Transport = Ola, Uber, Rapido, IRCTC, airlines, petrol, fuel stations
- Shopping = Amazon, Flipkart, Myntra, Meesho, ecommerce
- Entertainment = Netflix, Spotify, BookMyShow, cinemas
- Utilities = electricity, water, gas, internet, mobile recharge
- EMI/Loan Repayment = EMI, NACH, loan repayment
- Investments = mutual fund, SIP, Zerodha, Groww, stocks
- Medical = pharmacy, hospital, clinic, medicine
- Education = school/college fees, Byju's, Unacademy, Udemy
- Bounce/Return = bounced cheque, returned payment
- Other = anything unclassifiable

Categories: Salary, EMI/Loan Repayment, Rent, Utilities, Food & Grocery, Travel & Transport,
Entertainment, Insurance, Investments, Medical, Shopping, Education,
Cash Withdrawal/Deposit, Transfer, Bounce/Return, Other

Transactions:
{batch_text}

Return ONLY a JSON object: {{"0": "Food & Grocery", "1": "Transfer", ...}}
Pure JSON only, no markdown, no explanation."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()
        raw = json.loads(text)
        result = {}
        for k, v in raw.items():
            try:
                result[int(k) + offset] = TransactionCategory(v)
            except (ValueError, KeyError):
                result[int(k) + offset] = TransactionCategory.OTHER
        return result
    except Exception:
        return {}
