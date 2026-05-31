"""
Chatbot endpoint — uses Claude Sonnet with analytics JSON context only.
Never passes raw transactions (500 rows × 5 fields = thousands of tokens).
Analytics JSON is ~400-500 tokens. Context is tight and focused.
"""
import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import anthropic

from models.database import get_db, AnalysisRecord
from models.schemas import AnalysisStatus

router = APIRouter()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CHAT_SYSTEM = """You are a financial advisor AI analyzing a customer's bank statement.
You have access to their computed financial analytics. Answer questions clearly and helpfully.

STRICT FORMATTING RULES — follow these exactly:
- Write in plain conversational sentences only
- Never use markdown: no ##, ###, **, *, ---, ___, >, |---|
- Never use tables or code blocks
- Use plain numbered lists (1. 2. 3.) or dashes (- item) only when listing multiple items
- Keep responses under 150 words unless the user explicitly asks for a detailed breakdown
- Never add headers or section titles

Content guidelines:
- Be specific with numbers from the analytics (₹ amounts, percentages)
- For credit/loan questions, reference FOIR, BSA Score, and disposable income
- Flag concerns when relevant (high FOIR, bounce transactions, suspicious activity)
- Use Indian financial context (EMI, FOIR, CIBIL score awareness, etc.)
- Never make up data not present in the analytics
"""

SUGGESTED_CHIPS = [
    "Am I eligible for a home loan?",
    "Where am I spending the most?",
    "What is my FOIR and is it healthy?",
    "What are my biggest financial risks?",
    "How much can I save each month?",
]


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{role: user/assistant, content: str}]


class ChatResponse(BaseModel):
    reply: str
    suggested_chips: list[str]


def _build_analytics_context(record: AnalysisRecord) -> str:
    """Build a compact analytics summary — stays under 500 tokens."""
    if not record.analytics:
        return "No analytics available yet."

    an = record.analytics
    cw = an.get("creditworthiness", {})

    # Spending top 5 categories
    spending = sorted(an.get("spending_breakdown", []), key=lambda x: x.get("amount", 0), reverse=True)[:5]
    spending_summary = ", ".join(
        f"{s['category']}: ₹{s['amount']:,.0f} ({s['percentage']:.0f}%)"
        for s in spending
    )

    # Monthly trend (last 3 months)
    monthly = an.get("monthly_stats", [])[-3:]
    monthly_summary = " | ".join(
        f"{m['month']}: IN ₹{m['total_credits']:,.0f} OUT ₹{m['total_debits']:,.0f}"
        for m in monthly
    )

    # Risk flags
    flags = [f"{f['flag_type']} ({f['severity']})" for f in cw.get("risk_flags", [])]

    context = f"""
ACCOUNT: {record.account_info.get('bank_name', 'Unknown') if record.account_info else 'Unknown'} | {record.account_info.get('account_type', '') if record.account_info else ''}
PERIOD: {record.account_info.get('statement_period_from', '') if record.account_info else ''} to {record.account_info.get('statement_period_to', '') if record.account_info else ''}

FINANCIAL SUMMARY:
- Total Credits: ₹{an.get('total_credits', 0):,.0f}
- Total Debits: ₹{an.get('total_debits', 0):,.0f}
- Net Cash Flow: ₹{an.get('net_cash_flow', 0):,.0f}
- Avg Monthly Balance: ₹{an.get('average_monthly_balance', 0):,.0f}
- Min Balance: ₹{an.get('min_balance', 0):,.0f}
- Total Transactions: {an.get('total_transactions', 0)}
- Analysis Period: {an.get('analysis_period_months', 0)} months

CREDITWORTHINESS:
- BSA Score: {cw.get('bsa_score', 0)}/100
- Risk Category: {cw.get('risk_category', 'Unknown')}
- FOIR: {cw.get('foir', 'N/A')}%
- Avg Monthly Income: ₹{cw.get('average_monthly_income', 0):,.0f}
- Avg Monthly EMI: ₹{cw.get('average_monthly_emi', 0):,.0f}
- Disposable Income: ₹{cw.get('disposable_income', 0):,.0f}
- Max Eligible New EMI: ₹{cw.get('max_eligible_emi', 0):,.0f}
- Income Stability: {cw.get('income_stability_index', 0)}/100
- Bounce Count: {len(an.get('bounce_transactions', []))}
- Suspicious Transactions: {len(an.get('suspicious_transactions', []))}

TOP SPENDING CATEGORIES:
{spending_summary}

RECENT MONTHLY TREND:
{monthly_summary}

RISK FLAGS:
{', '.join(flags) if flags else 'None detected'}
""".strip()

    return context


@router.post("/chat/{analysis_id}", response_model=ChatResponse)
async def chat_with_analysis(
    analysis_id: str,
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(404, "Analysis not found")
    if record.status != AnalysisStatus.COMPLETED.value:
        raise HTTPException(400, "Analysis not complete yet")

    analytics_context = _build_analytics_context(record)

    # Build message history (last 6 turns to keep context tight)
    messages = []
    for turn in req.history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": req.message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=[
            {
                "type": "text",
                "text": CHAT_SYSTEM + f"\n\nBANK STATEMENT ANALYTICS:\n{analytics_context}",
                "cache_control": {"type": "ephemeral"},  # Cache the analytics context
            }
        ],
        messages=messages,
    )

    reply = response.content[0].text if response.content else "I couldn't generate a response."

    return ChatResponse(reply=reply, suggested_chips=SUGGESTED_CHIPS)


@router.get("/chat/{analysis_id}/chips")
async def get_suggested_chips():
    """Returns suggested question chips for the chatbot UI."""
    return {"chips": SUGGESTED_CHIPS}
