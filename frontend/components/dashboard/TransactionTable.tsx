"use client";
import { useState, useMemo } from "react";
import { Transaction, TransactionCategory } from "@/lib/types";
import { Search, ChevronUp, ChevronDown } from "lucide-react";

const CATEGORY_COLORS: Record<string, string> = {
  "Salary": "bg-[rgba(34,197,94,0.12)] text-green-400 border border-[rgba(34,197,94,0.2)]",
  "EMI/Loan Repayment": "bg-[rgba(239,68,68,0.1)] text-red-400 border border-[rgba(239,68,68,0.2)]",
  "Rent": "bg-[rgba(168,85,247,0.1)] text-purple-400 border border-[rgba(168,85,247,0.2)]",
  "Utilities": "bg-[rgba(59,130,246,0.1)] text-blue-400 border border-[rgba(59,130,246,0.2)]",
  "Food & Grocery": "bg-[rgba(249,115,22,0.1)] text-orange-400 border border-[rgba(249,115,22,0.2)]",
  "Travel & Transport": "bg-[rgba(6,182,212,0.1)] text-cyan-400 border border-[rgba(6,182,212,0.2)]",
  "Entertainment": "bg-[rgba(236,72,153,0.1)] text-pink-400 border border-[rgba(236,72,153,0.2)]",
  "Insurance": "bg-[rgba(99,102,241,0.1)] text-indigo-400 border border-[rgba(99,102,241,0.2)]",
  "Investments": "bg-[rgba(16,185,129,0.1)] text-emerald-400 border border-[rgba(16,185,129,0.2)]",
  "Medical": "bg-[rgba(244,63,94,0.1)] text-rose-400 border border-[rgba(244,63,94,0.2)]",
  "Shopping": "bg-[rgba(245,158,11,0.1)] text-amber-400 border border-[rgba(245,158,11,0.2)]",
  "Education": "bg-[rgba(14,165,233,0.1)] text-sky-400 border border-[rgba(14,165,233,0.2)]",
  "Cash Withdrawal/Deposit": "bg-[rgba(100,116,139,0.1)] text-slate-400 border border-[rgba(100,116,139,0.2)]",
  "Transfer": "bg-[rgba(71,85,105,0.1)] text-slate-400 border border-[rgba(71,85,105,0.2)]",
  "Bounce/Return": "bg-[rgba(239,68,68,0.15)] text-red-400 border border-red-500/30",
  "Gambling/High-Risk": "bg-[rgba(239,68,68,0.2)] text-red-400 border border-red-500/40",
  "Other": "bg-[rgba(71,85,105,0.08)] text-slate-500 border border-[rgba(71,85,105,0.15)]",
};

interface Props { transactions: Transaction[] }

export default function TransactionTable({ transactions }: Props) {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("All");
  const [typeFilter, setTypeFilter] = useState<string>("All");
  const [page, setPage] = useState(1);
  const PER_PAGE = 20;

  const categories = useMemo(() => {
    const cats = new Set(transactions.map((t) => t.category || "Other"));
    return ["All", ...Array.from(cats).sort()];
  }, [transactions]);

  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      const matchSearch = !search ||
        t.narration.toLowerCase().includes(search.toLowerCase()) ||
        t.date.includes(search);
      const matchCat = categoryFilter === "All" || t.category === categoryFilter;
      const matchType = typeFilter === "All" ||
        (typeFilter === "Credit" && t.credit) ||
        (typeFilter === "Debit" && t.debit);
      return matchSearch && matchCat && matchType;
    });
  }, [transactions, search, categoryFilter, typeFilter]);

  const pages = Math.ceil(filtered.length / PER_PAGE);
  const visible = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input type="text" placeholder="Search narration or date..." value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="input-dark pl-9" />
        </div>
        <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="input-dark w-auto">
          {categories.map((c) => <option key={c} className="bg-[#111827]">{c}</option>)}
        </select>
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="input-dark w-auto">
          {["All", "Credit", "Debit"].map((t) => <option key={t} className="bg-[#111827]">{t}</option>)}
        </select>
        <span className="text-xs text-slate-500 self-center ml-auto">
          {filtered.length} / {transactions.length} rows
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[#1e2d45]">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#111827] text-xs uppercase tracking-wide border-b border-[#1e2d45]">
              {["Date", "Narration", "Debit", "Credit", "Balance", "Category", "Flags"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-slate-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((t, i) => (
              <tr key={i} className={`border-b border-[#1e2d45] last:border-0 hover:bg-[#111827] transition-colors ${t.is_bounce ? "bg-red-500/5" : ""}`}>
                <td className="px-4 py-3 text-slate-500 whitespace-nowrap font-mono text-xs">{t.date}</td>
                <td className="px-4 py-3 max-w-[280px]">
                  <span className="line-clamp-2 text-slate-300">{t.narration}</span>
                </td>
                <td className="px-4 py-3 text-right font-semibold text-red-400 whitespace-nowrap">
                  {t.debit ? `₹${t.debit.toLocaleString("en-IN")}` : <span className="text-slate-700">—</span>}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-[#00d4aa] whitespace-nowrap">
                  {t.credit ? `₹${t.credit.toLocaleString("en-IN")}` : <span className="text-slate-700">—</span>}
                </td>
                <td className="px-4 py-3 text-right text-slate-400 whitespace-nowrap text-xs">
                  {t.balance ? `₹${t.balance.toLocaleString("en-IN")}` : "—"}
                </td>
                <td className="px-4 py-3">
                  <span className={`badge text-xs ${CATEGORY_COLORS[t.category || "Other"]}`}>{t.category || "Other"}</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {t.is_salary && <span className="badge-green text-xs">SALARY</span>}
                    {t.is_emi && <span className="badge-red text-xs">EMI</span>}
                    {t.is_bounce && <span className="badge-red text-xs">BOUNCE</span>}
                    {t.is_suspicious && <span className="badge-amber text-xs">⚠ RISK</span>}
                    {t.is_recurring && <span className="badge-blue text-xs">RECUR</span>}
                  </div>
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-600">No transactions match your filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40"
          >
            <ChevronUp className="w-4 h-4 rotate-90" />
          </button>
          <span className="text-sm text-gray-500">Page {page} of {pages}</span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="p-1.5 rounded-lg hover:bg-gray-100 disabled:opacity-40"
          >
            <ChevronDown className="w-4 h-4 rotate-90" />
          </button>
        </div>
      )}
    </div>
  );
}
