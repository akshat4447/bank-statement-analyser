"""
Analytics engine: computes all financial metrics from classified transactions.
Produces FOIR, BSA Score, AMB, cash flow trends, creditworthiness indicators.
"""
from collections import defaultdict
from datetime import datetime
from typing import List, Optional
import re

import pandas as pd
import numpy as np

from models.schemas import (
    Transaction, AccountInfo, AnalyticsResult, MonthlyStats,
    SpendingCategory, CreditworthinessMetrics, RiskFlag, TransactionCategory,
    MerchantSpend, IncomeSource, UnderwriterRecommendation, StatementQuality,
)
from services.transaction_classifier import extract_merchant


def _parse_date(date_str: str) -> Optional[datetime]:
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y",
        "%d/%m/%y", "%d-%m-%y", "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _compute_bsa_score(
    income_stability: float,
    foir: Optional[float],
    bounce_count: int,
    avg_balance: float,
    avg_income: float,
    suspicious_count: int,
    months: int,
) -> float:
    """
    BSA Score (0-100): higher = more creditworthy.
    Weighted composite of multiple financial health signals.
    """
    score = 50.0  # Base

    # Income stability (max +20)
    score += (income_stability / 100) * 20

    # FOIR penalty (max -25)
    if foir is not None:
        if foir < 30:
            score += 10
        elif foir < 40:
            score += 5
        elif foir < 50:
            score += 0
        elif foir < 60:
            score -= 10
        elif foir < 70:
            score -= 18
        else:
            score -= 25

    # Balance adequacy (max +15)
    if avg_income > 0:
        balance_ratio = avg_balance / avg_income
        if balance_ratio >= 2:
            score += 15
        elif balance_ratio >= 1:
            score += 10
        elif balance_ratio >= 0.5:
            score += 5
        else:
            score -= 5

    # Bounce penalty (max -20)
    bounce_per_month = bounce_count / max(months, 1)
    if bounce_per_month == 0:
        score += 5
    elif bounce_per_month < 0.5:
        score -= 5
    elif bounce_per_month < 1:
        score -= 12
    else:
        score -= 20

    # Suspicious transaction penalty (max -10)
    if suspicious_count > 0:
        score -= min(suspicious_count * 2, 10)

    return round(max(0.0, min(100.0, score)), 1)


def compute_income_stability(monthly_salaries: List[float]) -> float:
    """0-100 score. Low CV = stable income = high score."""
    if not monthly_salaries or len(monthly_salaries) < 2:
        return 50.0
    arr = np.array(monthly_salaries)
    mean = arr.mean()
    if mean == 0:
        return 0.0
    cv = arr.std() / mean  # Coefficient of variation
    # cv=0 → 100, cv=0.5 → 50, cv≥1 → 0
    stability = max(0.0, 100.0 * (1 - cv * 2))
    return round(stability, 1)


