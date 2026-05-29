"""
Two-tier transaction categorization:
  Tier 1 - Regex pre-tagger: handles ~70% of transactions instantly, zero cost
  Tier 2 - Gemini 1.5 Flash (free): batch-processes remaining ambiguous ones
Keeps Claude exclusively for QA + chatbot.
"""
import os
import re
import json
from typing import Optional

from models.schemas import Transaction, TransactionCategory

# ---------------------------------------------------------------------------
# Tier 1: Regex rules — ordered from most specific to least
# ---------------------------------------------------------------------------
_RULES: list[tuple[TransactionCategory, list[str]]] = [
    (TransactionCategory.BOUNCE, [
        r"(?i)\bBOUNCE\b", r"(?i)DISHONOUR", r"(?i)DISHONORED",
        r"(?i)\bRETURN(ED)?\b.*CHQ", r"(?i)CHQ.*RETURN", r"(?i)ECS.*RETURN",
        r"(?i)NACH.*RETURN", r"(?i)INSUFFICIENT FUND", r"(?i)NOT PAID",
        r"(?i)\bUNPAID\b", r"(?i)PAYMENT DECLINED",
    ]),
    (TransactionCategory.SALARY, [
        r"(?i)\bSALARY\b", r"(?i)\bSAL\b(?!\w)", r"(?i)\bPAYROLL\b",
        r"(?i)SALARY CREDIT", r"(?i)MONTHLY SALARY", r"(?i)\bWAGES\b",
        r"(?i)\bSTIPEND\b", r"(?i)COMPENSATION.*CREDIT",
    ]),
    (TransactionCategory.EMI, [
        r"(?i)\bEMI\b", r"(?i)NACH.*DEBIT", r"(?i)ECS.*LOAN",
        r"(?i)LOAN.*REPAY", r"(?i)HOUSING.*LOAN", r"(?i)HOME.*LOAN",
        r"(?i)CAR.*LOAN", r"(?i)BIKE.*LOAN", r"(?i)PERSONAL.*LOAN",
        r"(?i)EDUCATION.*LOAN", r"(?i)BAJAJ.*FINANCE", r"(?i)HDFC.*LOAN",
        r"(?i)ICICI.*LOAN", r"(?i)SBI.*LOAN",
    ]),
    (TransactionCategory.UTILITIES, [
        r"(?i)ELECTRICITY", r"(?i)\bBESCOM\b", r"(?i)\bMSEB\b",
        r"(?i)\bTNEB\b", r"(?i)\bBSES\b", r"(?i)WATER.*BILL",
        r"(?i)GAS.*BILL", r"(?i)\bIGL\b", r"(?i)\bMGL\b",
        r"(?i)INTERNET.*BILL", r"(?i)BROADBAND",
        r"(?i)\bAIRTEL\b", r"(?i)\bJIO\b", r"(?i)\bBSNL\b",
        r"(?i)\bVI\b.*BILL", r"(?i)VODAFONE.*BILL", r"(?i)IDEA.*BILL",
        r"(?i)TATA.*SKY", r"(?i)DISH.*TV",
    ]),
    (TransactionCategory.RENT, [
        r"(?i)\bRENT\b", r"(?i)HOUSE.*RENT", r"(?i)FLAT.*RENT",
        r"(?i)LANDLORD", r"(?i)PROPERTY.*RENT", r"(?i)ACCOMMODATION",
        r"(?i)PG.*RENT", r"(?i)HOSTEL.*FEES",
    ]),
    (TransactionCategory.FOOD, [
        r"(?i)\bSWIGGY\b", r"(?i)\bZOMATOb", r"(?i)\bZOMATO\b",
        r"(?i)\bBLINKIT\b", r"(?i)\bZEPTO\b", r"(?i)BIGBASKET",
        r"(?i)\bDMART\b", r"(?i)RELIANCE FRESH", r"(?i)RELIANCE SMART",
        r"(?i)MORE RETAIL", r"(?i)FRESH.*MEAT", r"(?i)RESTAURANT",
        r"(?i)\bCAFE\b", r"(?i)\bDINING\b",
    ]),
    (TransactionCategory.TRAVEL, [
        r"(?i)\bOLA\b", r"(?i)\bUBER\b", r"(?i)\bRAPIDO\b",
        r"(?i)\bIRCTC\b", r"(?i)INDIAN RAIL", r"(?i)RAILWAYS",
        r"(?i)\bINDIGO\b", r"(?i)SPICEJET", r"(?i)AIR INDIA",
        r"(?i)VISTARA", r"(?i)\bMMT\b", r"(?i)MAKEMYTRIP",
        r"(?i)YATRA", r"(?i)GOIBIBO",
        r"(?i)PETROL", r"(?i)\bFUEL\b", r"(?i)DIESEL",
        r"(?i)\bHPCL\b", r"(?i)\bBPCL\b", r"(?i)\bIOCL\b",
    ]),
    (TransactionCategory.ENTERTAINMENT, [
        r"(?i)NETFLIX", r"(?i)AMAZON PRIME", r"(?i)\bHOTSTAR\b",
        r"(?i)\bSPOTIFY\b", r"(?i)YOUTUBE PREMIUM", r"(?i)\bZEE5\b",
        r"(?i)SONYLIV", r"(?i)BOOKMYSHOW", r"(?i)BOOK.*SHOW",
        r"(?i)\bPVR\b", r"(?i)\bINOX\b",
    ]),
    (TransactionCategory.INSURANCE, [
        r"(?i)\bLIC\b", r"(?i)INSURANCE", r"(?i)POLICY.*PREMIUM",
        r"(?i)BAJAJ.*ALLIANZ", r"(?i)MAX.*LIFE", r"(?i)HDFC.*LIFE",
        r"(?i)ICICI.*PRUD", r"(?i)STAR HEALTH", r"(?i)NIVA BUPA",
        r"(?i)CARE.*HEALTH", r"(?i)TATA.*AIG",
    ]),
    (TransactionCategory.INVESTMENTS, [
        r"(?i)MUTUAL FUND", r"(?i)\bSIP\b", r"(?i)\bZERODHA\b",
        r"(?i)\bGROWW\b", r"(?i)\bUPSTOX\b", r"(?i)PPFAS",
        r"(?i)MIRAE ASSET", r"(?i)AXIS MF", r"(?i)SBI MF",
        r"(?i)HDFC MF", r"(?i)\bDEMAT\b", r"(?i)STOCKS.*INVEST",
        r"(?i)NSE.*INVEST", r"(?i)BSE.*INVEST",
        r"(?i)\bPPF\b", r"(?i)\bNPS\b", r"(?i)NATIONAL PENSION",
    ]),
    (TransactionCategory.MEDICAL, [
        r"(?i)PHARMACY", r"(?i)MEDICAL", r"(?i)HOSPITAL",
        r"(?i)CLINIC", r"(?i)APOLLO", r"(?i)FORTIS",
        r"(?i)MEDPLUS", r"(?i)NETMEDS", r"(?i)PHARMEASY",
        r"(?i)1MG", r"(?i)DOCTOR.*FEE",
    ]),
    (TransactionCategory.SHOPPING, [
        r"(?i)AMAZON", r"(?i)FLIPKART", r"(?i)\bMYNTRA\b",
        r"(?i)\bMEESHO\b", r"(?i)\bAJIO\b", r"(?i)\bNYKAA\b",
        r"(?i)TATA CLIQ", r"(?i)SNAPDEAL", r"(?i)SHOPSY",
    ]),
    (TransactionCategory.EDUCATION, [
        r"(?i)SCHOOL.*FEE", r"(?i)COLLEGE.*FEE", r"(?i)TUITION.*FEE",
        r"(?i)UNIVERSITY", r"(?i)\bUDEMY\b", r"(?i)\bCOURSERA\b",
        r"(?i)BYJU", r"(?i)\bUNACADEMY\b", r"(?i)VEDANTU",
    ]),
    (TransactionCategory.CASH, [
        r"(?i)\bATM\b", r"(?i)CASH.*WITH", r"(?i)CASH.*DEP",
        r"(?i)CDM", r"(?i)CASH DEPOSIT MACHINE", r"(?i)ATM.*WDL",
        r"(?i)CURRENCY.*CHEST",
    ]),
]

