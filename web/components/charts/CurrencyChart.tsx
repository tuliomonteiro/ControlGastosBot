"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { CurrencySummary } from "@/types/expense";

const COLORS: Record<string, string> = {
  USD: "#16a34a",
  BRL: "#2563eb",
  ARS: "#7c3aed",
  Gs: "#ea580c",
};

function formatGs(value: number) {
  return new Intl.NumberFormat("es-PY").format(Math.round(value));
}

export default function CurrencyChart({ data }: { data: CurrencySummary[] }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">
        Por moeda (acumulado, em Gs)
      </h2>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} layout="vertical" margin={{ left: 16, right: 16 }}>
          <XAxis
            type="number"
            tickFormatter={(v) => `${Math.round(v / 1_000_000)}M`}
            tick={{ fontSize: 11 }}
          />
          <YAxis type="category" dataKey="currency" tick={{ fontSize: 12 }} width={36} />
          <Tooltip formatter={(v: number) => [`Gs ${formatGs(v)}`, "Total"]} />
          <Bar dataKey="totalGs" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={COLORS[entry.currency] ?? "#94a3b8"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
