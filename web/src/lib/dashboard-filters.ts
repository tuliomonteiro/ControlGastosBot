export type RangeKey = "all" | "this-month" | "last-3-months" | "this-year" | "custom";

export type ResolvedRange = {
  key: RangeKey;
  from?: string;
  to?: string;
};

export const RANGE_PRESETS: { key: RangeKey; label: string }[] = [
  { key: "all", label: "Tudo" },
  { key: "this-month", label: "Este mês" },
  { key: "last-3-months", label: "Últimos 3 meses" },
  { key: "this-year", label: "Este ano" },
  { key: "custom", label: "Personalizado" },
];

function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function resolveRange(params: {
  range?: string;
  from?: string;
  to?: string;
}): ResolvedRange {
  const key = (RANGE_PRESETS.some((preset) => preset.key === params.range)
    ? params.range
    : "all") as RangeKey;
  const now = new Date();

  switch (key) {
    case "this-month": {
      const from = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
      return { key, from: toISODate(from), to: toISODate(now) };
    }
    case "last-3-months": {
      const from = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 2, 1));
      return { key, from: toISODate(from), to: toISODate(now) };
    }
    case "this-year": {
      const from = new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
      return { key, from: toISODate(from), to: toISODate(now) };
    }
    case "custom":
      return { key, from: params.from, to: params.to };
    case "all":
    default:
      return { key: "all" };
  }
}
