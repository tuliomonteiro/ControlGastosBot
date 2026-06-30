export interface Expense {
  description: string;
  amount: number;
  currency: string;
  exchangeRate: number;
  amountGs: number;
  date: string; // ISO date string
  category: string;
  bank: string;
  paymentMethod: string;
  invoiced: boolean;
}

export interface MonthlySummary {
  month: string; // "Jan 2026"
  totalGs: number;
  count: number;
}

export interface CategorySummary {
  category: string;
  totalGs: number;
  count: number;
}

export interface CurrencySummary {
  currency: string;
  totalGs: number;
  count: number;
}

export interface DashboardStats {
  totalThisMonth: number;
  totalThisMonthCount: number;
  topCategory: string;
  topCurrency: string;
  monthly: MonthlySummary[];
  byCategory: CategorySummary[];
  byCurrency: CurrencySummary[];
}
