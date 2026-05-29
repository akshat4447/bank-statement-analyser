"use client";
import { useState, useMemo } from "react";
import { Transaction, TransactionCategory } from "@/lib/types";
import { Search, ChevronUp, ChevronDown } from "lucide-react";

const CATEGORY_COLORS: Record<string, string> = {
  "Salary": "bg-green-100 text-green-700",
  "EMI/Loan Repayment": "bg-red-100 text-red-700",
  "Rent": "bg-purple-100 text-purple-700",
  "Utilities": "bg-blue-100 text-blue-700",
  "Food & Grocery": "bg-orange-100 text-orange-700",
  "Travel & Transport": "bg-cyan-100 text-cyan-700",
  "Entertainment": "bg-pink-100 text-pink-700",
  "Insurance": "bg-indigo-100 text-indigo-700",
  "Investments": "bg-emerald-100 text-emerald-700",
  "Medical": "bg-rose-100 text-rose-700",
  "Shopping": "bg-amber-100 text-amber-700",
  "Education": "bg-sky-100 text-sky-700",
  "Cash Withdrawal/Deposit": "bg-gray-100 text-gray-700",
  "Transfer": "bg-slate-100 text-slate-700",
  "Bounce/Return": "bg-red-200 text-red-800",
  "Other": "bg-gray-100 text-gray-500",
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
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search narration, date..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal/30"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none bg-white"
        >
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none bg-white"
        >
          {["All", "Credit", "Debit"].map((t) => <option key={t}>{t}</option>)}
        </select>
        <span className="text-sm text-gray-400 self-center ml-auto">
          {filtered.length} of {transactions.length} transactions
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-100">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-navy text-white text-xs uppercase tracking-wide">
              {["Date", "Narration", "Debit", "Credit", "Balance", "Category", "Flags"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium first:rounded-tl-xl last:rounded-tr-xl">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((t, i) => (
              <tr
                key={i}
                className={`border-b border-gray-50 hover:bg-gray-50 transition-colors
                  ${t.is_bounce ? "bg-red-50" : i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}
              >
                <td className="px-4 py-3 text-gray-500 whitespace-nowrap font-mono text-xs">{t.date}</td>
                <td className="px-4 py-3 max-w-[280px]">
                  <span className="line-clamp-2 text-navy">{t.narration}</span>
                </td>
                <td className="px-4 py-3 text-right font-medium text-red-600 whitespace-nowrap">
                  {t.debit ? `₹${t.debit.toLocaleString("en-IN")}` : "—"}
                </td>
                <td className="px-4 py-3 text-right font-medium text-green-600 whitespace-nowrap">
                  {t.credit ? `₹${t.credit.toLocaleString("en-IN")}` : "—"}
                </td>
                <td className="px-4 py-3 text-right text-gray-600 whitespace-nowrap">
                  {t.balance ? `₹${t.balance.toLocaleString("en-IN")}` : "—"}
                </td>
                <td className="px-4 py-3">
                  <span className={`badge text-xs ${CATEGORY_COLORS[t.category || "Other"] || "bg-gray-100 text-gray-600"}`}>
                    {t.category || "Other"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {t.is_salary && <span className="badge bg-green-100 text-green-700">SALARY</span>}
                    {t.is_emi && <span className="badge bg-red-100 text-red-700">EMI</span>}
                    {t.is_bounce && <span className="badge bg-red-200 text-red-800">BOUNCE</span>}
                    {t.is_suspicious && <span className="badge bg-amber-100 text-amber-700">⚠ RISK</span>}
                    {t.is_recurring && <span className="badge bg-blue-100 text-blue-700">RECURRING</span>}
                  </div>
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                  No transactions match your filters.
                </td>
              </tr>
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
