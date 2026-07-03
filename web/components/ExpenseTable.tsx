"use client";

import { useRouter, usePathname } from "next/navigation";
import { useState, useTransition } from "react";
import { Expense } from "@/types/expense";
import { clsx } from "clsx";

interface Props {
  expenses: Expense[];
  categories: string[];
  currencies: string[];
  banks: string[];
  filters: {
    category?: string;
    currency?: string;
    bank?: string;
    from?: string;
    to?: string;
    q?: string;
  };
}

function formatGs(value: number) {
  return new Intl.NumberFormat("es-PY").format(Math.round(value));
}

const PAGE_SIZE = 50;

export default function ExpenseTable({
  expenses,
  categories,
  currencies,
  banks,
  filters,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const [page, setPage] = useState(1);

  function applyFilter(key: string, value: string) {
    const params = new URLSearchParams({
      ...(filters.category ? { category: filters.category } : {}),
      ...(filters.currency ? { currency: filters.currency } : {}),
      ...(filters.bank ? { bank: filters.bank } : {}),
      ...(filters.from ? { from: filters.from } : {}),
      ...(filters.to ? { to: filters.to } : {}),
      ...(filters.q ? { q: filters.q } : {}),
    });
    if (value) params.set(key, value);
    else params.delete(key);
    setPage(1);
    startTransition(() => router.push(`${pathname}?${params.toString()}`));
  }

  const pageCount = Math.ceil(expenses.length / PAGE_SIZE);
  const visible = expenses.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className={clsx("space-y-4", isPending && "opacity-60 pointer-events-none")}>
      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Buscar</label>
          <input
            type="text"
            defaultValue={filters.q ?? ""}
            placeholder="Descricao ou categoria..."
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-300"
            onKeyDown={(e) => {
              if (e.key === "Enter")
                applyFilter("q", (e.target as HTMLInputElement).value);
            }}
            onBlur={(e) => applyFilter("q", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Categoria</label>
          <select
            value={filters.category ?? ""}
            onChange={(e) => applyFilter("category", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">Todas</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Moeda</label>
          <select
            value={filters.currency ?? ""}
            onChange={(e) => applyFilter("currency", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">Todas</option>
            {currencies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Banco</label>
          <select
            value={filters.bank ?? ""}
            onChange={(e) => applyFilter("bank", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <option value="">Todos</option>
            {banks.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">De</label>
          <input
            type="date"
            value={filters.from ?? ""}
            onChange={(e) => applyFilter("from", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ate</label>
          <input
            type="date"
            value={filters.to ?? ""}
            onChange={(e) => applyFilter("to", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        {Object.values(filters).some(Boolean) && (
          <button
            onClick={() => {
              setPage(1);
              startTransition(() => router.push(pathname));
            }}
            className="text-sm text-red-500 hover:text-red-700 underline mt-4"
          >
            Limpar filtros
          </button>
        )}
      </div>

      {/* Count */}
      <p className="text-sm text-gray-500">
        {expenses.length} registros encontrados
      </p>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3">Data</th>
              <th className="px-4 py-3">Descricao</th>
              <th className="px-4 py-3">Categoria</th>
              <th className="px-4 py-3 text-right">Monto</th>
              <th className="px-4 py-3">Moeda</th>
              <th className="px-4 py-3 text-right">Total (Gs)</th>
              <th className="px-4 py-3">Banco</th>
              <th className="px-4 py-3">Forma</th>
              <th className="px-4 py-3 text-center">Factura</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                  Nenhum registro encontrado
                </td>
              </tr>
            )}
            {visible.map((e, i) => (
              <tr
                key={i}
                className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
              >
                <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                  {e.date}
                </td>
                <td className="px-4 py-2.5 font-medium max-w-xs truncate">
                  {e.description}
                </td>
                <td className="px-4 py-2.5">
                  <span className="bg-blue-50 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full">
                    {e.category || "?"}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right text-gray-700">
                  {e.amount.toLocaleString("es-PY")}
                </td>
                <td className="px-4 py-2.5 text-gray-500">{e.currency}</td>
                <td className="px-4 py-2.5 text-right font-semibold">
                  {formatGs(e.amountGs)}
                </td>
                <td className="px-4 py-2.5 text-gray-500">{e.bank}</td>
                <td className="px-4 py-2.5 text-gray-500">{e.paymentMethod}</td>
                <td className="px-4 py-2.5 text-center">
                  {e.invoiced ? (
                    <span className="text-green-600 font-bold">SI</span>
                  ) : (
                    <span className="text-gray-300">NO</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex gap-2 items-center justify-center">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1 text-sm border rounded-lg disabled:opacity-40 hover:bg-gray-50"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-500">
            {page} / {pageCount}
          </span>
          <button
            disabled={page === pageCount}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 text-sm border rounded-lg disabled:opacity-40 hover:bg-gray-50"
          >
            Proximo
          </button>
        </div>
      )}
    </div>
  );
}
