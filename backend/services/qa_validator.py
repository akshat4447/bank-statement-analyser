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


def _math_checks(transactions: list[Transaction], analytics: AnalyticsResult) -> list[QACheck]:
    """Pure math validation — no AI needed, just verify numbers."""
    checks = []

    # Sum credits
    computed_credits = sum(t.credit for t in transactions if t.credit)
    diff_c = abs(computed_credits - analytics.total_credits)
    checks.append(QACheck(
        check_name="Total Credits Match",
        passed=diff_c < 1.0,
        confidence=100.0 if diff_c < 1.0 else max(0.0, 100.0 - diff_c / analytics.total_credits * 100),
        expected=f"₹{computed_credits:,.2f}",
        actual=f"₹{analytics.total_credits:,.2f}",
        note=f"Difference: ₹{diff_c:,.2f}" if diff_c >= 1.0 else None,
    ))

    # Sum debits
    computed_debits = sum(t.debit for t in transactions if t.debit)
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
    expected_ncf = analytics.total_credits - analytics.total_debits
    diff_n = abs(expected_ncf - analytics.net_cash_flow)
    checks.append(QACheck(
        check_name="Net Cash Flow Calculation",
        passed=diff_n < 0.01,
        confidence=100.0 if diff_n < 0.01 else 50.0,
        expected=f"₹{expected_ncf:,.2f}",
        actual=f"₹{analytics.net_cash_flow:,.2f}",
    ))

    # Balance progression: check if balance = prev_balance +/- transaction
    sorted_txns = sorted(transactions, key=lambda x: x.date)
    balance_errors = 0
    for i in range(1, min(len(sorted_txns), 50)):  # Check first 50
        prev = sorted_txns[i - 1]
        curr = sorted_txns[i]
        if prev.balance is None or curr.balance is None:
            continue
        expected_bal = prev.balance + (curr.credit or 0) - (curr.debit or 0)
        if abs(expected_bal - curr.balance) > 2.0:
            balance_errors += 1

    balance_check_count = min(len(sorted_txns) - 1, 49)
    balance_accuracy = (1 - balance_errors / max(balance_check_count, 1)) * 100
    checks.append(QACheck(
        check_name="Balance Progression Validity",
        passed=balance_accuracy >= 80,
        confidence=round(balance_accuracy, 1),
        note=f"{balance_errors} balance discrepancies in first {balance_check_count} transactions",
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
    Math checks run instantly; AI validates extraction quality and categorization.
    """
    # Math checks (deterministic)
    math_checks = _math_checks(transactions, analytics)

    # Build compact context for AI validation (keep it tight to save tokens)
    sample_txns = transactions[:30]  # Sample for AI review
    txn_sample_text = "\n".join([
        f"{t.date} | {t.narration[:50]} | {f'CR {t.credit}' if t.credit else f'DR {t.debit}'} | {t.category.value if t.category else 'Uncategorized'}"
        for t in sample_txns
    ])

    analytics_summary = {
        "total_credits": analytics.total_credits,
        "total_debits": analytics.total_debits,
        "total_transactions": analytics.total_transactions,
        "avg_monthly_balance": analytics.average_monthly_balance,
        "bsa_score": analytics.creditworthiness.bsa_score,
        "foir": analytics.creditworthiness.foir,
        "avg_monthly_income": analytics.creditworthiness.average_monthly_income,
        "bounce_count": len(analytics.bounce_transactions),
        "risk_category": analytics.creditworthiness.risk_category,
    }

    # Truncate raw text to first 3000 chars for AI validation context
    raw_text_sample = raw_text[:3000] + ("..." if len(raw_text) > 3000 else "")

    messages = [
        {
            "role": "user",
            "content": f"""Validate this bank statement analysis.

ORIGINAL STATEMENT (first 3000 chars):
{raw_text_sample}

SAMPLE EXTRACTED TRANSACTIONS (first 30):
{txn_sample_text}

COMPUTED ANALYTICS:
{json.dumps(analytics_summary, indent=2)}

Total transactions extracted: {len(transactions)}

Please validate extraction accuracy, categorization quality, and analytics correctness.""",
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

    # Derive overall confidence
    passed_checks = sum(1 for c in all_checks if c.passed)
    overall_confidence = round(passed_checks / max(len(all_checks), 1) * 100, 1)

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