def detect_fraud_signals(transactions: List[Transaction], monthly_income: float) -> List[RiskFlag]:
    flags = []

    credits = [t for t in transactions if t.credit and not t.is_salary]
    debits = [t for t in transactions if t.debit]

    # High cash dependency
    cash_txns = [t for t in transactions if t.category == TransactionCategory.CASH]
    cash_total = sum((t.debit or 0) + (t.credit or 0) for t in cash_txns)
    total_volume = sum((t.debit or 0) + (t.credit or 0) for t in transactions)
    if total_volume > 0 and cash_total / total_volume > 0.3:
        flags.append(RiskFlag(
            flag_type="HIGH_CASH_DEPENDENCY",
            severity="medium",
            description=f"Cash transactions are {cash_total/total_volume*100:.0f}% of total volume",
            evidence=f"Cash volume: ₹{cash_total:,.0f}",
        ))

    # Sudden large credit spikes (>5x avg monthly income)
    if monthly_income > 0:
        for t in credits:
            if t.credit and t.credit > 5 * monthly_income:
                flags.append(RiskFlag(
                    flag_type="LARGE_UNUSUAL_CREDIT",
                    severity="high",
                    description=f"Unusually large credit of ₹{t.credit:,.0f}",
                    evidence=f"{t.date}: {t.narration}",
                ))

    # Round tripping: credit followed immediately by similar debit
    sorted_txns = sorted(transactions, key=lambda x: x.date)
    for i in range(len(sorted_txns) - 1):
        t1, t2 = sorted_txns[i], sorted_txns[i + 1]
        if t1.date == t2.date and t1.credit and t2.debit:
            if abs((t1.credit - t2.debit) / max(t1.credit, 1)) < 0.05:
                flags.append(RiskFlag(
                    flag_type="ROUND_TRIPPING",
                    severity="high",
                    description="Possible round-trip transaction detected",
                    evidence=f"{t1.date}: Credit ₹{t1.credit:,.0f} then Debit ₹{t2.debit:,.0f}",
                ))

    # Structuring: multiple credits just below round numbers (smurfing)
    credit_amounts = [t.credit for t in credits if t.credit]
    suspicious_amounts = [a for a in credit_amounts if 90000 <= a <= 99999 or 45000 <= a <= 49999]
    if len(suspicious_amounts) >= 3:
        flags.append(RiskFlag(
            flag_type="POSSIBLE_STRUCTURING",
            severity="high",
            description="Multiple credits just below round-number thresholds (structuring pattern)",
            evidence=f"{len(suspicious_amounts)} transactions between ₹45K-50K or ₹90K-1L",
        ))

    return flags


