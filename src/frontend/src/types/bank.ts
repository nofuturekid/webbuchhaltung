export interface BankAccount {
  id: string
  mandant_id: string
  name: string
  iban: string
  bic: string | null
  currency: string
  is_active: boolean
  created_at: string
}

export interface BankAccountCreate {
  name: string
  iban: string
  bic?: string
  currency?: string
}

export interface BankAccountUpdate {
  name?: string
  iban?: string
  bic?: string
  is_active?: boolean
}

export interface BankTransaction {
  id: string
  bank_account_id: string
  transaction_date: string
  value_date: string | null
  amount_cents: number
  currency: string
  purpose: string | null
  counterpart_name: string | null
  counterpart_iban: string | null
  source_format: string
  status: 'unmatched' | 'matched' | 'ignored'
  booking_id: string | null
}

export interface BankTransactionListResponse {
  items: BankTransaction[]
  total: number
  page: number
  page_size: number
}

export interface ImportStatsResponse {
  imported: number
  skipped: number
}

export interface MatchCandidate {
  booking_id: string
  booking_date: string
  amount_cents: number
  description: string | null
  entry_number: number
  score: number
}