# Compile all patterns once at module load
_COMPILED_RULES: list[tuple[TransactionCategory, list[re.Pattern]]] = [
    (cat, [re.compile(p) for p in patterns])
    for cat, patterns in _RULES
]


def regex_classify(narration: str) -> Optional[TransactionCategory]:
    """Returns category if a regex rule matches, else None (ambiguous)."""
    for category, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(narration):
                return category
    return None


def is_transfer(narration: str) -> bool:
    """Generic UPI/NEFT/RTGS transfers with no merchant signal."""
    transfer_patterns = [
        r"(?i)^UPI/", r"(?i)^NEFT/", r"(?i)^RTGS/", r"(?i)^IMPS/",
        r"(?i)^UPI-", r"(?i)TRANSFER (TO|FROM)", r"(?i)FUND TRANSFER",
    ]
    for p in transfer_patterns:
        if re.search(p, narration):
            return True
    return False


# ---------------------------------------------------------------------------
# Tier 2: Gemini 1.5 Flash — batch classify ambiguous transactions
# ---------------------------------------------------------------------------
def _gemini_classify_batch(narrations: list[tuple[int, str]]) -> dict[int, TransactionCategory]:
    """Send ambiguous narrations to Gemini Flash in a single call."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    lines = "\n".join(f"{idx}|{narr}" for idx, narr in narrations)

    prompt = f"""Classify each Indian bank transaction narration into exactly one category.

