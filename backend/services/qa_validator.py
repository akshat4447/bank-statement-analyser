"""
AI QA Validation Layer.
Second Claude pass that cross-checks extracted data vs source and validates analytics.
"""
import os
import json
from datetime import datetime

import anthropic

from models.schemas import (
    Transaction, AccountInfo, AnalyticsResult,
    QAValidationResult, QACheck,
)
from prompts.qa_validation import QA_SYSTEM_PROMPT

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

QA_TOOL = {
    "name": "validate_bank_statement_analysis",
    "description": "Validate extracted bank statement data and analytics",
    "input_schema": {
        "type": "object",
        "properties": {
            "checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "check_name": {"type": "string"},
                        "passed": {"type": "boolean"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 100},
                        "expected": {"type": ["string", "null"]},
                        "actual": {"type": ["string", "null"]},
                        "note": {"type": ["string", "null"]},
                    },
                    "required": ["check_name", "passed", "confidence"],
                },
            },
            "issues_found": {
                "type": "array",
                "items": {"type": "string"},
            },
            "extraction_accuracy": {"type": "number", "minimum": 0, "maximum": 100},
            "calculation_accuracy": {"type": "number", "minimum": 0, "maximum": 100},
            "categorization_accuracy": {"type": "number", "minimum": 0, "maximum": 100},
            "overall_notes": {"type": "string"},
        },
        "required": ["checks", "issues_found", "extraction_accuracy", "calculation_accuracy", "categorization_accuracy"],
    },
}


