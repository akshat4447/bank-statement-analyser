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
    Classify all transactions:
    1. Tier-1: Fast regex rules for high-confidence patterns (runs always)
    2. Tier-2: Gemini Flash for remaining unclassified transactions
    This ensures categorization never returns all-Other even if Gemini fails.
    """
    if not transactions:
        return transactions

    # ── Tier 1: Regex rules (deterministic, runs first) ──────────────────────
    tier1_results = _classify_tier1(transactions)

    # Separate classified vs unclassified
    unclassified_idxs = [i for i, cat in tier1_results.items() if cat is None]
    classified_idxs = {i: cat for i, cat in tier1_results.items() if cat is not None}

    # ── Tier 2: Gemini Flash for remaining unclassified ───────────────────────
    gemini_results = {}
    if unclassified_idxs:
        lines = []
        for i in unclassified_idxs:
            txn = transactions[i]
            merchant = extract_merchant(txn.narration)
            amt_type = "CR" if txn.credit else "DR"
            lines.append(f"{i}|{merchant}|{amt_type}")
        gemini_results = _call_gemini_all(lines, index_map=unclassified_idxs)

    # ── Apply results ─────────────────────────────────────────────────────────
    for i, txn in enumerate(transactions):
        cat = classified_idxs.get(i) or gemini_results.get(i) or TransactionCategory.OTHER
        txn.category = cat
        txn.is_bounce = cat == TransactionCategory.BOUNCE
        txn.is_emi = cat == TransactionCategory.EMI

        # Salary: must come from a company/employer, NOT a personal UPI transfer
        if cat == TransactionCategory.SALARY:
            narr_lower = txn.narration.lower()
            merchant = extract_merchant(txn.narration)
            # Reject if UPI transfer from personal name
            is_upi = "upi/" in narr_lower or "upi-" in narr_lower
            if is_upi and _is_personal_name(merchant) and txn.credit:
                txn.category = TransactionCategory.TRANSFER
                txn.is_salary = False
            else:
                txn.is_salary = True
        else:
            txn.is_salary = False

    # Recurring: group by merchant, flag if appears 2+ times
    merchant_counts = Counter(extract_merchant(t.narration) for t in transactions)
    for txn in transactions:
        merchant = extract_merchant(txn.narration)
        if merchant_counts[merchant] >= 2:
            txn.is_recurring = True

    return transactions


# ── Known merchant keyword lookup tables ─────────────────────────────────────

_FOOD_KEYWORDS = [
    "swiggy", "zomato", "blinkit", "zepto", "amul", "cafe", "coffee",
    "restaurant", "dominos", "pizza", "burger", "mcdonald", "kfc", "subway",
    "dunkin", "starbucks", "chai", "biryani", "dhaba", "canteen", "mess",
    "haldiram", "bigbasket", "grofer", "instamart", "milkbasket",
]
# NOTE: "canteen" intentionally kept in FOOD (it overrides EDUCATION's "bits canteen")
# BITS college canteen is food spending, not tuition fees
_TRAVEL_KEYWORDS = [
    "irctc", "indigo", "spicejet", "airindia", "goair", "vistara", "akasa",
    "ola cabs", "uber", "rapido", "redbus", "cleartrip", "makemytrip", "yatra",
    "petrol", "fuel", "hpcl", "bpcl", "iocl", "shell", "essar",
    "metro card", "nmmrc", "bmtc", "msrtc",
]
# "ola" alone removed — too short, matches "payola" or other narrations
_SHOPPING_KEYWORDS = [
    "amazon", "flipkart", "myntra", "ajio", "meesho", "snapdeal", "tata cliq",
    "nykaa", "dmart", "more store", "big bazaar", "spencer",
    "shopsy", "decathlon", "ikea",
]
_ENTERTAINMENT_KEYWORDS = [
    "netflix", "spotify", "amazon prime", "hotstar", "disney", "zee5",
    "bookmyshow", "pvr", "inox", "cinepolis", "youtube premium",
    "gaana", "jio saavn", "apple music",
]
_UTILITIES_KEYWORDS = [
    "electricity", "bescom", "msedcl", "tpddl", "bses", "cesc",
    "airtel", "vodafone", "bsnl", "act fibernet",
    "hathway", "tikona", "piped gas", "mahanagar gas",
    "mobile bill", "broadband", "postpaid",
    # "jio" alone skipped — too common in narrations unrelated to Jio services
]
_EMI_KEYWORDS = [
    "emi", "nach", "ecs debit", "loan repay", "loan emi", "hdfc bank emi",
    "icici bank emi", "axis bank emi", "kotak emi", "housing loan",
    "car loan", "personal loan", "home loan",
]
_SALARY_KEYWORDS = [
    "salary", "payroll", "stipend", "wages",
    "salary credit", "sal cr", "monthly salary",
    # "ctc" removed — too short, matches "irctc"
    # "neft cr" removed — too broad; IRCTC contains "cr"
]
_GAMBLING_KEYWORDS = [
    "dream11", "dream 11", "mpl game", "rummy", "poker", "casino", "winzo",
    "adda52", "junglee", "hobigames", "my11circle", "fantasy cricket",
    "wazirx", "binance", "coinbase", "coindcx", "zebpay", "bitbns",
    "crypto buy", "crypto sell",
]
_MEDICAL_KEYWORDS = [
    "pharmacy", "chemist", "hospital", "clinic", "apollo", "medplus",
    "netmeds", "1mg", "pharmeasy", "doctor", "lab test", "diagnostics",
    "medanta", "fortis", "max hospital",
]
_EDUCATION_KEYWORDS = [
    "school fees", "college fees", "university fees", "tuition fee", "exam fee",
    "byjus", "unacademy", "udemy", "coursera", "neso academy",
    "bits pilani", "iit fees", "nit fees", "coaching fees",
]
_INVESTMENT_KEYWORDS = [
    "zerodha", "groww", "upstox", "angel", "hdfc securities", "icici direct",
    "mutual fund", "sip", "nps", "ppf", "fd booking", "rd booking",
    "goldbees", "liquidbees",
]
_CASH_KEYWORDS = [
    "atm", "cash withdrawal", "cash deposit", "cdm",
]
_BOUNCE_KEYWORDS = [
    "bounce", "returned", "dishonoured", "dishonourd", "chq ret",
    "cheque return", "ecs return", "nach return", "mandate return",
]


def _classify_tier1(transactions: list[Transaction]) -> dict[int, TransactionCategory | None]:
    """
    Fast keyword-based Tier-1 classifier.
    Order matters: more specific rules first (e.g. SALARY before generic UPI TRANSFER).
    Returns None for unmatched — Tier-2 (Gemini) handles those.
    """
    results: dict[int, TransactionCategory | None] = {}

    for i, txn in enumerate(transactions):
        narr = txn.narration.lower()
        cat = None

        if any(k in narr for k in _BOUNCE_KEYWORDS):
            cat = TransactionCategory.BOUNCE
        elif any(k in narr for k in _SALARY_KEYWORDS):
            cat = TransactionCategory.SALARY
        elif any(k in narr for k in _EMI_KEYWORDS):
            cat = TransactionCategory.EMI
        elif any(k in narr for k in _GAMBLING_KEYWORDS):
            cat = TransactionCategory.GAMBLING
        elif any(k in narr for k in _TRAVEL_KEYWORDS):
            cat = TransactionCategory.TRAVEL
        elif any(k in narr for k in _FOOD_KEYWORDS):
            cat = TransactionCategory.FOOD
        elif any(k in narr for k in _SHOPPING_KEYWORDS):
            cat = TransactionCategory.SHOPPING
        elif any(k in narr for k in _ENTERTAINMENT_KEYWORDS):
            cat = TransactionCategory.ENTERTAINMENT
        elif any(k in narr for k in _UTILITIES_KEYWORDS):
            cat = TransactionCategory.UTILITIES
        elif any(k in narr for k in _MEDICAL_KEYWORDS):
            cat = TransactionCategory.MEDICAL
        elif any(k in narr for k in _EDUCATION_KEYWORDS):
            cat = TransactionCategory.EDUCATION
        elif any(k in narr for k in _INVESTMENT_KEYWORDS):
            cat = TransactionCategory.INVESTMENTS
        elif any(k in narr for k in _CASH_KEYWORDS):
            cat = TransactionCategory.CASH
        elif narr.startswith("upi/") or narr.startswith("upi-"):
            # Any UPI transaction not caught by specific rules above → Transfer
            # This ensures ANAMIKA KU / BOBBA NAGA / generic UPI goes to Transfer, not Other
            cat = TransactionCategory.TRANSFER

        results[i] = cat

    return results


def _is_personal_name(merchant: str) -> bool:
    """
    Stricter check: only flag as personal name when it's a UPI transfer
    AND looks like a human name (2-3 words, mostly alphabetic, no company indicators).
    """
    # Company indicators — never flag these as personal
    company_indicators = [
        "pvt", "ltd", "limited", "llp", "inc", "corp", "technologies",
        "solutions", "services", "enterprises", "industries", "foundation",
        "bank", "finance", "capital", "payments", "pay", "tech",
    ]
    merchant_lower = merchant.lower()
    if any(ind in merchant_lower for ind in company_indicators):
        return False

    words = [w for w in merchant.strip().split() if w]
    # Personal name pattern: 2-3 short words, all alphabetic
    if 2 <= len(words) <= 3:
        all_alpha = all(w.replace(".", "").isalpha() for w in words)
        all_short = all(len(w) <= 12 for w in words)
        if all_alpha and all_short:
            return True

    return False


def _call_gemini_all(lines: list[str], index_map: list[int] | None = None) -> dict[int, TransactionCategory]:
    """
    Gemini Flash call for a list of transactions.
    index_map: original transaction indices (so results map back correctly).
    """
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception:
        return {}

    # Re-index lines as 0,1,2... for the LLM; translate back using index_map
    if index_map is None:
        index_map = list(range(len(lines)))

    chunk_size = 400
    result: dict[int, TransactionCategory] = {}

    for chunk_start in range(0, len(lines), chunk_size):
        chunk_lines = lines[chunk_start:chunk_start + chunk_size]
        chunk_map = index_map[chunk_start:chunk_start + chunk_size]
        # Re-number 0-based for the prompt
        renumbered = [f"{j}|{'|'.join(ln.split('|')[1:])}" for j, ln in enumerate(chunk_lines)]
        partial = _gemini_request(model, renumbered, chunk_map)
        result.update(partial)

    return result


# ── Normalization map: Gemini often returns short names, map to exact enum values ──
_CATEGORY_NORMALIZE: dict[str, str] = {
    # Short aliases Gemini commonly returns
    "food": "Food & Grocery",
    "grocery": "Food & Grocery",
    "food & grocery": "Food & Grocery",
    "travel": "Travel & Transport",
    "transport": "Travel & Transport",
    "travel & transport": "Travel & Transport",
    "emi": "EMI/Loan Repayment",
    "loan": "EMI/Loan Repayment",
    "emi/loan repayment": "EMI/Loan Repayment",
    "loan repayment": "EMI/Loan Repayment",
    "cash": "Cash Withdrawal/Deposit",
    "atm": "Cash Withdrawal/Deposit",
    "cash withdrawal": "Cash Withdrawal/Deposit",
    "cash withdrawal/deposit": "Cash Withdrawal/Deposit",
    "bounce": "Bounce/Return",
    "return": "Bounce/Return",
    "bounce/return": "Bounce/Return",
    "gambling": "Gambling/High-Risk",
    "high-risk": "Gambling/High-Risk",
    "gambling/high-risk": "Gambling/High-Risk",
    "crypto": "Gambling/High-Risk",
    "transfer": "Transfer",
    "salary": "Salary",
    "utilities": "Utilities",
    "utility": "Utilities",
    "shopping": "Shopping",
    "entertainment": "Entertainment",
    "investments": "Investments",
    "investment": "Investments",
    "medical": "Medical",
    "healthcare": "Medical",
    "education": "Education",
    "insurance": "Insurance",
    "rent": "Rent",
    "other": "Other",
}


def _normalize_category(raw: str) -> TransactionCategory:
    """Map any Gemini response string to a valid TransactionCategory, never raises."""
    normalized = _CATEGORY_NORMALIZE.get(raw.lower().strip(), raw)
    try:
        return TransactionCategory(normalized)
    except (ValueError, KeyError):
        return TransactionCategory.OTHER


def _gemini_request(model, lines: list[str], index_map: list[int]) -> dict[int, TransactionCategory]:
    n = len(lines)
    batch_text = "\n".join(lines)
    prompt = f"""You are classifying {n} Indian bank transactions.
