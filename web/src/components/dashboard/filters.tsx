"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useState, useTransition } from "react";
import { RANGE_PRESETS, type RangeKey } from "@/lib/dashboard-filters";
import styles from "./dashboard.module.css";

type Option = { id: string; name: string };

type DashboardFiltersProps = {
  categories: Option[];
  accounts: Option[];
  currentRange: RangeKey;
  currentFrom?: string;
  currentTo?: string;
  currentCategoryId?: string;
  currentAccountId?: string;
};

export function DashboardFilters({
  categories,
  accounts,
  currentRange,
  currentFrom,
  currentTo,
  currentCategoryId,
  currentAccountId,
}: DashboardFiltersProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [customFrom, setCustomFrom] = useState(currentFrom ?? "");
  const [customTo, setCustomTo] = useState(currentTo ?? "");

  function pushParams(next: Record<string, string | undefined>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    }
    startTransition(() => {
      router.push(`${pathname}?${params.toString()}`);
    });
  }

  function selectRange(key: RangeKey) {
    if (key === "custom") {
      pushParams({ range: "custom", from: customFrom || undefined, to: customTo || undefined });
      return;
    }
    pushParams({ range: key, from: undefined, to: undefined });
  }

  function applyCustomRange() {
    pushParams({ range: "custom", from: customFrom || undefined, to: customTo || undefined });
  }

  return (
    <section className={styles.filters} aria-label="Filtros" data-loading={isPending || undefined}>
      <div className={styles.filterRow}>
        <div className={styles.presetGroup} role="group" aria-label="Período">
          {RANGE_PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className={styles.presetButton}
              data-active={currentRange === preset.key || undefined}
              onClick={() => selectRange(preset.key)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className={styles.selectGroup}>
          <select
            aria-label="Categoria"
            value={currentCategoryId ?? ""}
            onChange={(event) => pushParams({ category: event.target.value || undefined })}
          >
            <option value="">Todas as categorias</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>

          <select
            aria-label="Conta"
            value={currentAccountId ?? ""}
            onChange={(event) => pushParams({ account: event.target.value || undefined })}
          >
            <option value="">Todas as contas</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {currentRange === "custom" ? (
        <div className={styles.customRange}>
          <label>
            De
            <input
              type="date"
              value={customFrom}
              onChange={(event) => setCustomFrom(event.target.value)}
            />
          </label>
          <label>
            Até
            <input
              type="date"
              value={customTo}
              onChange={(event) => setCustomTo(event.target.value)}
            />
          </label>
          <button type="button" className={styles.applyButton} onClick={applyCustomRange}>
            Aplicar
          </button>
        </div>
      ) : null}
    </section>
  );
}
