"use client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import { MonthlyStats } from "@/lib/types";
import { formatINRShort } from "@/lib/utils";

interface Props { data: MonthlyStats[] }

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-100 shadow-lg rounded-xl px-4 py-3 text-sm">
      <p className="font-semibold text-navy mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.fill }} />
          <span className="text-gray-500">{p.name}:</span>
          <span className="font-medium">{formatINRShort(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

export default function CashFlowChart({ data }: Props) {
  const chartData = data.map((m) => ({
    month: m.month.slice(-7),
    "Credits": m.total_credits,
    "Debits": m.total_debits,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} barGap={4} barSize={22}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={formatINRShort} tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar
          dataKey="Credits"
          fill="#0d7377"
          radius={[4, 4, 0, 0]}
          isAnimationActive={true}
          animationDuration={800}
        />
        <Bar
          dataKey="Debits"
          fill="#e74c3c"
          radius={[4, 4, 0, 0]}
          isAnimationActive={true}
          animationDuration={800}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
