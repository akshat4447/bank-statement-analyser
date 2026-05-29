import { CreditworthinessMetrics } from "@/lib/types";
import { AlertTriangle, CheckCircle, Info, ShieldAlert } from "lucide-react";
import { formatINR } from "@/lib/utils";

const SEVERITY_STYLES = {
  high: "bg-red-50 border-red-200 text-red-700",
  medium: "bg-amber-50 border-amber-200 text-amber-700",
  low: "bg-blue-50 border-blue-200 text-blue-700",
};
const SEVERITY_ICONS = {
  high: AlertTriangle,
  medium: Info,
  low: Info,
};

interface Props { cw: CreditworthinessMetrics }

export default function RiskPanel({ cw }: Props) {
  const foirOk = !cw.foir || cw.foir <= 50;
  const scoreColor = cw.bsa_score >= 75 ? "text-green-600" : cw.bsa_score >= 60 ? "text-amber-500" : "text-red-500";

  return (
    <div className="space-y-5">
      {/* Score breakdown */}
      <div className="card">
        <h3 className="font-semibold text-navy mb-4 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-teal" /> BSA Score Breakdown
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "BSA Score", value: `${cw.bsa_score}/100`, ok: cw.bsa_score >= 60, desc: "Overall risk" },
            { label: "FOIR", value: cw.foir ? `${cw.foir}%` : "N/A", ok: foirOk, desc: "< 50% is good" },
            { label: "Income Stability", value: `${cw.income_stability_index}/100`, ok: cw.income_stability_index >= 60, desc: "Salary consistency" },
            { label: "Risk Category", value: cw.risk_category, ok: cw.risk_category === "LOW" || cw.risk_category === "MEDIUM", desc: "Overall rating" },
          ].map((item) => (
            <div key={item.label} className="bg-gray-50 rounded-xl p-4">
              <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">{item.label}</div>
              <div className={`text-xl font-bold ${item.ok ? "text-green-600" : "text-red-500"}`}>
                {item.value}
              </div>
              <div className="text-xs text-gray-400 mt-0.5">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Income vs obligations */}
      <div className="card">
        <h3 className="font-semibold text-navy mb-4">Income vs Obligations</h3>
        <div className="space-y-3">
          {[
            { label: "Avg Monthly Income", amount: cw.average_monthly_income, color: "bg-green-500", pct: 100 },
            { label: "Avg Monthly EMI", amount: cw.average_monthly_emi, color: "bg-red-500", pct: cw.average_monthly_income > 0 ? (cw.average_monthly_emi / cw.average_monthly_income) * 100 : 0 },
            { label: "Disposable Income", amount: cw.disposable_income, color: "bg-teal", pct: cw.average_monthly_income > 0 ? (cw.disposable_income / cw.average_monthly_income) * 100 : 0 },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">{item.label}</span>
                <span className="font-semibold">{formatINR(item.amount)}</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-1000 ${item.color}`}
                  style={{ width: `${Math.max(0, Math.min(100, item.pct))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        {cw.max_eligible_emi && (
          <div className="mt-4 p-3 bg-teal/5 border border-teal/20 rounded-xl text-sm">
            <span className="text-teal font-semibold">Max additional EMI eligibility: </span>
            <span className="font-bold">{formatINR(cw.max_eligible_emi)}/month</span>
            <span className="text-gray-400 ml-1">(50% income rule)</span>
          </div>
        )}
      </div>

      {/* Risk flags */}
      <div className="card">
        <h3 className="font-semibold text-navy mb-4">Risk Flags</h3>
        {cw.risk_flags.length === 0 ? (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">No risk flags detected</span>
          </div>
        ) : (
          <div className="space-y-2">
            {cw.risk_flags.map((flag, i) => {
              const Icon = SEVERITY_ICONS[flag.severity as keyof typeof SEVERITY_ICONS] || Info;
              return (
                <div
                  key={i}
                  className={`flex items-start gap-3 p-3 rounded-xl border text-sm ${SEVERITY_STYLES[flag.severity as keyof typeof SEVERITY_STYLES] || ""}`}
                >
                  <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-semibold text-xs uppercase tracking-wide mb-0.5">{flag.flag_type}</div>
                    <div>{flag.description}</div>
                    {flag.evidence && <div className="text-xs mt-0.5 opacity-70">{flag.evidence}</div>}
                  </div>
                  <span className="ml-auto text-xs font-bold uppercase opacity-70 flex-shrink-0">{flag.severity}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
