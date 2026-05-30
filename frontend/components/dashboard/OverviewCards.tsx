import { AnalyticsResult, AccountInfo } from "@/lib/types";
import { formatINRShort } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle, Activity, Building2 } from "lucide-react";

const MetricCard = ({ label, value, sub, color = "text-slate-100", icon }: {
  label: string; value: string; sub?: string; color?: string; icon?: React.ReactNode;
}) => (
  <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</span>
      {icon && <span className="text-slate-600">{icon}</span>}
    </div>
    <div className={`text-2xl font-black ${color}`}>{value}</div>
    {sub && <div className="text-xs text-slate-600 mt-0.5">{sub}</div>}
  </div>
);

const ScoreRing = ({ score }: { score: number }) => {
  const color = score >= 75 ? "#00d4aa" : score >= 60 ? "#f59e0b" : "#ef4444";
  const r = 32, circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45] flex items-center gap-4">
      <div className="relative w-20 h-20 flex-shrink-0">
        <svg viewBox="0 0 72 72" className="w-20 h-20 -rotate-90">
          <circle cx="36" cy="36" r={r} fill="none" stroke="#1e2d45" strokeWidth="6" />
          <circle cx="36" cy="36" r={r} fill="none" stroke={color} strokeWidth="6"
            strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
            style={{ transition: "stroke-dasharray 1.2s ease-out" }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-black" style={{ color }}>{score}</span>
        </div>
      </div>
      <div>
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">BSA Score</div>
        <div className="text-sm font-bold text-slate-200">out of 100</div>
        <div className="text-xs text-slate-500 mt-1">Financial health index</div>
      </div>
    </div>
  );
};

interface Props { analytics: AnalyticsResult; accountInfo?: AccountInfo }

export default function OverviewCards({ analytics, accountInfo }: Props) {
  const cw = analytics.creditworthiness;
  const ncf = analytics.net_cash_flow;

  const riskColors: Record<string, string> = {
    LOW: "text-[#00d4aa]", MEDIUM: "text-amber-400", HIGH: "text-red-400", "VERY HIGH": "text-red-600",
  };

  return (
    <div className="space-y-5">
      {/* Account header */}
      {accountInfo && (
        <div className="card" style={{ background: "linear-gradient(135deg, #0d1e35 0%, #0a1628 100%)", borderColor: "#1e3a5c" }}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ background: "rgba(0,212,170,0.1)", border: "1px solid rgba(0,212,170,0.2)" }}>
                <Building2 className="w-6 h-6 text-[#00d4aa]" />
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wide">Account Holder</p>
                <p className="text-xl font-black text-slate-100">{accountInfo.account_holder || "—"}</p>
                <p className="text-slate-500 text-sm mt-0.5">
                  {accountInfo.bank_name} {accountInfo.account_type ? `· ${accountInfo.account_type}` : ""}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-slate-500 text-xs uppercase tracking-wide mb-1">Transaction Period</p>
              <p className="font-bold text-slate-200">{analytics.actual_period_from} → {analytics.actual_period_to}</p>
              <p className="text-slate-600 text-xs mt-1">A/C: {accountInfo.account_number || "—"}</p>
            </div>
          </div>
        </div>
      )}

      {/* BSA + Risk */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ScoreRing score={cw.bsa_score} />
        <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Risk Category</span>
          <div className={`text-3xl font-black mt-2 ${riskColors[cw.risk_category] || "text-slate-100"}`}>
            {cw.risk_category}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            FOIR: {cw.foir ? `${cw.foir}%` : "N/A"} · Stability: {cw.income_stability_index.toFixed(0)}/100
          </div>
          {cw.risk_flags.length > 0 && (
            <div className="mt-2 flex items-center gap-1 text-xs text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5" /> {cw.risk_flags.length} risk flag(s) detected
            </div>
          )}
        </div>
      </div>

      {/* Core metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Total Credits" value={formatINRShort(analytics.total_credits)}
          sub={`${analytics.analysis_period_months} months`} color="text-[#00d4aa]"
          icon={<TrendingUp className="w-4 h-4 text-[#00d4aa]" />} />
        <MetricCard label="Total Debits" value={formatINRShort(analytics.total_debits)}
          color="text-red-400" icon={<TrendingDown className="w-4 h-4 text-red-400" />} />
        <MetricCard label="Net Cash Flow" value={formatINRShort(ncf)}
          color={ncf >= 0 ? "text-[#00d4aa]" : "text-red-400"}
          icon={ncf > 0 ? <TrendingUp className="w-4 h-4 text-[#00d4aa]" /> : <TrendingDown className="w-4 h-4 text-red-400" />} />
        <MetricCard label="Avg Balance"
          value={formatINRShort(analytics.average_monthly_balance)}
          sub={`Min ₹${(analytics.min_balance/1000).toFixed(1)}K · Max ₹${(analytics.max_balance/1000).toFixed(1)}K`}
          icon={<Activity className="w-4 h-4 text-slate-500" />} />
      </div>

      {/* Income / EMI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Avg Monthly Income" value={formatINRShort(cw.average_monthly_income)} color="text-[#00d4aa]" />
        <MetricCard label="Avg Monthly EMI" value={formatINRShort(cw.average_monthly_emi)} color="text-red-400" />
        <MetricCard label="Disposable Income" value={formatINRShort(cw.disposable_income)}
          sub="After EMIs" color={cw.disposable_income >= 0 ? "text-[#00d4aa]" : "text-red-400"} />
        <MetricCard label="Savings Rate" value={`${analytics.savings_rate?.toFixed(1) ?? 0}%`}
          sub={`Spend: ${analytics.spend_to_income_ratio?.toFixed(1) ?? 0}%`}
          color={analytics.savings_rate >= 10 ? "text-[#00d4aa]" : "text-amber-400"} />
      </div>

      {/* Risk counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Bounces" value={String(analytics.bounce_transactions.length)}
          color={analytics.bounce_transactions.length > 0 ? "text-red-400" : "text-[#00d4aa]"}
          icon={analytics.bounce_transactions.length > 0 ? <AlertTriangle className="w-4 h-4 text-red-400" /> : <CheckCircle className="w-4 h-4 text-[#00d4aa]" />} />
        <MetricCard label="Suspicious" value={String(analytics.suspicious_transactions.length)}
          color={analytics.suspicious_transactions.length > 0 ? "text-amber-400" : "text-[#00d4aa]"} />
        <MetricCard label="Gambling / High-Risk" value={String(analytics.gambling_transactions?.length ?? 0)}
          color={(analytics.gambling_transactions?.length ?? 0) > 0 ? "text-red-400" : "text-[#00d4aa]"} />
        <MetricCard label="Total Transactions" value={String(analytics.total_transactions)}
          sub={`${analytics.analysis_period_months} month(s)`} />
      </div>
    </div>
  );
}
