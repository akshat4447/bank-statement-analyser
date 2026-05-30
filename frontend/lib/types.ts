export type TransactionCategory =
  | "Salary" | "EMI/Loan Repayment" | "Rent" | "Utilities"
  | "Food & Grocery" | "Travel & Transport" | "Entertainment"
  | "Insurance" | "Investments" | "Medical" | "Shopping"
  | "Education" | "Cash Withdrawal/Deposit" | "Transfer"
  | "Bounce/Return" | "Other" | "Gambling/High-Risk";

export interface Transaction {
  date: string;
  narration: string;
  debit?: number;
  credit?: number;
  balance?: number;
  category?: TransactionCategory;
  transaction_type?: "credit" | "debit";
  is_salary: boolean;
  is_emi: boolean;
  is_bounce: boolean;
  is_recurring: boolean;
  is_suspicious: boolean;
  confidence: number;
  tags: string[];
}

export interface AccountInfo {
  account_holder?: string;
  account_number?: string;
  bank_name?: string;
  branch?: string;
  ifsc?: string;
  statement_period_from?: string;
  statement_period_to?: string;
  account_type?: string;
  opening_balance?: number;
  closing_balance?: number;
}

export interface MonthlyStats {
  month: string;
  total_credits: number;
  total_debits: number;
  net_cash_flow: number;
  average_balance: number;
  min_balance: number;
  max_balance: number;
  transaction_count: number;
  salary_credits: number;
  emi_debits: number;
  bounce_count: number;
}

export interface RiskFlag {
  flag_type: string;
  severity: "low" | "medium" | "high";
  description: string;
  evidence?: string;
}

export interface StatementQuality {
  total_rows_extracted: number;
  missing_uncertain_rows: number;
  ocr_confidence: number;
  balance_continuity_pass_rate: number;
  duplicate_rows_detected: number;
  overall_quality_score: number;
  grade: string;
}

export interface UnderwriterRecommendation {
  verdict: "APPROVE" | "REVIEW" | "REJECT";
  verdict_color: "green" | "amber" | "red";
  suggested_loan_amount: number;
  suggested_emi_capacity: number;
  key_reasons: string[];
  manual_review_triggers: string[];
  confidence: number;
}

export interface LoanAffordability {
  proposed_emi: number;
  new_foir: number;
  current_foir?: number;
  is_affordable: boolean;
  verdict: string;
  stress_10pct: string;
  stress_20pct: string;
  stress_30pct: string;
  max_safe_emi: number;
}

export interface CreditworthinessMetrics {
  bsa_score: number;
  foir?: number;
  income_stability_index: number;
  average_monthly_income: number;
  average_monthly_emi: number;
  disposable_income: number;
  debt_service_ratio?: number;
  max_eligible_emi?: number;
  risk_category: "LOW" | "MEDIUM" | "HIGH" | "VERY HIGH";
  risk_flags: RiskFlag[];
  score_income_stability: number;
  score_cash_flow: number;
  score_balance_behavior: number;
  score_debt_burden: number;
  score_risk_events: number;
}

export interface SpendingCategory {
  category: string;
  amount: number;
  percentage: number;
  transaction_count: number;
}

export interface MerchantSpend {
  merchant: string;
  amount: number;
  count: number;
  category: string;
}

export interface IncomeSource {
  source: string;
  total_amount: number;
  transaction_count: number;
  is_verified_salary: boolean;
  flag?: string;
}

export interface AnalyticsResult {
  total_credits: number;
  total_debits: number;
  net_cash_flow: number;
  average_monthly_balance: number;
  min_balance: number;
  max_balance: number;
  total_transactions: number;
  analysis_period_months: number;
  actual_period_from?: string;
  actual_period_to?: string;
  monthly_stats: MonthlyStats[];
  spending_breakdown: SpendingCategory[];
  merchant_breakdown: MerchantSpend[];
  income_sources: IncomeSource[];
  upi_transaction_percentage: number;
  savings_rate: number;
  spend_to_income_ratio: number;
  creditworthiness: CreditworthinessMetrics;
  underwriter?: UnderwriterRecommendation;
  statement_quality?: StatementQuality;
  salary_transactions: Transaction[];
  emi_transactions: Transaction[];
  bounce_transactions: Transaction[];
  suspicious_transactions: Transaction[];
  recurring_transactions: Transaction[];
  gambling_transactions: Transaction[];
}

export interface QACheck {
  check_name: string;
  passed: boolean;
  confidence: number;
  expected?: string;
  actual?: string;
  note?: string;
}

export interface QAValidationResult {
  overall_confidence: number;
  extraction_accuracy: number;
  calculation_accuracy: number;
  categorization_accuracy: number;
  checks: QACheck[];
  issues_found: string[];
  data_quality_grade: string;
  manual_review_required: boolean;
  validated_at: string;
}

export type AnalysisStatus =
  | "pending" | "extracting" | "analyzing" | "validating" | "completed" | "failed";

export interface AnalysisResponse {
  analysis_id: string;
  status: AnalysisStatus;
  account_info?: AccountInfo;
  transactions?: Transaction[];
  analytics?: AnalyticsResult;
  qa_result?: QAValidationResult;
  error?: string;
  created_at: string;
  completed_at?: string;
}