def run_analytics(
    transactions: List[Transaction],
    account_info: AccountInfo,
) -> AnalyticsResult:
    """Main analytics computation entry point."""
    if not transactions:
        raise ValueError("No transactions to analyze")

    # Build DataFrame
    rows = []
    for t in transactions:
        dt = _parse_date(t.date)
        rows.append({
            "date": dt,
            "date_str": t.date,
            "narration": t.narration,
            "debit": t.debit or 0.0,
            "credit": t.credit or 0.0,
            "balance": t.balance,
            "category": t.category.value if t.category else "Other",
            "is_salary": t.is_salary,
            "is_emi": t.is_emi,
            "is_bounce": t.is_bounce,
            "is_recurring": t.is_recurring,
            "is_suspicious": t.is_suspicious,
        })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date"])
    df = df.sort_values("date")

    total_credits = float(df["credit"].sum())
    total_debits = float(df["debit"].sum())
    net_cash_flow = total_credits - total_debits

    balances = df["balance"].dropna()
    avg_balance = float(balances.mean()) if not balances.empty else 0.0
    min_balance = float(balances.min()) if not balances.empty else 0.0
    max_balance = float(balances.max()) if not balances.empty else 0.0

    # Monthly grouping
    df["month"] = df["date"].dt.to_period("M")
    monthly_groups = df.groupby("month")

    monthly_stats = []
    monthly_salaries = []
    monthly_incomes = []
    monthly_emis = []

    for period, group in monthly_groups:
        month_credits = float(group["credit"].sum())
        month_debits = float(group["debit"].sum())
        month_balances = group["balance"].dropna()
        month_avg_bal = float(month_balances.mean()) if not month_balances.empty else 0.0
        month_min_bal = float(month_balances.min()) if not month_balances.empty else 0.0
        month_max_bal = float(month_balances.max()) if not month_balances.empty else 0.0
        month_salary = float(group[group["is_salary"]]["credit"].sum())
        month_emi = float(group[group["is_emi"]]["debit"].sum())
        bounce_count = int(group["is_bounce"].sum())

        monthly_stats.append(MonthlyStats(
            month=str(period),
            total_credits=month_credits,
            total_debits=month_debits,
            net_cash_flow=month_credits - month_debits,
            average_balance=month_avg_bal,
            min_balance=month_min_bal,
            max_balance=month_max_bal,
            transaction_count=len(group),
            salary_credits=month_salary,
            emi_debits=month_emi,
            bounce_count=bounce_count,
        ))

        monthly_salaries.append(month_salary)
        monthly_incomes.append(month_credits)
        monthly_emis.append(month_emi)

    n_months = max(len(monthly_stats), 1)
    avg_monthly_income = float(np.mean(monthly_incomes)) if monthly_incomes else 0.0
    avg_salary = float(np.mean([s for s in monthly_salaries if s > 0])) if any(s > 0 for s in monthly_salaries) else 0.0
    avg_monthly_emi = float(np.mean(monthly_emis)) if monthly_emis else 0.0

    # Use salary as primary income signal; fall back to total credits
    primary_income = avg_salary if avg_salary > 0 else avg_monthly_income

    foir = round((avg_monthly_emi / primary_income * 100), 1) if primary_income > 0 else None
    disposable_income = primary_income - avg_monthly_emi

    income_stability = compute_income_stability([s for s in monthly_salaries if s > 0])

    bounce_count = int(df["is_bounce"].sum())
    suspicious_count = int(df["is_suspicious"].sum())

    bsa_score = _compute_bsa_score(
        income_stability=income_stability,
        foir=foir,
        bounce_count=bounce_count,
        avg_balance=avg_balance,
        avg_income=primary_income,
        suspicious_count=suspicious_count,
        months=n_months,
    )

    if bsa_score >= 75:
        risk_category = "LOW"
    elif bsa_score >= 60:
        risk_category = "MEDIUM"
    elif bsa_score >= 45:
        risk_category = "HIGH"
    else:
        risk_category = "VERY HIGH"

    # Max eligible EMI: 50% of income - existing EMIs
    max_eligible_emi = max(0.0, primary_income * 0.5 - avg_monthly_emi)

    # Debt service ratio
    dsr = round(avg_monthly_emi / primary_income * 100, 1) if primary_income > 0 else None

    fraud_flags = detect_fraud_signals(transactions, primary_income)
    risk_flags = []

    if bounce_count > 0:
        risk_flags.append(RiskFlag(
            flag_type="BOUNCED_TRANSACTIONS",
            severity="high" if bounce_count > 3 else "medium",
            description=f"{bounce_count} bounced/returned transaction(s) detected",
        ))
    if min_balance < 0:
        risk_flags.append(RiskFlag(
            flag_type="NEGATIVE_BALANCE",
            severity="high",
            description="Account balance went negative",
            evidence=f"Min balance: ₹{min_balance:,.0f}",
        ))
    if foir and foir > 60:
        risk_flags.append(RiskFlag(
            flag_type="HIGH_FOIR",
            severity="high",
            description=f"FOIR of {foir}% exceeds safe lending threshold (50%)",
        ))

    risk_flags.extend(fraud_flags)

    creditworthiness = CreditworthinessMetrics(
        bsa_score=bsa_score,
        foir=foir,
        income_stability_index=income_stability,
        average_monthly_income=round(primary_income, 2),
        average_monthly_emi=round(avg_monthly_emi, 2),
        disposable_income=round(disposable_income, 2),
        debt_service_ratio=dsr,
        max_eligible_emi=round(max_eligible_emi, 2),
        risk_category=risk_category,
        risk_flags=risk_flags,
    )

    # ── Actual statement period from transaction dates (not PDF header) ──────
    actual_period_from = df["date"].min().strftime("%Y-%m-%d") if not df.empty else None
    actual_period_to = df["date"].max().strftime("%Y-%m-%d") if not df.empty else None

    # ── Spending breakdown (exclude Transfer for meaningful donut) ────────────
    from services.transaction_classifier import extract_merchant
    expense_df = df[df["debit"] > 0].copy()
    # Don't count pure transfers in spending breakdown — use all categories
    category_groups = expense_df.groupby("category")["debit"].agg(["sum", "count"])
    total_expense = float(expense_df["debit"].sum())

    spending_breakdown = []
    for cat_name, row in category_groups.iterrows():
        spending_breakdown.append(SpendingCategory(
            category=cat_name,
            amount=round(float(row["sum"]), 2),
            percentage=round(float(row["sum"]) / total_expense * 100, 1) if total_expense > 0 else 0.0,
            transaction_count=int(row["count"]),
        ))
    spending_breakdown.sort(key=lambda x: x.amount, reverse=True)

    # ── Merchant breakdown (top 15 merchants by spend) ────────────────────────
    expense_df["merchant"] = expense_df["narration"].apply(extract_merchant)
    merchant_groups = expense_df.groupby("merchant").agg(
        amount=("debit", "sum"),
        count=("debit", "count"),
        category=("category", lambda x: x.mode()[0] if len(x) > 0 else "Other")
    ).reset_index()
    merchant_groups = merchant_groups.sort_values("amount", ascending=False).head(15)

    merchant_breakdown = [
        MerchantSpend(
            merchant=row["merchant"],
            amount=round(float(row["amount"]), 2),
            count=int(row["count"]),
            category=str(row["category"]),
        )
        for _, row in merchant_groups.iterrows()
    ]

    # ── Income source analysis — flag P2P vs salary ───────────────────────────
    credit_df = df[df["credit"] > 0].copy()
    credit_df["merchant"] = credit_df["narration"].apply(extract_merchant)
    income_groups = credit_df.groupby("merchant").agg(
        total=("credit", "sum"),
        count=("credit", "count"),
        is_salary=("is_salary", "any"),
    ).reset_index().sort_values("total", ascending=False).head(10)

    income_sources = []
    for _, row in income_groups.iterrows():
        merchant_name = str(row["merchant"])
        is_verified = bool(row["is_salary"])
        # P2P flag: personal name, UPI transfer, no company indicators
        is_p2p = _is_likely_personal_transfer(merchant_name, credit_df[credit_df["merchant"] == merchant_name])
        flag = None
        if is_p2p and float(row["total"]) > 1000:
            flag = "⚠️ P2P transfer — unverified income, not salary"
        income_sources.append(IncomeSource(
            source=merchant_name,
            total_amount=round(float(row["total"]), 2),
            transaction_count=int(row["count"]),
            is_verified_salary=is_verified,
            flag=flag,
        ))

    # Flag P2P income in risk flags
    p2p_income = [s for s in income_sources if s.flag]
    if p2p_income:
        total_p2p = sum(s.total_amount for s in p2p_income)
        risk_flags.append(RiskFlag(
            flag_type="UNVERIFIED_INCOME_SOURCE",
            severity="medium",
            description=f"₹{total_p2p:,.0f} income is from P2P transfers, not verifiable salary",
            evidence=", ".join(s.source for s in p2p_income[:3]),
        ))

    # ── UPI dominance ─────────────────────────────────────────────────────────
    upi_count = sum(1 for t in transactions if t.narration.upper().startswith("UPI"))
    upi_pct = round(upi_count / max(len(transactions), 1) * 100, 1)
    if upi_pct > 90:
        risk_flags.append(RiskFlag(
            flag_type="HIGH_UPI_DEPENDENCY",
            severity="low",
            description=f"{upi_pct}% of transactions are UPI — strong digital footprint",
            evidence="Typical for young urban professional",
        ))

    # ── Gambling / high-risk merchant detection ───────────────────────────────
    GAMBLING_KEYWORDS = ["DREAM11", "MPL ", "RUMMY", "POKER", "CASINO", "BET", "GAMBL",
                         "FANTASY", "MY11", "WINZO", "ADDA52", "JUNGLEE", "HOBIGAMES",
                         "CRYPTO", "BINANCE", "COINBASE", "WAZIRX", "ZEBPAY", "COINDCX"]
    gambling_txns = []
    for t in transactions:
        narr_upper = t.narration.upper()
        if any(kw in narr_upper for kw in GAMBLING_KEYWORDS):
            t.category = TransactionCategory.GAMBLING
            t.is_suspicious = True
            gambling_txns.append(t)
    if gambling_txns:
        gambling_total = sum((t.debit or 0) for t in gambling_txns)
        risk_flags.append(RiskFlag(
            flag_type="GAMBLING_HIGH_RISK_MERCHANTS",
            severity="high",
            description=f"₹{gambling_total:,.0f} spent on gambling/crypto/high-risk platforms",
            evidence=", ".join(set(extract_merchant(t.narration) for t in gambling_txns[:3])),
        ))

    # ── Savings rate & spend-to-income ───────────────────────────────────────
    savings_rate = round((net_cash_flow / total_credits * 100), 1) if total_credits > 0 else 0.0
    spend_to_income = round((total_debits / total_credits * 100), 1) if total_credits > 0 else 0.0

    # ── Statement quality ─────────────────────────────────────────────────────
    low_conf = sum(1 for t in transactions if t.confidence < 0.7)
    balance_errors = 0
    sorted_txns = sorted(transactions, key=lambda x: x.date)
    for i in range(1, min(len(sorted_txns), 50)):
        prev, curr = sorted_txns[i-1], sorted_txns[i]
        if prev.balance and curr.balance and curr.debit:
            exp = prev.balance - curr.debit
            if abs(exp - curr.balance) > 5:
                balance_errors += 1
    balance_pass = round((1 - balance_errors / max(min(len(sorted_txns)-1, 49), 1)) * 100, 1)
    quality_score = round((balance_pass * 0.5 + (1 - low_conf / max(len(transactions), 1)) * 100 * 0.5), 1)
    quality_grade = "A" if quality_score >= 90 else "B" if quality_score >= 80 else "C" if quality_score >= 70 else "D" if quality_score >= 60 else "F"
    statement_quality = StatementQuality(
        total_rows_extracted=len(transactions),
        missing_uncertain_rows=low_conf,
        ocr_confidence=round((1 - low_conf / max(len(transactions), 1)) * 100, 1),
        balance_continuity_pass_rate=balance_pass,
        duplicate_rows_detected=0,
        overall_quality_score=quality_score,
        grade=quality_grade,
    )

    # ── Recurring transaction detection ───────────────────────────────────────
    # 🟠 Bug #9 Fix: Detect merchants appearing 2+ times
    from services.recurring_detector import detect_recurring_transactions
    recurring_merchants = detect_recurring_transactions(transactions)

    # Mark transactions as recurring if they belong to a recurring merchant
    recurring_merchant_names = {r.merchant for r in recurring_merchants}
    for t in transactions:
        merchant = extract_merchant(t.narration)
        if merchant in recurring_merchant_names:
            t.is_recurring = True

    recurring_txns = [t for t in transactions if t.is_recurring]

    # ── Underwriter recommendation ────────────────────────────────────────────
    underwriter = _generate_underwriter_rec(
        bsa_score=bsa_score,
        foir=foir,
        bounce_count=bounce_count,
        primary_income=primary_income,
        avg_monthly_emi=avg_monthly_emi,
        risk_flags=risk_flags,
        income_sources=income_sources,
        gambling_count=len(gambling_txns),
    )

    # ── Score component breakdown ─────────────────────────────────────────────
    creditworthiness.score_income_stability = round(min(20, (income_stability / 100) * 20), 1)
    creditworthiness.score_cash_flow = round(min(20, max(0, (1 - abs(spend_to_income - 70) / 100) * 20)), 1)
    creditworthiness.score_balance_behavior = round(min(20, (avg_balance / max(primary_income, 1)) * 10), 1)
    creditworthiness.score_debt_burden = round(min(20, max(0, 20 - (foir or 0) / 5)), 1)
    creditworthiness.score_risk_events = round(max(0, 20 - bounce_count * 4 - len(gambling_txns) * 2), 1)

    return AnalyticsResult(
        total_credits=round(total_credits, 2),
        total_debits=round(total_debits, 2),
        net_cash_flow=round(net_cash_flow, 2),
        average_monthly_balance=round(avg_balance, 2),
        min_balance=round(min_balance, 2),
        max_balance=round(max_balance, 2),
        total_transactions=len(transactions),
        analysis_period_months=n_months,
        actual_period_from=actual_period_from,
        actual_period_to=actual_period_to,
        monthly_stats=monthly_stats,
        spending_breakdown=spending_breakdown,
        merchant_breakdown=merchant_breakdown,
        income_sources=income_sources,
        upi_transaction_percentage=upi_pct,
        savings_rate=savings_rate,
        spend_to_income_ratio=spend_to_income,
        creditworthiness=creditworthiness,
        underwriter=underwriter,
        statement_quality=statement_quality,
        salary_transactions=[t for t in transactions if t.is_salary],
        emi_transactions=[t for t in transactions if t.is_emi],
        bounce_transactions=[t for t in transactions if t.is_bounce],
        suspicious_transactions=[t for t in transactions if t.is_suspicious],
        recurring_transactions=[t for t in transactions if t.is_recurring],
        gambling_transactions=gambling_txns,
    )