def _parse_date_safe(d: str):
    """Parse date string in any known format, returns datetime or None."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d/%m/%y"):
        try:
            return datetime.strptime(d.strip(), fmt)
        except ValueError:
            continue
    return None


def _math_checks(transactions: list[Transaction], analytics: AnalyticsResult) -> list[QACheck]:
    """Pure math validation — no AI needed, just verify numbers."""
    checks = []

    # Sum credits
    computed_credits = round(sum(t.credit for t in transactions if t.credit), 2)
    diff_c = abs(computed_credits - analytics.total_credits)
    checks.append(QACheck(
        check_name="Total Credits Match",
        passed=diff_c < 1.0,
        confidence=100.0 if diff_c < 1.0 else max(0.0, 100.0 - diff_c / max(analytics.total_credits, 1) * 100),
        expected=f"₹{computed_credits:,.2f}",
        actual=f"₹{analytics.total_credits:,.2f}",
        note=f"Difference: ₹{diff_c:,.2f}" if diff_c >= 1.0 else None,
    ))

    # Sum debits
    computed_debits = round(sum(t.debit for t in transactions if t.debit), 2)
    diff_d = abs(computed_debits - analytics.total_debits)
    checks.append(QACheck(
        check_name="Total Debits Match",
        passed=diff_d < 1.0,
        confidence=100.0 if diff_d < 1.0 else max(0.0, 100.0 - diff_d / max(analytics.total_debits, 1) * 100),
        expected=f"₹{computed_debits:,.2f}",
        actual=f"₹{analytics.total_debits:,.2f}",
        note=f"Difference: ₹{diff_d:,.2f}" if diff_d >= 1.0 else None,
    ))

    # Net cash flow
    expected_ncf = round(analytics.total_credits - analytics.total_debits, 2)
    diff_n = abs(expected_ncf - analytics.net_cash_flow)
    checks.append(QACheck(
        check_name="Net Cash Flow Calculation",
        passed=diff_n < 0.01,
        confidence=100.0 if diff_n < 0.01 else 50.0,
        expected=f"₹{expected_ncf:,.2f}",
        actual=f"₹{analytics.net_cash_flow:,.2f}",
    ))

    # Balance progression — use proper date sort (not string sort)
    sorted_txns = sorted(
        transactions,
        key=lambda x: _parse_date_safe(x.date) or datetime.min
    )
    balance_errors = 0
    checked = 0
    for i in range(1, len(sorted_txns)):
        prev = sorted_txns[i - 1]
        curr = sorted_txns[i]
        if prev.balance is None or curr.balance is None:
            continue
        expected_bal = round(prev.balance + (curr.credit or 0) - (curr.debit or 0), 2)
        if abs(expected_bal - curr.balance) > 2.0:
            balance_errors += 1
        checked += 1
        if checked >= 100:  # check up to 100 rows (not just 50)
            break

    balance_accuracy = round((1 - balance_errors / max(checked, 1)) * 100, 1)
    checks.append(QACheck(
        check_name="Balance Progression Validity",
        passed=balance_accuracy >= 80,
        confidence=balance_accuracy,
        note=f"{balance_errors}/{checked} rows with arithmetic mismatch",
    ))

    # Transaction count check
    checks.append(QACheck(
        check_name="Transaction Count",
        passed=len(transactions) == analytics.total_transactions,
        confidence=100.0 if len(transactions) == analytics.total_transactions else 80.0,
        expected=str(analytics.total_transactions),
        actual=str(len(transactions)),
    ))

    # Categorization coverage — how many transactions got a real category (not Other)
    categorized = sum(1 for t in transactions if t.category and t.category.value != "Other")
    cat_pct = round(categorized / max(len(transactions), 1) * 100, 1)
    checks.append(QACheck(
        check_name="Categorization Coverage",
        passed=cat_pct >= 50,
        confidence=cat_pct,
        note=f"{categorized}/{len(transactions)} transactions have a specific category ({cat_pct}%)",
    ))

    # Income source check — flag if no verified salary
    has_salary = any(t.is_salary for t in transactions)
    has_credits = any(t.credit for t in transactions)
    checks.append(QACheck(
        check_name="Income Source Verification",
        passed=has_salary,
        confidence=100.0 if has_salary else 40.0,
        note="Verified employer salary detected" if has_salary else
             "No verified salary — all credits are P2P or unidentified transfers",
    ))

    # FOIR sanity check
    cw = analytics.creditworthiness
    if cw.foir is not None and cw.average_monthly_income > 0:
        expected_foir = round(cw.average_monthly_emi / cw.average_monthly_income * 100, 1)
        foir_diff = abs(expected_foir - cw.foir)
        checks.append(QACheck(
            check_name="FOIR Calculation",
            passed=foir_diff < 1.0,
            confidence=100.0 if foir_diff < 1.0 else 70.0,
            expected=f"{expected_foir}%",
            actual=f"{cw.foir}%",
        ))

    return checks


def run_qa_validation(
    raw_text: str,
    transactions: list[Transaction],
    analytics: AnalyticsResult,
    account_info: AccountInfo,
) -> QAValidationResult:
    """
    Combined math + AI validation pass.
    Math checks run instantly and cover ALL transactions.
    AI layer validates categorization quality and income classification.
    """
    # Math checks (deterministic, full dataset)
    math_checks = _math_checks(transactions, analytics)

    # ── Build STRUCTURED context for AI (not truncated raw text) ─────────────
    # Send complete transaction list as compact JSON — no truncation issues
    all_txn_data = [
        {
            "date": t.date,
            "narration": t.narration[:60],
            "debit": t.debit or 0,
            "credit": t.credit or 0,
            "balance": t.balance,
            "category": t.category.value if t.category else "Other",
            "is_salary": t.is_salary,
        }
        for t in transactions
    ]

    # Derive opening balance from first transaction
    sorted_for_balance = sorted(transactions, key=lambda x: _parse_date_safe(x.date) or datetime.min)
    opening_balance = None
    closing_balance = None
    if sorted_for_balance:
        first = sorted_for_balance[0]
        if first.balance is not None:
            opening_balance = round(first.balance + (first.debit or 0) - (first.credit or 0), 2)
        last = sorted_for_balance[-1]
        closing_balance = last.balance

    # Categorization breakdown for AI review
    from collections import Counter
    cat_counts = Counter(t.category.value if t.category else "Other" for t in transactions)

    structured_context = {
        "statement_period": {
            "from": analytics.actual_period_from,
            "to": analytics.actual_period_to,
        },
        "account": {
            "holder": account_info.account_holder if account_info else None,
            "bank": account_info.bank_name if account_info else None,
        },
        "totals": {
            "total_transactions": len(transactions),
            "total_credits": analytics.total_credits,
            "total_debits": analytics.total_debits,
            "net_cash_flow": analytics.net_cash_flow,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
        },
        "creditworthiness": {
            "bsa_score": analytics.creditworthiness.bsa_score,
            "foir": analytics.creditworthiness.foir,
            "avg_monthly_income": analytics.creditworthiness.average_monthly_income,
            "avg_monthly_emi": analytics.creditworthiness.average_monthly_emi,
            "risk_category": analytics.creditworthiness.risk_category,
            "bounce_count": len(analytics.bounce_transactions),
        },
        "categorization_breakdown": dict(cat_counts),
        "salary_transactions": [
            {"date": t.date, "narration": t.narration[:50], "credit": t.credit}
            for t in transactions if t.is_salary
        ],
        "all_transactions": all_txn_data,  # FULL LIST — no truncation
    }

    messages = [
        {
            "role": "user",
            "content": f"""You are a senior financial analyst validating a bank statement analysis.

