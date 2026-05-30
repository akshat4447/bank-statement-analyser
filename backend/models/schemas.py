from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionCategory(str, Enum):
    SALARY = "Salary"
    EMI = "EMI/Loan Repayment"
    RENT = "Rent"
    UTILITIES = "Utilities"
    FOOD = "Food & Grocery"
    TRAVEL = "Travel & Transport"
    ENTERTAINMENT = "Entertainment"
    INSURANCE = "Insurance"
    INVESTMENTS = "Investments"
    MEDICAL = "Medical"
    SHOPPING = "Shopping"
    EDUCATION = "Education"
    CASH = "Cash Withdrawal/Deposit"
    TRANSFER = "Transfer"
    OTHER = "Other"
    BOUNCE = "Bounce/Return"
    GAMBLING = "Gambling/High-Risk"


class Transaction(BaseModel):
    id: Optional[int] = None
    date: str
    narration: str
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    category: Optional[TransactionCategory] = None
    transaction_type: Optional[TransactionType] = None
    is_salary: bool = False
    is_emi: bool = False
    is_bounce: bool = False
    is_recurring: bool = False
    is_suspicious: bool = False
    confidence: float = 1.0
    tags: List[str] = []


class AccountInfo(BaseModel):
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch: Optional[str] = None
    ifsc: Optional[str] = None
    statement_period_from: Optional[str] = None
    statement_period_to: Optional[str] = None
    account_type: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None


class MonthlyStats(BaseModel):
    month: str
    total_credits: float
    total_debits: float
    net_cash_flow: float
    average_balance: float
    min_balance: float
    max_balance: float
    transaction_count: int
    salary_credits: float
    emi_debits: float
    bounce_count: int


class RiskFlag(BaseModel):
    flag_type: str
    severity: str  # low / medium / high
    description: str
    evidence: Optional[str] = None


class StatementQuality(BaseModel):
    total_rows_extracted: int
    missing_uncertain_rows: int
    ocr_confidence: float = Field(ge=0, le=100)
    balance_continuity_pass_rate: float = Field(ge=0, le=100)
    duplicate_rows_detected: int = 0
    overall_quality_score: float = Field(ge=0, le=100)
    grade: str  # A/B/C/D/F


class UnderwriterRecommendation(BaseModel):
    verdict: str  # APPROVE / REVIEW / REJECT
    verdict_color: str  # green / amber / red
    suggested_loan_amount: float
    suggested_emi_capacity: float
    key_reasons: List[str]
    manual_review_triggers: List[str]
    confidence: float = Field(ge=0, le=100)


class LoanAffordability(BaseModel):
    proposed_emi: float
    new_foir: float
    current_foir: Optional[float]
    is_affordable: bool
    verdict: str
    stress_10pct: str  # verdict if income drops 10%
    stress_20pct: str
    stress_30pct: str
    max_safe_emi: float


class CreditworthinessMetrics(BaseModel):
    bsa_score: float = Field(ge=0, le=100)
    foir: Optional[float] = None
    income_stability_index: float = Field(ge=0, le=100)
    average_monthly_income: float
    average_monthly_emi: float
    disposable_income: float
    debt_service_ratio: Optional[float] = None
    max_eligible_emi: Optional[float] = None
    risk_category: str  # LOW / MEDIUM / HIGH / VERY HIGH
    risk_flags: List[RiskFlag] = []
    # Score component breakdown
    score_income_stability: float = 0
    score_cash_flow: float = 0
    score_balance_behavior: float = 0
    score_debt_burden: float = 0
    score_risk_events: float = 0


class SpendingCategory(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int


class MerchantSpend(BaseModel):
    merchant: str
    amount: float
    count: int
    category: str


class IncomeSource(BaseModel):
    source: str
    total_amount: float
    transaction_count: int
    is_verified_salary: bool
    flag: Optional[str] = None


class AnalyticsResult(BaseModel):
    total_credits: float
    total_debits: float
    net_cash_flow: float
    average_monthly_balance: float
    min_balance: float
    max_balance: float
    total_transactions: int
    analysis_period_months: int
    actual_period_from: Optional[str] = None
    actual_period_to: Optional[str] = None
    monthly_stats: List[MonthlyStats]
    spending_breakdown: List[SpendingCategory]
    merchant_breakdown: List[MerchantSpend] = []
    income_sources: List[IncomeSource] = []
    upi_transaction_percentage: float = 0.0
    savings_rate: float = 0.0
    spend_to_income_ratio: float = 0.0
    creditworthiness: CreditworthinessMetrics
    underwriter: Optional[UnderwriterRecommendation] = None
    statement_quality: Optional[StatementQuality] = None
    salary_transactions: List[Transaction] = []
    emi_transactions: List[Transaction] = []
    bounce_transactions: List[Transaction] = []
    suspicious_transactions: List[Transaction] = []
    recurring_transactions: List[Transaction] = []
    gambling_transactions: List[Transaction] = []


class QACheck(BaseModel):
    check_name: str
    passed: Optional[bool] = False
    confidence: float = Field(ge=0, le=100, default=0.0)
    expected: Optional[str] = None
    actual: Optional[str] = None
    note: Optional[str] = None


class QAValidationResult(BaseModel):
    overall_confidence: float = Field(ge=0, le=100)
    extraction_accuracy: float = Field(ge=0, le=100)
    calculation_accuracy: float = Field(ge=0, le=100)
    categorization_accuracy: float = Field(ge=0, le=100)
    checks: List[QACheck]
    issues_found: List[str]
    data_quality_grade: str  # A / B / C / D / F
    manual_review_required: bool = False
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    account_info: Optional[AccountInfo] = None
    transactions: Optional[List[Transaction]] = None
    analytics: Optional[AnalyticsResult] = None
    qa_result: Optional[QAValidationResult] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    analysis_id: str
    message: str
    status: AnalysisStatus
