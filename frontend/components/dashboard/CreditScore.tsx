import { AnalyticsResult } from "@/lib/types";
import { formatINR, formatINRShort } from "@/lib/utils";
import { TrendingUp, TrendingDown, CheckCircle, AlertTriangle, XCircle } from "lucide-react";

const ScoreArc = ({ score }: { score: number }) => {
  const color = score >= 75 ? "#00d4aa" : score >= 55 ? "#f59e0b" : "#ef4444";
  const r = 60, cx = 80, cy = 80;
  const circumference = Math.PI * r; // half circle
  const dash = (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-40 h-24">
        <svg viewBox="0 0 160 90" className="w-40 h-24">
          {/* Background arc */}
          <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="#1e2d45" strokeWidth="10" strokeLinecap="round" />
          {/* Score arc */}
          <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
            style={{ transition: "stroke-dasharray 1.2s ease-out" }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-0">
          <span className="text-4xl font-black" style={{ color }}>{score}</span>
          <span className="text-xs text-slate-500">out of 100</span>
        </div>
      </div>
    </div>
  );
};

const ScoreBar = ({ label, value, max = 20, color }: { label: string; value: number; max?: number; color: string }) => (
  <div>
    <div className="flex justify-between text-xs text-slate-400 mb-1">
      <span>{label}</span><span>{value.toFixed(1)}/{max}</span>
    </div>
    <div className="h-1.5 bg-[#1e2d45] rounded-full overflow-hidden">
      <div className="h-1.5 rounded-full transition-all duration-1000"
        style={{ width: `${(value / max) * 100}%`, background: color }} />
    </div>
  </div>
);

interface Props { analytics: AnalyticsResult }

export default function CreditScore({ analytics }: Props) {
  const cw = analytics.creditworthiness;
  const uw = analytics.underwriter;

  const verdictClass = uw?.verdict === "APPROVE" ? "verdict-approve" : uw?.verdict === "REVIEW" ? "verdict-review" : "verdict-reject";
  const verdictIcon = uw?.verdict === "APPROVE" ? <CheckCircle className="w-4 h-4" /> : uw?.verdict === "REJECT" ? <XCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />;

  return (
    <div className="space-y-5">
      {/* Score + underwriter */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Score */}
        <div className="card col-span-1 flex flex-col items-center text-center">
          <p className="section-title justify-center">BSA Score</p>
          <ScoreArc score={cw.bsa_score} />
          <p className={`text-lg font-bold mt-2 ${cw.risk_category === "LOW" ? "text-[#00d4aa]" : cw.risk_category === "MEDIUM" ? "text-amber-400" : "text-red-400"}`}>
            {cw.risk_category} RISK
          </p>
          <div className="mt-4 w-full space-y-2">
            <ScoreBar label="Income Stability" value={cw.score_income_stability} color="#00d4aa" />
            <ScoreBar label="Cash Flow Health" value={cw.score_cash_flow} color="#3b82f6" />
            <ScoreBar label="Balance Behavior" value={cw.score_balance_behavior} color="#a855f7" />
            <ScoreBar label="Debt Burden" value={cw.score_debt_burden} color="#f59e0b" />
            <ScoreBar label="Risk Events" value={cw.score_risk_events} color="#22c55e" />
          </div>
        </div>

        {/* Underwriter recommendation */}
        <div className="card col-span-2">
          <p className="section-title">Underwriter Recommendation</p>
          {uw ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className={verdictClass}>{verdictIcon} {uw.verdict}</span>
                <span className="text-xs text-slate-500">{uw.confidence.toFixed(0)}% confidence</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
                  <p className="stat-label mb-1">Suggested Loan</p>
                  <p className="text-2xl font-black text-slate-100">₹{(uw.suggested_loan_amount / 100000).toFixed(1)}L</p>
                </div>
                <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
                  <p className="stat-label mb-1">EMI Capacity</p>
                  <p className="text-2xl font-black text-slate-100">{formatINRShort(uw.suggested_emi_capacity)}/mo</p>
                </div>
              </div>

              {uw.key_reasons.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2 font-medium">Key Reasons</p>
                  <div className="space-y-1.5">
                    {uw.key_reasons.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <CheckCircle className="w-3.5 h-3.5 text-[#00d4aa] mt-0.5 flex-shrink-0" />
                        {r}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {uw.manual_review_triggers.length > 0 && (
                <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3">
                  <p className="text-xs text-amber-400 font-semibold mb-2 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Manual Review Triggers
                  </p>
                  {uw.manual_review_triggers.map((t, i) => (
                    <p key={i} className="text-xs text-amber-300 mt-1">• {t}</p>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">Underwriter data not available</p>
          )}
        </div>
      </div>

      {/* Financial metrics */}
      <div className="card">
        <p className="section-title">Detailed Metrics</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "FOIR", value: cw.foir ? `${cw.foir}%` : "N/A", ok: !cw.foir || cw.foir <= 50, desc: "< 50% is healthy" },
            { label: "Income Stability", value: `${cw.income_stability_index.toFixed(0)}/100`, ok: cw.income_stability_index >= 60, desc: "Salary consistency" },
            { label: "Avg Monthly Income", value: formatINRShort(cw.average_monthly_income), ok: true, desc: "Primary income" },
            { label: "Monthly EMI", value: formatINRShort(cw.average_monthly_emi), ok: cw.average_monthly_emi < cw.average_monthly_income * 0.5, desc: "Existing obligations" },
            { label: "Disposable Income", value: formatINRShort(cw.disposable_income), ok: cw.disposable_income > 0, desc: "After EMIs" },
            { label: "Max New EMI", value: formatINRShort(cw.max_eligible_emi || 0), ok: true, desc: "50% income rule" },
            { label: "Savings Rate", value: `${analytics.savings_rate.toFixed(1)}%`, ok: analytics.savings_rate >= 10, desc: "Net / Total credits" },
            { label: "Spend-to-Income", value: `${analytics.spend_to_income_ratio.toFixed(1)}%`, ok: analytics.spend_to_income_ratio <= 80, desc: "Expense / Income" },
          ].map((m) => (
            <div key={m.label} className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
              <p className="stat-label mb-1">{m.label}</p>
              <p className={`text-xl font-bold ${m.ok ? "text-slate-100" : "text-red-400"}`}>{m.value}</p>
              <p className="text-xs text-slate-600 mt-0.5">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
