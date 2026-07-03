"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { CategorySummary } from "@/types/expense";

const COLORS = [
  "#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a",
  "#0891b2", "#ca8a04", "#dc2626", "#9333ea", "#0284c7",
];

function formatGs(value: number) {
  return new Intl.NumberFormat("es-PY").format(Math.round(value));
}

export default function CategoryChart({ data }: { data: CategorySummary[] }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">
        Por categoria (acumulado)
      </h2>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={data}
            dataKey="totalGs"
            nameKey="category"
            cx="50%"
            cy="45%"
            outerRadius={90}
            label={({ name, percent }) =>
              `${name} ${(percent * 100).toFixed(0)}%`
            }
            labelLine={false}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => [`Gs ${formatGs(v)}`, "Total"]} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
