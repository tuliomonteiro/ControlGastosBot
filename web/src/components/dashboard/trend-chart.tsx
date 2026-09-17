"use client";

import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TrendPoint } from "@/lib/analytics";
import { formatGuaraniAmount } from "@/lib/format";
import styles from "./dashboard.module.css";

function compactGuaranis(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`;
  return String(Math.round(value));
}

function TrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: TrendPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>{point.label}</div>
      <div className={styles.tooltipValue}>Gs. {formatGuaraniAmount(point.total)}</div>
    </div>
  );
}

export function TrendChart({ data }: { data: TrendPoint[] }) {
  if (data.length === 0) {
    return <p className={styles.emptyState}>Nenhum gasto no período selecionado.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeWidth={1} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 12, fill: "var(--chart-text-secondary)" }}
          axisLine={{ stroke: "var(--chart-grid)" }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 12, fill: "var(--chart-text-secondary)" }}
          axisLine={false}
          tickLine={false}
          width={48}
          tickFormatter={compactGuaranis}
        />
        <Tooltip
          content={<TrendTooltip />}
          cursor={{ stroke: "var(--chart-grid)", strokeWidth: 1 }}
        />
        <Line
          type="monotone"
          dataKey="total"
          stroke="var(--chart-series)"
          strokeWidth={2}
          dot={{ r: 3, fill: "var(--chart-series)", strokeWidth: 0 }}
          activeDot={{ r: 6, fill: "var(--chart-series)", stroke: "var(--chart-surface)", strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