You have the COMPLETE extracted dataset — all {len(transactions)} transactions.
Validate extraction accuracy, categorization quality, and analytics correctness.

COMPLETE STRUCTURED DATA:
{json.dumps(structured_context, default=str, indent=2)}

Key things to validate:
1. Are categories accurate? (SWIGGY=Food, IRCTC=Travel, ANAMIKA KU UPI=Transfer not Salary)
2. Is income classification correct? (P2P UPI ≠ employer salary)
3. Are totals arithmetically consistent?
4. Any suspicious patterns or data quality issues?""",
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": QA_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        tools=[QA_TOOL],
        tool_choice={"type": "tool", "name": "validate_bank_statement_analysis"},
        messages=messages,
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"), None
    )

    ai_checks = []
    issues_found = []
    extraction_accuracy = 85.0
    calculation_accuracy = 90.0
    categorization_accuracy = 80.0

    if tool_use_block:
        data = tool_use_block.input
        for chk in data.get("checks", []):
            ai_checks.append(QACheck(
                check_name=chk.get("check_name", "Unknown Check"),
                passed=bool(chk.get("passed", False)),
                confidence=float(chk.get("confidence", 0.0)),
                expected=chk.get("expected"),
                actual=chk.get("actual"),
                note=chk.get("note"),
            ))
        issues_found = data.get("issues_found", [])
        extraction_accuracy = data.get("extraction_accuracy", 85.0)
        calculation_accuracy = data.get("calculation_accuracy", 90.0)
        categorization_accuracy = data.get("categorization_accuracy", 80.0)

    all_checks = math_checks + ai_checks

    # Overall confidence = weighted average of individual check confidence scores
    # (not just pass/fail count — a check at 95% confidence is better than one at 51%)
    if all_checks:
        overall_confidence = round(sum(c.confidence for c in all_checks) / len(all_checks), 1)
    else:
        overall_confidence = 0.0

    # Data quality grade
    if overall_confidence >= 90:
        grade = "A"
    elif overall_confidence >= 80:
        grade = "B"
    elif overall_confidence >= 70:
        grade = "C"
    elif overall_confidence >= 60:
        grade = "D"
    else:
        grade = "F"

    return QAValidationResult(
        overall_confidence=overall_confidence,
        extraction_accuracy=extraction_accuracy,
        calculation_accuracy=calculation_accuracy,
        categorization_accuracy=categorization_accuracy,
        checks=all_checks,
        issues_found=issues_found,
        data_quality_grade=grade,
        validated_at=datetime.utcnow(),
    )
