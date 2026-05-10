// Types matching src/backend/app/schemas/reports.py

export type SaldenlisteRow = {
  account_number: string;
  account_name: string;
  opening_balance_cents: number;
  period_debit_cents: number;
  period_credit_cents: number;
  closing_balance_cents: number;
};

export type SaldenlisteResponse = {
  date_from: string;
  date_to: string;
  rows: SaldenlisteRow[];
  total_debit_cents: number;
  total_credit_cents: number;
};

export type BilanzSection = {
  label: string;
  amount_cents: number;
  subsections: BilanzSection[];
};

export type BilanzResponse = {
  as_of_date: string;
  aktiva: BilanzSection[];
  passiva: BilanzSection[];
  aktiva_total_cents: number;
  passiva_total_cents: number;
  balanced: boolean;
  imbalance_cents: number;
};

export type GuvRow = {
  label: string;
  account_numbers: string[];
  amount_cents: number;
};

export type GuvResponse = {
  date_from: string;
  date_to: string;
  revenue_rows: GuvRow[];
  expense_rows: GuvRow[];
  revenue_total_cents: number;
  expense_total_cents: number;
  result_cents: number;
};

export type BWAColumn = {
  year: number;
  month: number;
  revenue_cents: number;
  material_costs_cents: number;
  personnel_costs_cents: number;
  other_costs_cents: number;
  ebit_cents: number;
};

export type BWAResponse = {
  year: number;
  columns: BWAColumn[];
  ytd_revenue_cents: number;
  ytd_ebit_cents: number;
};
