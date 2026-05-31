"""
Recurring transaction detection: identify merchants that appear multiple times.
🟠 Bug #9 Fix: Detect recurring transactions with merchant extraction and frequency analysis.
"""
from collections import defaultdict
from typing import List
from models.schemas import Transaction, MerchantSpend
from services.transaction_classifier import extract_merchant


def detect_recurring_transactions(transactions: List[Transaction]) -> List[MerchantSpend]:
    """
    Identify recurring merchants (appear 2+ times).
    🔴 Analyze by merchant name after deduplication.
    """
    merchant_data = defaultdict(lambda: {"count": 0, "total": 0.0, "amounts": []})

    for t in transactions:
        # Only count debits (expenses), not credits
        if t.debit and t.debit > 0:
            merchant = extract_merchant(t.narration)
            merchant_data[merchant]["count"] += 1
            merchant_data[merchant]["total"] += t.debit
            merchant_data[merchant]["amounts"].append(t.debit)

    # Filter for recurring (2+ transactions) and sort by frequency
    recurring = []
    for merchant, data in merchant_data.items():
        if data["count"] >= 2:
            recurring.append(MerchantSpend(
                merchant=merchant,
                amount=round(data["total"], 2),
                count=data["count"],
                category="Recurring",
            ))

    # Sort by frequency (count) descending
    recurring.sort(key=lambda x: -x.count)

    return recurring
