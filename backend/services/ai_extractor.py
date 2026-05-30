"""
Claude Sonnet 4.6 extraction service.
Claude's ONLY job here is structured extraction (Pass 1).
Categorization is handled by the two-tier classifier (regex + Gemini Flash).
Claude is reserved for QA validation and chatbot where quality matters most.
"""
import os
import json
from typing import Tuple

import anthropic
from models.schemas import Transaction, AccountInfo, TransactionCategory
from prompts.extraction import EXTRACTION_SYSTEM_PROMPT, CLASSIFICATION_SYSTEM_PROMPT

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXTRACTION_TOOL = {
    "name": "extract_bank_statement_data",
    "description": "Extract all structured data from a bank statement",
    "input_schema": {
        "type": "object",
        "properties": {
            "account_info": {
                "type": "object",
                "properties": {
                    "account_holder": {"type": ["string", "null"]},
                    "account_number": {"type": ["string", "null"]},
                    "bank_name": {"type": ["string", "null"]},
                    "branch": {"type": ["string", "null"]},
                    "ifsc": {"type": ["string", "null"]},
                    "statement_period_from": {"type": ["string", "null"]},
                    "statement_period_to": {"type": ["string", "null"]},
                    "account_type": {"type": ["string", "null"]},
                    "opening_balance": {"type": ["number", "null"]},
                    "closing_balance": {"type": ["number", "null"]},
                },
            },
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Normalized to YYYY-MM-DD"},
                        "narration": {"type": "string"},
                        "debit": {"type": ["number", "null"]},
                        "credit": {"type": ["number", "null"]},
                        "balance": {"type": ["number", "null"]},
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Extraction confidence for this row",
                        },
                    },
                    "required": ["date", "narration", "confidence"],
                },
            },
        },
        "required": ["account_info", "transactions"],
    },
}

CLASSIFICATION_TOOL = {
    "name": "classify_transactions",
    "description": "Classify transaction categories and identify special transaction types",
    "input_schema": {
        "type": "object",
        "properties": {
            "classified_transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "Salary", "EMI/Loan Repayment", "Rent", "Utilities",
                                "Food & Grocery", "Travel & Transport", "Entertainment",
                                "Insurance", "Investments", "Medical", "Shopping",
                                "Education", "Cash Withdrawal/Deposit", "Transfer",
                                "Bounce/Return", "Other",
                            ],
                        },
                        "is_salary": {"type": "boolean"},
                        "is_emi": {"type": "boolean"},
                        "is_bounce": {"type": "boolean"},
                        "is_recurring": {"type": "boolean"},
                        "is_suspicious": {"type": "boolean"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["index", "category", "is_salary", "is_emi", "is_bounce", "is_recurring", "is_suspicious"],
                },
            }
        },
        "required": ["classified_transactions"],
    },
}


