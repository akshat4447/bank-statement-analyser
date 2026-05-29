"use client";
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { SpendingCategory } from "@/lib/types";
import { formatINRShort } from "@/lib/utils";

const COLORS = [
  "#0d7377", "#1a2e4a", "#e74c3c", "#f39c12", "#27ae60",
  "#8e44ad", "#2980b9", "#e67e22", "#16a085", "#c0392b",
  "#7f8c8d", "#d35400", "#2c3e50", "#27ae60", "#c0392b",
];

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-100 shadow-lg rounded-xl px-4 py-3 text-sm">
      <p className="font-semibold text-navy">{d.category}</p>
      <p className="text-gray-500">{formatINRShort(d.amount)} · {d.percentage.toFixed(1)}%</p>
      <p className="text-gray-400 text-xs">{d.transaction_count} transactions</p>
    </div>
  );
};

const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
  if (percent < 0.05) return null;
  const r = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + r * Math.cos(-midAngle * Math.PI / 180);
  const y = cy + r * Math.sin(-midAngle * Math.PI / 180);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight="600">
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

interface Props { data: SpendingCategory[] }

export default function SpendingDonut({ data }: Props) {
  const top = data.slice(0, 8);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={top}
          dataKey="amount"
          nameKey="category"
          cx="45%"
          cy="50%"
          outerRadius={110}
          innerRadius={55}
          paddingAngle={2}
          labelLine={false}
          label={CustomLabel}
          isAnimationActive={true}
          animationDuration={800}
        >
          {top.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          formatter={(value) => <span style={{ fontSize: 11, color: "#374151" }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