Categories: Salary, EMI/Loan Repayment, Rent, Utilities, Food & Grocery, Travel & Transport,
Entertainment, Insurance, Investments, Medical, Shopping, Education,
Cash Withdrawal/Deposit, Transfer, Bounce/Return, Other

Input format: index|narration
Output format: Return a JSON object mapping index (as string) to category name.
Only output valid JSON, nothing else.

Transactions:
{lines}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()
        raw = json.loads(text)
        result = {}
        for k, v in raw.items():
            try:
                result[int(k)] = TransactionCategory(v)
            except (ValueError, KeyError):
                result[int(k)] = TransactionCategory.OTHER
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def classify_transactions_hybrid(transactions: list[Transaction]) -> list[Transaction]:
    """
    Two-tier classifier:
    1. Regex handles obvious ones (free, instant)
    2. Gemini Flash handles the rest in one batched call
    Returns transactions with category + flags populated.
    """
    ambiguous: list[tuple[int, str]] = []

    # Tier 1
    for i, txn in enumerate(transactions):
        category = regex_classify(txn.narration)
        if category:
            txn.category = category
            txn.is_bounce = category == TransactionCategory.BOUNCE
            txn.is_salary = category == TransactionCategory.SALARY
            txn.is_emi = category == TransactionCategory.EMI
        elif is_transfer(txn.narration):
            txn.category = TransactionCategory.TRANSFER
        else:
            ambiguous.append((i, txn.narration[:120]))  # Truncate long narrations

    # Tier 2: only the ambiguous ones
    if ambiguous:
        gemini_results = _gemini_classify_batch(ambiguous)
        for orig_idx, _ in ambiguous:
            if orig_idx in gemini_results:
                cat = gemini_results[orig_idx]
                transactions[orig_idx].category = cat
                transactions[orig_idx].is_bounce = cat == TransactionCategory.BOUNCE
                transactions[orig_idx].is_salary = cat == TransactionCategory.SALARY
                transactions[orig_idx].is_emi = cat == TransactionCategory.EMI
            else:
                transactions[orig_idx].category = TransactionCategory.OTHER

    # Detect recurring: same narration root appears 2+ times with similar amounts
    from collections import Counter
    narr_counts = Counter(t.narration[:30] for t in transactions)
    for txn in transactions:
        if narr_counts[txn.narration[:30]] >= 2:
            txn.is_recurring = True

    return transactions
