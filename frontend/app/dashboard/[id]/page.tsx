"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { AnalysisResponse, AnalysisStatus } from "@/lib/types";
import { getAnalysis, getStatus, getPdfUrl, getExcelUrl } from "@/lib/api";
import { Loader2, Download, FileSpreadsheet, FileText, Bot, CheckCircle, AlertTriangle } from "lucide-react";

import OverviewCards from "@/components/dashboard/OverviewCards";
import TransactionTable from "@/components/dashboard/TransactionTable";
import RiskPanel from "@/components/dashboard/RiskPanel";
import QAReport from "@/components/dashboard/QAReport";
import Chatbot from "@/components/dashboard/Chatbot";
import CashFlowChart from "@/components/charts/CashFlowChart";
import SpendingDonut from "@/components/charts/SpendingDonut";
import BalanceTrendChart from "@/components/charts/BalanceTrendChart";
import IncomeExpenseChart from "@/components/charts/IncomeExpenseChart";
import CreditScore from "@/components/dashboard/CreditScore";
import LoanSimulator from "@/components/dashboard/LoanSimulator";

const STATUS_LABELS: Record<AnalysisStatus, string> = {
  pending: "Initialising pipeline...",
  extracting: "Vision AI extracting transactions...",
  analyzing: "Computing 60+ financial metrics...",
  validating: "Running QA validation...",
  completed: "Analysis complete",
  failed: "Analysis failed",
};

const STATUS_PROGRESS: Record<AnalysisStatus, number> = {
  pending: 8, extracting: 35, analyzing: 70, validating: 88, completed: 100, failed: 100,
};

const STEPS = [
  { label: "Document processing", progress: 8 },
  { label: "Vision AI extraction", progress: 35 },
  { label: "Spend classification", progress: 55 },
  { label: "Financial analytics", progress: 70 },
  { label: "QA validation", progress: 88 },
  { label: "Report generation", progress: 100 },
];

