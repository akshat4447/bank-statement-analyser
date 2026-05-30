"""
Transaction classifier — single Gemini Flash batch call for ALL transactions.
No regex needed: Gemini 1.5 Flash is free, fast, and handles every format.
One API call classifies entire statement in ~2 seconds.
"""
import os
import re
import json
from collections import Counter

from models.schemas import Transaction, TransactionCategory


def classify_transactions_hybrid(transactions: list[Transaction]) -> list[Transaction]:
    """
    Send ALL transactions to Gemini Flash in one batched call.
    Handles every bank format, merchant, and narration style accurately.
    Falls back to Transfer/Other if Gemini unavailable.
    """
    if not transactions:
        return transactions

    # Build compact batch — index|narration|amount_type
    lines = []
    for i, txn in enumerate(transactions):
        amt_type = "CR" if txn.credit else "DR"
        lines.append(f"{i}|{txn.narration[:100]}|{amt_type}")

    gemini_results = _gemini_classify_batch_all(lines)

    for i, txn in enumerate(transactions):
        if i in gemini_results:
            cat = gemini_results[i]
        else:
            # Fallback: UPI/NEFT = Transfer, else Other
            narr = txn.narration.upper()
            if any(k in narr for k in ["UPI/", "NEFT/", "RTGS/", "IMPS/"]):
                cat = TransactionCategory.TRANSFER
            else:
                cat = TransactionCategory.OTHER

        txn.category = cat
        txn.is_bounce = cat == TransactionCategory.BOUNCE
        txn.is_salary = cat == TransactionCategory.SALARY
        txn.is_emi = cat == TransactionCategory.EMI

    # Detect recurring: same narration root appears 2+ times
    narr_counts = Counter(t.narration[:30] for t in transactions)
    for txn in transactions:
        if narr_counts[txn.narration[:30]] >= 2:
            txn.is_recurring = True

    return transactions


def _gemini_classify_batch_all(lines: list[str]) -> dict[int, TransactionCategory]:
    """Single Gemini Flash call for all transactions."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Gemini can handle ~500 transactions per call easily
    # Chunk if very large statement
    if len(lines) > 500:
        result = {}
        for chunk_start in range(0, len(lines), 500):
            chunk = lines[chunk_start:chunk_start + 500]
            partial = _call_gemini(model, chunk, offset=chunk_start)
            result.update(partial)
        return result

    return _call_gemini(model, lines, offset=0)


def _call_gemini(model, lines: list[str], offset: int = 0) -> dict[int, TransactionCategory]:
    batch_text = "\n".join(lines)
    prompt = f"""Classify each Indian bank transaction into exactly one category.
Format: index|narration|CR(credit/incoming) or DR(debit/outgoing)

Categories:
- Salary: salary credits, payroll, stipend
- EMI/Loan Repayment: EMI, NACH debit, loan repayment
- Rent: rent, house/flat/PG rent
- Utilities: electricity, water, gas, internet, mobile recharge, DTH
- Food & Grocery: Swiggy, Zomato, Blinkit, Zepto, BigBasket, restaurants, grocery stores
- Travel & Transport: Ola, Uber, Rapido, IRCTC, airlines, petrol, fuel
- Entertainment: Netflix, Prime, Hotstar, Spotify, BookMyShow, cinema
- Insurance: LIC, insurance premium, policy
- Investments: mutual fund, SIP, Zerodha, Groww, stocks, PPF, NPS
- Medical: pharmacy, hospital, clinic, doctor, medicine
- Shopping: Amazon, Flipkart, Myntra, Meesho, Ajio, Nykaa, ecommerce
- Education: school/college fees, tuition, Udemy, Coursera, Byju's
- Cash Withdrawal/Deposit: ATM withdrawal, cash deposit
- Transfer: generic UPI/NEFT/RTGS/IMPS transfers to individuals, no clear merchant
- Bounce/Return: bounced cheque, returned payment, insufficient funds
- Other: anything else

Transactions:
{batch_text}

Return ONLY a JSON object: {{"0": "Category", "1": "Category", ...}}
No explanation. No markdown. Pure JSON only."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()
        raw = json.loads(text)
        result = {}
        for k, v in raw.items():
            try:
                real_idx = int(k) + offset
                result[real_idx] = TransactionCategory(v)
            except (ValueError, KeyError):
                result[int(k) + offset] = TransactionCategory.OTHER
        return result
    except Exception:
        return {}