def _chunk_text(text: str, max_chars: int = 80000) -> list[str]:
    """Split large statements into chunks to stay within token limits."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += len(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def extract_transactions_vision(page_images: list[str], bank_name: str = "Unknown") -> Tuple[AccountInfo, list[Transaction]]:
    """
    Claude Vision extraction — sends each page as an image.
    Works for ANY bank format without any text parsing logic.
    """
    all_transactions = []
    account_info = None

    for page_idx, b64_image in enumerate(page_images):
        is_first = page_idx == 0
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64_image,
                },
            },
            {
                "type": "text",
                "text": (
                    f"This is page {page_idx + 1} of a bank statement from {bank_name}.\n"
                    + (
                        "Extract the account information AND every transaction visible in the table. "
                        "For each row: read the date, description/narration, and amounts. "
                        "Determine if each amount is a debit (money OUT) or credit (money IN) "
                        "by reading column headers (Withdrawal/Debit/Dr = debit, Deposit/Credit/Cr = credit) "
                        "or by checking if the running balance decreased (debit) or increased (credit). "
                        "Extract ALL rows — do not skip any."
                        if is_first else
                        "Extract ALL transactions visible on this page. Same rules as before."
                    )
                ),
            },
        ]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=[{"type": "text", "text": EXTRACTION_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_bank_statement_data"},
            messages=[{"role": "user", "content": content}],
        )

        tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use_block:
            continue

        data = tool_use_block.input

        if is_first and data.get("account_info"):
            ai = data["account_info"]
            account_info = AccountInfo(
                account_holder=ai.get("account_holder"),
                account_number=ai.get("account_number"),
                bank_name=ai.get("bank_name") or bank_name,
                branch=ai.get("branch"),
                ifsc=ai.get("ifsc"),
                statement_period_from=ai.get("statement_period_from"),
                statement_period_to=ai.get("statement_period_to"),
                account_type=ai.get("account_type"),
                opening_balance=ai.get("opening_balance"),
                closing_balance=ai.get("closing_balance"),
            )

        for raw_txn in data.get("transactions", []):
            txn = Transaction(
                date=raw_txn.get("date", ""),
                narration=raw_txn.get("narration", ""),
                debit=raw_txn.get("debit"),
                credit=raw_txn.get("credit"),
                balance=raw_txn.get("balance"),
                confidence=raw_txn.get("confidence", 1.0),
            )
            txn.transaction_type = "credit" if txn.credit else "debit"
            all_transactions.append(txn)

    if account_info is None:
        account_info = AccountInfo(bank_name=bank_name)

    return account_info, all_transactions


def extract_transactions(raw_text: str, bank_name: str = "Unknown") -> Tuple[AccountInfo, list[Transaction]]:
    """
    Pass 1: Extract raw transactions from statement text using Claude tool_use.
    Uses prompt caching on the bank statement text for efficiency.
    """
    chunks = _chunk_text(raw_text)
    all_transactions = []
    account_info = None

    for chunk_idx, chunk in enumerate(chunks):
        is_first_chunk = chunk_idx == 0

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Bank: {bank_name}\nChunk {chunk_idx + 1} of {len(chunks)}\n\n"
                                + ("Extract the account information and ALL transactions from this bank statement:\n\n" if is_first_chunk
                                   else "Continue extracting transactions from this next chunk (same statement, no account info needed):\n\n"),
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": chunk,
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            }
        ]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=[
                {
                    "type": "text",
                    "text": EXTRACTION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_bank_statement_data"},
            messages=messages,
        )

        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"), None
        )
        if not tool_use_block:
            continue

        data = tool_use_block.input

        if is_first_chunk and data.get("account_info"):
            ai = data["account_info"]
            account_info = AccountInfo(
                account_holder=ai.get("account_holder"),
                account_number=ai.get("account_number"),
                bank_name=ai.get("bank_name") or bank_name,
                branch=ai.get("branch"),
                ifsc=ai.get("ifsc"),
                statement_period_from=ai.get("statement_period_from"),
                statement_period_to=ai.get("statement_period_to"),
                account_type=ai.get("account_type"),
                opening_balance=ai.get("opening_balance"),
                closing_balance=ai.get("closing_balance"),
            )

        for raw_txn in data.get("transactions", []):
            txn = Transaction(
                date=raw_txn.get("date", ""),
                narration=raw_txn.get("narration", ""),
                debit=raw_txn.get("debit"),
                credit=raw_txn.get("credit"),
                balance=raw_txn.get("balance"),
                confidence=raw_txn.get("confidence", 1.0),
            )
            txn.transaction_type = "credit" if txn.credit else "debit"
            all_transactions.append(txn)

    if account_info is None:
        account_info = AccountInfo(bank_name=bank_name)

    return account_info, all_transactions


def classify_transactions(transactions: list[Transaction], raw_text: str) -> list[Transaction]:
    """
    Pass 2: Classify categories and identify special transaction types.
    Batches transactions to stay within token limits.
    """
    if not transactions:
        return transactions

    # Build compact transaction list for Claude
    txn_list = []
    for i, txn in enumerate(transactions):
        amount = txn.credit if txn.credit else f"-{txn.debit}"
        txn_list.append(f"{i}|{txn.date}|{txn.narration}|{amount}|{txn.balance or ''}")

    txn_text = "\n".join(txn_list)

    # Batch in groups of 200
    batch_size = 200
    classified_map = {}

    for batch_start in range(0, len(transactions), batch_size):
        batch_end = min(batch_start + batch_size, len(transactions))
        batch_text = "\n".join(txn_list[batch_start:batch_end])

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Classify these bank transactions. Format: index|date|narration|amount|balance\n\n",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": batch_text,
                    },
                ],
            }
        ]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=6000,
            system=[
                {
                    "type": "text",
                    "text": CLASSIFICATION_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[CLASSIFICATION_TOOL],
            tool_choice={"type": "tool", "name": "classify_transactions"},
            messages=messages,
        )

        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"), None
        )
        if not tool_use_block:
            continue

        for classified in tool_use_block.input.get("classified_transactions", []):
            real_idx = batch_start + classified["index"]
            classified_map[real_idx] = classified

    # Merge classifications back into transactions
    for i, txn in enumerate(transactions):
        if i in classified_map:
            cls = classified_map[i]
            try:
                txn.category = TransactionCategory(cls["category"])
            except ValueError:
                txn.category = TransactionCategory.OTHER
            txn.is_salary = cls.get("is_salary", False)
            txn.is_emi = cls.get("is_emi", False)
            txn.is_bounce = cls.get("is_bounce", False)
            txn.is_recurring = cls.get("is_recurring", False)
            txn.is_suspicious = cls.get("is_suspicious", False)
            txn.tags = cls.get("tags", [])
        else:
            txn.category = TransactionCategory.OTHER

    return transactions