def _generate_underwriter_rec(
    bsa_score: float, foir: Optional[float], bounce_count: int,
    primary_income: float, avg_monthly_emi: float,
    risk_flags: list, income_sources: list, gambling_count: int,
) -> UnderwriterRecommendation:
    reasons = []
    triggers = []

    # Decision logic
    reject_triggers = bounce_count > 5 or (foir and foir > 75) or gambling_count > 10
    review_triggers = (bounce_count > 2 or (foir and foir > 55) or
                       any(s.flag for s in income_sources) or gambling_count > 0)

    if reject_triggers:
        verdict = "REJECT"
        verdict_color = "red"
        if bounce_count > 5: reasons.append(f"{bounce_count} bounced transactions indicate payment stress")
        if foir and foir > 75: reasons.append(f"FOIR {foir}% severely exceeds safe threshold")
        if gambling_count > 10: reasons.append("Significant gambling/high-risk spending detected")
    elif review_triggers or bsa_score < 55:
        verdict = "REVIEW"
        verdict_color = "amber"
        if bounce_count > 0: triggers.append(f"Verify reason for {bounce_count} bounce(s)")
        if foir and foir > 55: triggers.append(f"FOIR {foir}% — verify all EMI obligations")
        if any(s.flag for s in income_sources): triggers.append("Income source verification required (P2P transfers)")
        if gambling_count > 0: triggers.append(f"Review {gambling_count} gambling/high-risk transactions")
        reasons.append(f"BSA Score {bsa_score}/100 requires manual review")
    else:
        verdict = "APPROVE"
        verdict_color = "green"
        if foir and foir < 35: reasons.append(f"Low FOIR ({foir}%) — strong repayment capacity")
        if bounce_count == 0: reasons.append("No bounce history — reliable payment track record")
        if bsa_score >= 75: reasons.append(f"Strong BSA Score ({bsa_score}/100)")

    # Loan calculations
    max_safe_emi = max(0.0, primary_income * 0.5 - avg_monthly_emi)
    # Suggested loan: 48x monthly EMI capacity (4-year tenure)
    suggested_loan = round(max_safe_emi * 48 / 1000) * 1000

    return UnderwriterRecommendation(
        verdict=verdict,
        verdict_color=verdict_color,
        suggested_loan_amount=suggested_loan,
        suggested_emi_capacity=round(max_safe_emi, 2),
        key_reasons=reasons[:4],
        manual_review_triggers=triggers[:4],
        confidence=round(min(95, bsa_score + 10), 1),
    )


def _is_likely_personal_transfer(merchant: str, txn_df) -> bool:
    words = merchant.strip().split()
    if len(words) <= 3 and all(w.replace(".", "").isalpha() for w in words if w):
        return True
    return False
