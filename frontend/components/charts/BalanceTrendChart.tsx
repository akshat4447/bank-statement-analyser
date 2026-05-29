"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Area, AreaChart,
} from "recharts";
import { MonthlyStats } from "@/lib/types";
import { formatINRShort } from "@/lib/utils";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-100 shadow-lg rounded-xl px-4 py-3 text-sm">
      <p className="font-semibold text-navy mb-1">{label}</p>
      <p className="text-teal">Avg Balance: <strong>{formatINRShort(payload[0]?.value)}</strong></p>
      {payload[1] && <p className="text-gray-500">Min: {formatINRShort(payload[1]?.value)}</p>}
    </div>
  );
};

interface Props { data: MonthlyStats[] }

export default function BalanceTrendChart({ data }: Props) {
  const chartData = data.map((m) => ({
    month: m.month.slice(-7),
    avg: m.average_balance,
    min: m.min_balance,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0d7377" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#0d7377" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={formatINRShort} tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#e74c3c" strokeDasharray="4 4" strokeWidth={1} />
        <Area
          type="monotone"
          dataKey="avg"
          stroke="#0d7377"
          strokeWidth={2.5}
          fill="url(#balGrad)"
          dot={{ r: 4, fill: "#0d7377", strokeWidth: 2, stroke: "white" }}
          activeDot={{ r: 6 }}
          isAnimationActive={true}
          animationDuration={800}
          animationEasing="ease-out"
          name="Avg Balance"
        />
        <Line
          type="monotone"
          dataKey="min"
          stroke="#e74c3c"
          strokeWidth={1.5}
          strokeDasharray="5 5"
          dot={false}
          isAnimationActive={true}
          animationDuration={800}
          animationEasing="ease-out"
          name="Min Balance"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