const TABS = [
  { id: "overview", label: "Overview", icon: "📊" },
  { id: "transactions", label: "Transactions", icon: "📋" },
  { id: "cashflow", label: "Cash Flow", icon: "📈" },
  { id: "credit", label: "Creditworthiness", icon: "🏦" },
  { id: "risk", label: "Risk & Flags", icon: "🛡️" },
  { id: "simulator", label: "Loan Simulator", icon: "🧮" },
  { id: "qa", label: "QA Report", icon: "✅" },
  { id: "chat", label: "AI Analyst", icon: "🤖" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>("pending");
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const s = await getStatus(id);
      setStatus(s.status);
      if (s.status === "completed") {
        const full = await getAnalysis(id);
        setData(full);
      } else if (s.status === "failed") {
        setError(s.error || "Analysis failed");
      }
    } catch {
      setError("Could not connect to server");
    }
  }, [id]);

  useEffect(() => {
    poll();
    const interval = setInterval(() => {
      if (status !== "completed" && status !== "failed") poll();
      else clearInterval(interval);
    }, 3000);
    return () => clearInterval(interval);
  }, [poll, status]);

  const progress = STATUS_PROGRESS[status] || 5;

  if (error) return (
    <div className="max-w-xl mx-auto px-4 py-24 text-center">
      <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-8 h-8 text-red-400" />
      </div>
      <h2 className="text-xl font-bold text-slate-100 mb-2">Analysis Failed</h2>
      <p className="text-slate-400 text-sm">{error}</p>
    </div>
  );

  if (status !== "completed") return (
    <div className="max-w-lg mx-auto px-4 py-24">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
          style={{ background: "linear-gradient(135deg, rgba(0,212,170,0.15) 0%, rgba(59,130,246,0.15) 100%)" }}>
          <Loader2 className="w-8 h-8 text-[#00d4aa] animate-spin" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-1">{STATUS_LABELS[status]}</h2>
        <p className="text-slate-500 text-sm">Processing your statement — this takes 20–45 seconds</p>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-[#1e2d45] rounded-full h-1.5 mb-6 overflow-hidden">
        <div className="h-1.5 rounded-full transition-all duration-1000"
          style={{ width: `${progress}%`, background: "linear-gradient(90deg, #00d4aa 0%, #3b82f6 100%)" }} />
      </div>

      {/* Steps */}
      <div className="card space-y-3">
        {STEPS.map((s, i) => {
          const done = progress >= s.progress;
          const active = progress >= (STEPS[i-1]?.progress || 0) && progress < s.progress;
          return (
            <div key={s.label} className={`flex items-center gap-3 text-sm transition-all ${done ? "text-[#00d4aa]" : active ? "text-slate-200" : "text-slate-600"}`}>
              {done
                ? <CheckCircle className="w-4 h-4 flex-shrink-0 text-[#00d4aa]" />
                : active
                  ? <div className="w-4 h-4 rounded-full border-2 border-[#00d4aa] border-t-transparent animate-spin flex-shrink-0" />
                  : <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
              }
              {s.label}
            </div>
          );
        })}
      </div>
    </div>
  );

  if (!data?.analytics) return null;
  const an = data.analytics;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="badge-teal text-xs">
              <CheckCircle className="w-3 h-3 mr-1" />Complete
            </span>
            {an.statement_quality && (
              <span className="badge-blue text-xs">Quality: {an.statement_quality.grade}</span>
            )}
          </div>
          <h1 className="text-2xl font-black text-slate-100">
            {data.account_info?.account_holder || "Financial Analysis Report"}
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {data.account_info?.bank_name} · {an.actual_period_from} → {an.actual_period_to} · {an.total_transactions} transactions
          </p>
        </div>
        <div className="flex gap-2">
          <a href={getPdfUrl(id)} target="_blank" rel="noopener" className="btn-ghost flex items-center gap-1.5 text-sm">
            <FileText className="w-4 h-4" /> PDF
          </a>
          <a href={getExcelUrl(id)} target="_blank" rel="noopener" className="btn-ghost flex items-center gap-1.5 text-sm">
            <FileSpreadsheet className="w-4 h-4" /> Excel
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 flex-wrap bg-[#0d1424] p-1.5 rounded-2xl border border-[#1e2d45] w-fit">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={activeTab === tab.id ? "tab-btn-active" : "tab-btn-inactive"}>
            <span className="mr-1.5">{tab.icon}</span>{tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="animate-slide-up">
        {activeTab === "overview" && <OverviewCards analytics={an} accountInfo={data.account_info} />}

        {activeTab === "transactions" && data.transactions && (
          <div className="card">
            <TransactionTable transactions={data.transactions} />
          </div>
        )}

        {activeTab === "cashflow" && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="card"><h3 className="section-title">Monthly Cash Flow</h3><CashFlowChart data={an.monthly_stats} /></div>
              <div className="card"><h3 className="section-title">Spending Breakdown</h3><SpendingDonut data={an.spending_breakdown} /></div>
              <div className="card"><h3 className="section-title">Balance Trend</h3><BalanceTrendChart data={an.monthly_stats} /></div>
              <div className="card"><h3 className="section-title">Income vs Obligations</h3><IncomeExpenseChart data={an.monthly_stats} /></div>
            </div>

            {/* Merchant table */}
            {an.merchant_breakdown?.length > 0 && (
              <div className="card">
                <h3 className="section-title">Top Merchant Spend</h3>
                <table className="data-table">
                  <thead><tr><th>Merchant</th><th>Category</th><th className="text-right">Amount</th><th className="text-right">Count</th></tr></thead>
                  <tbody>
                    {an.merchant_breakdown.map((m, i) => (
                      <tr key={i}>
                        <td className="font-medium text-slate-200">{m.merchant}</td>
                        <td><span className="badge-blue text-xs">{m.category}</span></td>
                        <td className="text-right font-semibold text-slate-200">₹{m.amount.toLocaleString("en-IN")}</td>
                        <td className="text-right text-slate-500">{m.count}×</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Income sources */}
            {an.income_sources?.length > 0 && (
              <div className="card">
                <h3 className="section-title">Income Sources</h3>
                <div className="space-y-2">
                  {an.income_sources.map((src, i) => (
                    <div key={i} className={`flex items-center justify-between p-3 rounded-xl border text-sm ${src.flag ? "bg-amber-500/5 border-amber-500/20" : "bg-[#00d4aa]/5 border-[#00d4aa]/20"}`}>
                      <div>
                        <span className="font-semibold text-slate-200">{src.source}</span>
                        {src.flag && <p className="text-xs text-amber-400 mt-0.5">{src.flag}</p>}
                        {src.is_verified_salary && <p className="text-xs text-[#00d4aa] mt-0.5">✓ Verified salary</p>}
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-slate-200">₹{src.total_amount.toLocaleString("en-IN")}</div>
                        <div className="text-xs text-slate-500">{src.transaction_count} credit(s)</div>
                      </div>
                    </div>
                  ))}
                </div>
                {an.upi_transaction_percentage > 0 && (
                  <p className="text-xs text-slate-500 mt-3">📱 {an.upi_transaction_percentage}% of transactions via UPI — strong digital footprint</p>
                )}
              </div>
            )}

            {/* Recurring */}
            {an.recurring_transactions?.length > 0 && (
              <div className="card">
                <h3 className="section-title">Recurring Transactions ({an.recurring_transactions.length})</h3>
                <table className="data-table">
                  <thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th className="text-right">Amount</th></tr></thead>
                  <tbody>
                    {an.recurring_transactions.slice(0, 20).map((t, i) => (
                      <tr key={i}>
                        <td className="text-slate-500 text-xs">{t.date}</td>
                        <td className="font-medium text-slate-200">{t.narration.slice(0, 45)}</td>
                        <td><span className="badge-blue text-xs">{t.category}</span></td>
                        <td className={`text-right font-semibold ${t.credit ? "text-[#00d4aa]" : "text-red-400"}`}>
                          {t.credit ? `+₹${t.credit.toLocaleString("en-IN")}` : `-₹${t.debit?.toLocaleString("en-IN")}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "credit" && <CreditScore analytics={an} />}
        {activeTab === "risk" && <RiskPanel cw={an.creditworthiness} gamblingTxns={an.gambling_transactions} />}
        {activeTab === "simulator" && <LoanSimulator analysisId={id} analytics={an} />}

        {activeTab === "qa" && (
          data.qa_result
            ? <QAReport qa={data.qa_result} quality={an.statement_quality} />
            : <div className="card text-center py-12">
                <div className="w-12 h-12 rounded-xl bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                  <Loader2 className="w-6 h-6 text-[#00d4aa] animate-spin" />
                </div>
                <p className="font-semibold text-slate-200">QA validation running in background</p>
                <p className="text-sm text-slate-500 mt-1">Refresh in a few seconds</p>
                <button onClick={poll} className="mt-4 btn-ghost text-sm">Refresh Now</button>
              </div>
        )}

        {activeTab === "chat" && (
          <div className="max-w-2xl mx-auto"><Chatbot analysisId={id} /></div>
        )}
      </div>
    </div>
  );
}
