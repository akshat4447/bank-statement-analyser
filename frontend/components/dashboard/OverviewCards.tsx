import { AnalyticsResult, AccountInfo } from "@/lib/types";
import { formatINR, formatINRShort } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle, Activity } from "lucide-react";

const MetricCard = ({
  label, value, sub, color = "text-navy", icon,
}: {
  label: string; value: string; sub?: string; color?: string; icon?: React.ReactNode;
}) => (
  <div className="metric-card">
    <div className="flex items-center justify-between mb-1">
      <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      {icon && <span className="text-gray-300">{icon}</span>}
    </div>
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
  </div>
);

const ScoreRing = ({ score, label }: { score: number; label: string }) => {
  const color = score >= 75 ? "#27ae60" : score >= 60 ? "#f39c12" : "#e74c3c";
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <div className="metric-card flex-row items-center gap-4">
      <div className="relative w-20 h-20 flex-shrink-0">
        <svg viewBox="0 0 72 72" className="w-20 h-20 -rotate-90">
          <circle cx="36" cy="36" r={r} fill="none" stroke="#f0f0f0" strokeWidth="6" />
          <circle
            cx="36" cy="36" r={r} fill="none"
            stroke={color} strokeWidth="6"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 1s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold" style={{ color }}>{score}</span>
        </div>
      </div>
      <div>
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</div>
        <div className="text-sm font-semibold text-navy mt-0.5">out of 100</div>
      </div>
    </div>
  );
};

interface Props {
  analytics: AnalyticsResult;
  accountInfo?: AccountInfo;
}

export default function OverviewCards({ analytics, accountInfo }: Props) {
  const cw = analytics.creditworthiness;
  const ncf = analytics.net_cash_flow;
  const ncfColor = ncf >= 0 ? "text-green-600" : "text-red-600";
  const ncfIcon = ncf > 0 ? <TrendingUp className="w-4 h-4" /> : ncf < 0 ? <TrendingDown className="w-4 h-4" /> : <Minus className="w-4 h-4" />;

  const riskColors: Record<string, string> = {
    LOW: "text-green-600", MEDIUM: "text-amber-500",
    HIGH: "text-red-500", "VERY HIGH": "text-red-700",
  };

  return (
    <div className="space-y-4">
      {/* Account header */}
      {accountInfo && (
        <div className="card bg-navy text-white">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-blue-200 text-xs uppercase tracking-wide">Account Holder</p>
              <p className="text-xl font-bold">{accountInfo.account_holder || "—"}</p>
              <p className="text-blue-200 text-sm mt-0.5">{accountInfo.bank_name} · {accountInfo.account_type}</p>
            </div>
            <div className="text-right">
              <p className="text-blue-200 text-xs">Statement Period</p>
              <p className="font-semibold">{accountInfo.statement_period_from} → {accountInfo.statement_period_to}</p>
              <p className="text-blue-200 text-xs mt-1">A/C: {accountInfo.account_number || "—"}</p>
            </div>
          </div>
        </div>
      )}

      {/* Scores row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ScoreRing score={cw.bsa_score} label="BSA Score" />
        <div className="metric-card">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Risk Category</span>
          <div className={`text-2xl font-bold mt-1 ${riskColors[cw.risk_category] || "text-navy"}`}>
            {cw.risk_category}
          </div>
          <div className="text-xs text-gray-400">
            FOIR: {cw.foir ? `${cw.foir}%` : "N/A"} · Stability: {cw.income_stability_index}/100
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Total Credits"
          value={formatINRShort(analytics.total_credits)}
          sub={`${analytics.analysis_period_months} months`}
          color="text-green-600"
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <MetricCard
          label="Total Debits"
          value={formatINRShort(analytics.total_debits)}
          color="text-red-500"
          icon={<TrendingDown className="w-4 h-4" />}
        />
        <MetricCard
          label="Net Cash Flow"
          value={formatINRShort(ncf)}
          color={ncfColor}
          icon={ncfIcon}
        />
        <MetricCard
          label="Avg Monthly Balance"
          value={formatINRShort(analytics.average_monthly_balance)}
          sub={`Min: ${formatINRShort(analytics.min_balance)}`}
          icon={<Activity className="w-4 h-4" />}
        />
      </div>

      {/* Income / EMI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Avg Monthly Income"
          value={formatINRShort(cw.average_monthly_income)}
          color="text-green-600"
        />
        <MetricCard
          label="Avg Monthly EMI"
          value={formatINRShort(cw.average_monthly_emi)}
          color="text-red-500"
        />
        <MetricCard
          label="Disposable Income"
          value={formatINRShort(cw.disposable_income)}
          sub="After EMIs"
          color={cw.disposable_income >= 0 ? "text-green-600" : "text-red-600"}
        />
        <MetricCard
          label="Max New EMI"
          value={formatINRShort(cw.max_eligible_emi || 0)}
          sub="50% rule"
          color="text-teal"
        />
      </div>

      {/* Bounce & Suspicious */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Bounce Count"
          value={String(analytics.bounce_transactions.length)}
          color={analytics.bounce_transactions.length > 0 ? "text-red-500" : "text-green-600"}
          icon={analytics.bounce_transactions.length > 0
            ? <AlertTriangle className="w-4 h-4 text-red-400" />
            : <CheckCircle className="w-4 h-4 text-green-400" />}
        />
        <MetricCard
          label="Suspicious"
          value={String(analytics.suspicious_transactions.length)}
          color={analytics.suspicious_transactions.length > 0 ? "text-amber-500" : "text-green-600"}
        />
        <MetricCard
          label="EMI Obligations"
          value={String(analytics.emi_transactions.length)}
          sub="recurring"
        />
        <MetricCard
          label="Total Transactions"
          value={String(analytics.total_transactions)}
          sub={`${analytics.analysis_period_months} months`}
        />
      </div>
    </div>
  );
}
