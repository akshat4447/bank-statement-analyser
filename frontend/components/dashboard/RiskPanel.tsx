import { CreditworthinessMetrics, Transaction } from "@/lib/types";
import { AlertTriangle, CheckCircle, Info, ShieldAlert, XCircle } from "lucide-react";
import { formatINR } from "@/lib/utils";

const SEVERITY_STYLES = {
  high: "bg-red-500/5 border-red-500/20 text-red-300",
  medium: "bg-amber-500/5 border-amber-500/20 text-amber-300",
  low: "bg-blue-500/5 border-blue-500/20 text-blue-300",
};
const SEVERITY_ICONS = { high: AlertTriangle, medium: AlertTriangle, low: Info };

interface Props { cw: CreditworthinessMetrics; gamblingTxns?: Transaction[] }

export default function RiskPanel({ cw, gamblingTxns = [] }: Props) {
  const foirOk = !cw.foir || cw.foir <= 50;

  return (
    <div className="space-y-5">
      {/* Score overview */}
      <div className="card">
        <h3 className="section-title"><ShieldAlert className="w-4 h-4 text-[#00d4aa]" /> Risk Score Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "BSA Score", value: `${cw.bsa_score}/100`, ok: cw.bsa_score >= 60, desc: "Composite risk score" },
            { label: "FOIR", value: cw.foir ? `${cw.foir}%` : "N/A", ok: foirOk, desc: "< 50% is healthy" },
            { label: "Income Stability", value: `${cw.income_stability_index.toFixed(0)}/100`, ok: cw.income_stability_index >= 60, desc: "Salary consistency" },
            { label: "Risk Category", value: cw.risk_category, ok: ["LOW", "MEDIUM"].includes(cw.risk_category), desc: "Overall rating" },
          ].map(item => (
            <div key={item.label} className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
              <p className="stat-label mb-2">{item.label}</p>
              <p className={`text-xl font-black ${item.ok ? "text-slate-100" : "text-red-400"}`}>{item.value}</p>
              <p className="text-xs text-slate-600 mt-0.5">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Income vs obligations bar */}
      <div className="card">
        <h3 className="section-title">Income vs Obligations</h3>
        <div className="space-y-4">
          {[
            { label: "Monthly Income", amount: cw.average_monthly_income, color: "#00d4aa", pct: 100 },
            { label: "Monthly EMI", amount: cw.average_monthly_emi, color: "#ef4444", pct: cw.average_monthly_income > 0 ? (cw.average_monthly_emi / cw.average_monthly_income) * 100 : 0 },
            { label: "Disposable Income", amount: cw.disposable_income, color: "#3b82f6", pct: cw.average_monthly_income > 0 ? (cw.disposable_income / cw.average_monthly_income) * 100 : 0 },
          ].map(item => (
            <div key={item.label}>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-slate-400">{item.label}</span>
                <span className="font-semibold text-slate-200">{formatINR(item.amount)}</span>
              </div>
              <div className="h-2 bg-[#1e2d45] rounded-full overflow-hidden">
                <div className="h-2 rounded-full transition-all duration-1000"
                  style={{ width: `${Math.max(0, Math.min(100, item.pct))}%`, background: item.color }} />
              </div>
            </div>
          ))}
        </div>
        {cw.max_eligible_emi && (
          <div className="mt-4 p-3 rounded-xl border text-sm"
            style={{ background: "rgba(0,212,170,0.05)", borderColor: "rgba(0,212,170,0.2)" }}>
            <span className="text-[#00d4aa] font-semibold">Max additional EMI: </span>
            <span className="font-bold text-slate-200">{formatINR(cw.max_eligible_emi)}/month</span>
            <span className="text-slate-500 ml-1">(50% income rule)</span>
          </div>
        )}
      </div>

      {/* Risk flags */}
      <div className="card">
        <h3 className="section-title">Risk Flags ({cw.risk_flags.length})</h3>
        {cw.risk_flags.length === 0 ? (
          <div className="flex items-center gap-2 text-[#00d4aa] py-4">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">No risk flags detected — clean profile</span>
          </div>
        ) : (
          <div className="space-y-2">
            {cw.risk_flags.map((flag, i) => {
              const Icon = SEVERITY_ICONS[flag.severity as keyof typeof SEVERITY_ICONS] || Info;
              return (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border text-sm ${SEVERITY_STYLES[flag.severity as keyof typeof SEVERITY_STYLES]}`}>
                  <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-xs uppercase tracking-wide mb-0.5 opacity-70">{flag.flag_type.replace(/_/g, " ")}</div>
                    <div className="text-sm">{flag.description}</div>
                    {flag.evidence && <div className="text-xs mt-0.5 opacity-60">{flag.evidence}</div>}
                  </div>
                  <span className={`text-xs font-bold uppercase flex-shrink-0 px-2 py-0.5 rounded-full ${flag.severity === "high" ? "bg-red-500/20 text-red-400" : flag.severity === "medium" ? "bg-amber-500/20 text-amber-400" : "bg-blue-500/20 text-blue-400"}`}>
                    {flag.severity}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Gambling / high-risk */}
      {gamblingTxns.length > 0 && (
        <div className="card" style={{ borderColor: "rgba(239,68,68,0.3)" }}>
          <h3 className="section-title text-red-400">
            <XCircle className="w-4 h-4 text-red-400" /> Gambling / High-Risk Transactions ({gamblingTxns.length})
          </h3>
          <table className="data-table">
            <thead><tr><th>Date</th><th>Merchant</th><th className="text-right">Amount</th></tr></thead>
            <tbody>
              {gamblingTxns.slice(0, 10).map((t, i) => (
                <tr key={i}>
                  <td className="text-slate-500 text-xs">{t.date}</td>
                  <td className="font-medium text-red-300">{t.narration.slice(0, 50)}</td>
                  <td className="text-right font-semibold text-red-400">-₹{t.debit?.toLocaleString("en-IN")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
