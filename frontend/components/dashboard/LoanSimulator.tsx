"use client";
import { useState } from "react";
import { AnalyticsResult, LoanAffordability } from "@/lib/types";
import { loanSimulator } from "@/lib/api";
import { Loader2, Calculator, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { formatINR, formatINRShort } from "@/lib/utils";

interface Props { analysisId: string; analytics: AnalyticsResult }

export default function LoanSimulator({ analysisId, analytics }: Props) {
  const [emi, setEmi] = useState("");
  const [result, setResult] = useState<LoanAffordability | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cw = analytics.creditworthiness;
  const income = cw.average_monthly_income;

  const handleSimulate = async () => {
    const val = parseFloat(emi.replace(/,/g, ""));
    if (!val || val <= 0) { setError("Enter a valid EMI amount"); return; }
    setError(null);
    setLoading(true);
    try {
      const r = await loanSimulator(analysisId, val);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const StressRow = ({ label, verdict }: { label: string; verdict: string }) => {
    const isOk = verdict.includes("✅");
    const isBorder = verdict.includes("⚠️");
    return (
      <div className="flex items-center justify-between py-2 border-b border-[#1e2d45] last:border-0">
        <span className="text-sm text-slate-400">{label}</span>
        <span className={`text-sm font-semibold ${isOk ? "text-[#00d4aa]" : isBorder ? "text-amber-400" : "text-red-400"}`}>
          {verdict}
        </span>
      </div>
    );
  };

  const presets = [
    Math.round(income * 0.2 / 1000) * 1000,
    Math.round(income * 0.3 / 1000) * 1000,
    Math.round(income * 0.4 / 1000) * 1000,
  ].filter(v => v > 0);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Input */}
        <div className="card">
          <h3 className="section-title"><Calculator className="w-4 h-4 text-[#00d4aa]" /> Loan Affordability Simulator</h3>
          <p className="text-sm text-slate-500 mb-4">Enter a proposed monthly EMI to check if it's affordable based on the applicant's income and existing obligations.</p>

          <div className="space-y-4">
            {/* Current context */}
            <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45] text-sm space-y-2">
              <div className="flex justify-between"><span className="text-slate-500">Monthly Income</span><span className="font-semibold text-[#00d4aa]">{formatINR(income)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Existing EMIs</span><span className="font-semibold text-red-400">{formatINR(cw.average_monthly_emi)}</span></div>
              <div className="divider !my-2" />
              <div className="flex justify-between"><span className="text-slate-500">Current FOIR</span><span className="font-semibold text-slate-200">{cw.foir ? `${cw.foir}%` : "N/A"}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Max Safe New EMI</span><span className="font-semibold text-[#00d4aa]">{formatINR(cw.max_eligible_emi || 0)}</span></div>
            </div>

            {/* Input */}
            <div>
              <label className="stat-label block mb-2">Proposed Monthly EMI (₹)</label>
              <input
                type="text"
                className="input-dark text-lg font-bold"
                placeholder="e.g. 15,000"
                value={emi}
                onChange={e => setEmi(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSimulate()}
              />
            </div>

            {/* Presets */}
            {presets.length > 0 && (
              <div className="flex gap-2 flex-wrap">
                {presets.map(p => (
                  <button key={p} onClick={() => setEmi(p.toLocaleString("en-IN"))}
                    className="text-xs px-3 py-1.5 rounded-lg border border-[#1e2d45] text-slate-400 hover:border-[#00d4aa] hover:text-[#00d4aa] transition-all">
                    ₹{(p/1000).toFixed(0)}K
                  </button>
                ))}
              </div>
            )}

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button onClick={handleSimulate} disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
              Simulate Affordability
            </button>
          </div>
        </div>

        {/* Result */}
        <div className="card">
          <h3 className="section-title">Simulation Result</h3>
          {result ? (
            <div className="space-y-4 animate-slide-up">
              {/* Main verdict */}
              <div className={`p-4 rounded-xl border text-center ${result.is_affordable ? "bg-[#00d4aa]/5 border-[#00d4aa]/20" : "bg-red-500/5 border-red-500/20"}`}>
                {result.is_affordable
                  ? <CheckCircle className="w-8 h-8 text-[#00d4aa] mx-auto mb-2" />
                  : <XCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                }
                <p className={`font-bold text-lg ${result.is_affordable ? "text-[#00d4aa]" : "text-red-400"}`}>{result.verdict}</p>
              </div>

              {/* FOIR comparison */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#111827] rounded-xl p-3 border border-[#1e2d45] text-center">
                  <p className="stat-label mb-1">Current FOIR</p>
                  <p className="text-2xl font-black text-slate-300">{result.current_foir?.toFixed(1) ?? "—"}%</p>
                </div>
                <div className={`rounded-xl p-3 border text-center ${result.new_foir > 50 ? "bg-red-500/5 border-red-500/20" : "bg-[#00d4aa]/5 border-[#00d4aa]/20"}`}>
                  <p className="stat-label mb-1">New FOIR</p>
                  <p className={`text-2xl font-black ${result.new_foir > 50 ? "text-red-400" : "text-[#00d4aa]"}`}>{result.new_foir.toFixed(1)}%</p>
                </div>
              </div>

              {/* Stress tests */}
              <div className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
                <p className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wide">Income Stress Scenarios</p>
                <StressRow label="10% income drop" verdict={result.stress_10pct} />
                <StressRow label="20% income drop" verdict={result.stress_20pct} />
                <StressRow label="30% income drop" verdict={result.stress_30pct} />
              </div>

              <div className="text-xs text-slate-500 flex items-start gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                Recommended max EMI: <span className="font-semibold text-slate-300 ml-1">{formatINR(result.max_safe_emi)}/month</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-slate-600">
              <Calculator className="w-10 h-10 mb-3 opacity-30" />
              <p className="text-sm">Enter an EMI amount to simulate</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
