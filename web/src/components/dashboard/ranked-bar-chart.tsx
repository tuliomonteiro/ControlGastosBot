"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  LabelList,
  ResponsiveContainer,
} from "recharts";
import type { RankedSlice } from "@/lib/analytics";
import { formatGuaraniAmount } from "@/lib/format";
import styles from "./dashboard.module.css";

function compactGuaranis(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`;
  return String(Math.round(value));
}

function RankedTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: RankedSlice }[];
}) {
  if (!active || !payload?.length) return null;
  const slice = payload[0].payload;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>{slice.label}</div>
      <div className={styles.tooltipValue}>Gs. {formatGuaraniAmount(slice.total)}</div>
    </div>
  );
}

export function RankedBarChart({ data }: { data: RankedSlice[] }) {
  if (data.length === 0) {
    return <p className={styles.emptyState}>Nenhum gasto no período selecionado.</p>;
  }

  const height = Math.max(120, data.length * 40);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 48, bottom: 4, left: 8 }}
        barCategoryGap={10}
      >
        <CartesianGrid horizontal={false} stroke="var(--chart-grid)" strokeWidth={1} />
        <XAxis
          type="number"
          tick={{ fontSize: 12, fill: "var(--chart-text-secondary)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={compactGuaranis}
        />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fontSize: 13, fill: "var(--chart-text-primary)" }}
          axisLine={false}
          tickLine={false}
          width={120}
        />
        <Tooltip content={<RankedTooltip />} cursor={{ fill: "rgba(29, 34, 28, 0.04)" }} />
        <Bar dataKey="total" fill="var(--chart-series)" radius={[0, 4, 4, 0]} maxBarSize={22}>
          <LabelList
            dataKey="total"
            position="right"
            formatter={(value: number) => compactGuaranis(value)}
            style={{ fill: "var(--chart-text-primary)", fontSize: 12, fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
