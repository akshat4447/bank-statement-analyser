"use client";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { MonthlyStats } from "@/lib/types";
import { formatINRShort } from "@/lib/utils";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-100 shadow-lg rounded-xl px-4 py-3 text-sm">
      <p className="font-semibold text-navy mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-500">{p.name}:</span>
          <span className="font-medium">{formatINRShort(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

interface Props { data: MonthlyStats[] }

export default function IncomeExpenseChart({ data }: Props) {
  const chartData = data.map((m) => ({
    month: m.month.slice(-7),
    "Salary": m.salary_credits,
    "EMI": m.emi_debits,
    "Net Flow": m.net_cash_flow,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={chartData} barGap={6} barSize={20}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={formatINRShort} tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar
          dataKey="Salary"
          fill="#22c55e"
          radius={[4, 4, 0, 0]}
          isAnimationActive={true}
          animationDuration={800}
        />
        <Bar
          dataKey="EMI"
          fill="#ef4444"
          radius={[4, 4, 0, 0]}
          isAnimationActive={true}
          animationDuration={800}
        />
        <Line
          type="monotone"
          dataKey="Net Flow"
          stroke="#3b82f6"
          strokeWidth={2.5}
          dot={{ r: 4, fill: "#1a2e4a" }}
          isAnimationActive={true}
          animationDuration={800}
          animationEasing="ease-out"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