Input: index|merchant_name|CR or DR

You MUST return exactly {n} entries in your JSON — one per input line.

Use ONLY these exact category strings (copy them exactly):
"Salary", "EMI/Loan Repayment", "Rent", "Utilities", "Food & Grocery",
"Travel & Transport", "Entertainment", "Insurance", "Investments",
"Medical", "Shopping", "Education", "Cash Withdrawal/Deposit",
"Transfer", "Bounce/Return", "Gambling/High-Risk", "Other"

Classification rules:
- Salary = employer NEFT credit (NOT UPI from individual person)
- EMI/Loan Repayment = NACH, ECS, loan repayment debits
- Food & Grocery = Swiggy, Zomato, Amul, cafe, restaurant, canteen, dhaba
- Travel & Transport = IRCTC, Uber, Rapido, airlines, petrol, fuel, metro
- Shopping = Amazon, Flipkart, Myntra, Meesho, ecommerce
- Entertainment = Netflix, Spotify, BookMyShow, cinemas
- Utilities = electricity, Airtel, Vodafone, recharge, broadband, gas bill
- Medical = pharmacy, hospital, clinic, Apollo, 1mg
- Education = school fees, Byju's, Unacademy, Neso Academy
- Investments = Zerodha, Groww, mutual fund, SIP
- Transfer = UPI to individual person, personal money transfer
- Bounce/Return = bounced cheque, ECS return, mandate return
- Gambling/High-Risk = Dream11, WazirX, Binance, poker, casino

Transactions ({n} total):
{batch_text}

Return ONLY a JSON object with exactly {n} keys (0 to {n-1}):
{{"0": "Food & Grocery", "1": "Transfer", "2": "EMI/Loan Repayment", ...}}
Pure JSON only. No markdown. No explanation. No extra keys."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown fences
        if "```" in text:
            text = re.sub(r"```[a-z]*\n?", "", text).strip().rstrip("`").strip()
        # Extract JSON object if there's surrounding text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
        raw = json.loads(text)
        result: dict[int, TransactionCategory] = {}
        for k, v in raw.items():
            local_idx = int(k)
            if 0 <= local_idx < len(index_map):
                orig_idx = index_map[local_idx]
                result[orig_idx] = _normalize_category(str(v))
        return result
    except Exception as e:
        return {}
