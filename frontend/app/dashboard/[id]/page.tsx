"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { AnalysisResponse, AnalysisStatus } from "@/lib/types";
import { getAnalysis, getStatus, getPdfUrl, getExcelUrl } from "@/lib/api";
import { Loader2, RefreshCw, Download, FileSpreadsheet, FileText, Bot } from "lucide-react";

import OverviewCards from "@/components/dashboard/OverviewCards";
import TransactionTable from "@/components/dashboard/TransactionTable";
import RiskPanel from "@/components/dashboard/RiskPanel";
import QAReport from "@/components/dashboard/QAReport";
import Chatbot from "@/components/dashboard/Chatbot";
import CashFlowChart from "@/components/charts/CashFlowChart";
import SpendingDonut from "@/components/charts/SpendingDonut";
import BalanceTrendChart from "@/components/charts/BalanceTrendChart";
import IncomeExpenseChart from "@/components/charts/IncomeExpenseChart";

const STATUS_LABELS: Record<AnalysisStatus, string> = {
  pending: "Queued...",
  extracting: "Extracting transactions...",
  analyzing: "Running analytics...",
  validating: "AI QA validation...",
  completed: "Complete",
  failed: "Failed",
};

const STATUS_PROGRESS: Record<AnalysisStatus, number> = {
  pending: 5,
  extracting: 30,
  analyzing: 65,
  validating: 85,
  completed: 100,
  failed: 100,
};

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "transactions", label: "Transactions" },
  { id: "analytics", label: "Analytics" },
  { id: "risk", label: "Risk" },
  { id: "qa", label: "QA Report" },
  { id: "chat", label: "AI Chat" },
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
    } catch (e) {
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

  if (error) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="text-5xl mb-4">❌</div>
        <h2 className="text-xl font-bold text-red-600 mb-2">Analysis Failed</h2>
        <p className="text-gray-500">{error}</p>
      </div>
    );
  }

  if (status !== "completed") {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <Loader2 className="w-12 h-12 text-teal animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-bold text-navy mb-2">{STATUS_LABELS[status]}</h2>
        <p className="text-gray-400 text-sm mb-6">This usually takes 20–45 seconds for a typical 3-month statement.</p>
        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
          <div
            className="h-2.5 bg-teal rounded-full transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-xs text-gray-300 mt-2">{progress}%</p>

        <div className="mt-8 text-left bg-white rounded-2xl p-5 border border-gray-100 text-sm text-gray-400">
          <p className="font-medium text-gray-500 mb-3">What's happening:</p>
          {[
            { step: "📄 Extracting text", done: progress >= 30 },
            { step: "🤖 AI transaction extraction (Claude)", done: progress >= 50 },
            { step: "🏷️ Auto-categorizing (Regex + Gemini)", done: progress >= 65 },
            { step: "📊 Computing analytics & BSA score", done: progress >= 85 },
            { step: "✅ AI QA validation", done: progress >= 100 },
          ].map((s) => (
            <div key={s.step} className={`flex items-center gap-2 py-1 ${s.done ? "text-green-600" : "text-gray-300"}`}>
              <span>{s.done ? "✓" : "○"}</span> {s.step}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data?.analytics) return null;

  const an = data.analytics;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-5">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-navy">Financial Analysis Report</h1>
          <p className="text-sm text-gray-400">
            {data.account_info?.bank_name} · {data.account_info?.account_holder} · {an.total_transactions} transactions
          </p>
        </div>
        <div className="flex gap-2">
          <a href={getPdfUrl(id)} target="_blank" rel="noopener"
            className="flex items-center gap-1.5 text-sm px-4 py-2 bg-navy text-white rounded-xl hover:bg-navy-light transition-colors">
            <FileText className="w-4 h-4" /> PDF Report
          </a>
          <a href={getExcelUrl(id)} target="_blank" rel="noopener"
            className="flex items-center gap-1.5 text-sm px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors">
            <FileSpreadsheet className="w-4 h-4" /> Excel
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 flex-wrap bg-white p-1.5 rounded-2xl border border-gray-100 w-fit shadow-sm">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={activeTab === tab.id ? "tab-btn-active" : "tab-btn-inactive"}
          >
            {tab.id === "chat" && <Bot className="w-3.5 h-3.5 inline mr-1" />}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <OverviewCards analytics={an} accountInfo={data.account_info} />
      )}

      {activeTab === "transactions" && data.transactions && (
        <div className="card">
          <TransactionTable transactions={data.transactions} />
        </div>
      )}

      {activeTab === "analytics" && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="card"><h3 className="font-semibold text-navy mb-4">Monthly Cash Flow</h3><CashFlowChart data={an.monthly_stats} /></div>
            <div className="card"><h3 className="font-semibold text-navy mb-4">Spending Breakdown</h3><SpendingDonut data={an.spending_breakdown} /></div>
            <div className="card"><h3 className="font-semibold text-navy mb-4">Balance Trend</h3><BalanceTrendChart data={an.monthly_stats} /></div>
            <div className="card"><h3 className="font-semibold text-navy mb-4">Salary vs EMI vs Net Flow</h3><IncomeExpenseChart data={an.monthly_stats} /></div>
          </div>

          {/* Merchant spend table */}
          {an.merchant_breakdown?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-navy mb-4">Top Merchant Spend</h3>
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr className="text-xs text-gray-400 border-b"><th className="text-left pb-2">Merchant</th><th className="text-left pb-2">Category</th><th className="text-right pb-2">Amount</th><th className="text-right pb-2">Txns</th></tr></thead>
                <tbody>{an.merchant_breakdown.map((m, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-2 font-medium text-navy">{m.merchant}</td>
                    <td className="py-2 text-gray-500 text-xs">{m.category}</td>
                    <td className="py-2 text-right font-semibold">₹{m.amount.toLocaleString("en-IN")}</td>
                    <td className="py-2 text-right text-gray-400">{m.count}×</td>
                  </tr>
                ))}</tbody>
              </table></div>
            </div>
          )}

          {/* Income sources */}
          {an.income_sources?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-navy mb-4">Income Sources</h3>
              <div className="space-y-2">
                {an.income_sources.map((src, i) => (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-xl border text-sm ${src.flag ? "bg-amber-50 border-amber-200" : "bg-green-50 border-green-100"}`}>
                    <div>
                      <span className="font-semibold text-navy">{src.source}</span>
                      {src.flag && <p className="text-xs text-amber-600 mt-0.5">{src.flag}</p>}
                      {src.is_verified_salary && <p className="text-xs text-green-600 mt-0.5">✓ Verified salary</p>}
                    </div>
                    <div className="text-right">
                      <div className="font-bold">₹{src.total_amount.toLocaleString("en-IN")}</div>
                      <div className="text-xs text-gray-400">{src.transaction_count} credit(s)</div>
                    </div>
                  </div>
                ))}
              </div>
              {an.upi_transaction_percentage > 0 && (
                <p className="text-xs text-gray-400 mt-3">📱 {an.upi_transaction_percentage}% of all transactions are UPI — strong digital footprint</p>
              )}
            </div>
          )}

          {/* Recurring transactions */}
          {an.recurring_transactions?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-navy mb-4">Recurring Transactions ({an.recurring_transactions.length})</h3>
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr className="text-xs text-gray-400 border-b"><th className="text-left pb-2">Date</th><th className="text-left pb-2">Merchant</th><th className="text-left pb-2">Category</th><th className="text-right pb-2">Amount</th></tr></thead>
                <tbody>{an.recurring_transactions.slice(0, 20).map((t, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-2 text-gray-500 text-xs">{t.date}</td>
                    <td className="py-2 font-medium text-navy">{t.narration.slice(0, 40)}</td>
                    <td className="py-2 text-xs text-gray-400">{t.category}</td>
                    <td className={`py-2 text-right font-semibold ${t.credit ? "text-green-600" : "text-red-500"}`}>
                      {t.credit ? `+₹${t.credit.toLocaleString("en-IN")}` : `-₹${t.debit?.toLocaleString("en-IN")}`}
                    </td>
                  </tr>
                ))}</tbody>
              </table></div>
            </div>
          )}
        </div>
      )}

      {activeTab === "risk" && (
        <RiskPanel cw={an.creditworthiness} />
      )}

      {activeTab === "qa" && (
        data.qa_result
          ? <QAReport qa={data.qa_result} />
          : <div className="card text-center py-10 text-gray-400">
              <p className="text-2xl mb-2">⏳</p>
              <p className="font-medium text-navy">QA validation is running in the background</p>
              <p className="text-sm mt-1">Refresh in a few seconds</p>
              <button onClick={poll} className="mt-4 text-sm px-4 py-2 bg-teal text-white rounded-xl hover:opacity-90 transition-opacity">Refresh Now</button>
            </div>
      )}

      {activeTab === "chat" && (
        <div className="max-w-2xl mx-auto">
          <Chatbot analysisId={id} />
        </div>
      )}
    </div>
  );
}
