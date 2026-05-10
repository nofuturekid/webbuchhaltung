export interface MandantResponse {
  id: string
  name: string
  steuernummer: string | null
  ust_id: string | null
  datev_beraternummer: string | null
  datev_mandantennummer: string | null
  fiscal_year_start: number
  skr_variant: string
  is_active: boolean
  iban: string | null
  bic: string | null
  smtp_host: string | null
  smtp_port: number
  smtp_user: string | null
  smtp_from: string | null
  smtp_from_name: string | null
}

export interface AccountResponse {
  id: string
  account_number: string
  name: string
  account_class: string
  tax_type: string | null
  skr_variant: string
  is_custom: boolean
  private_share_percent: number
  is_active: boolean
}

export interface BookingResponse {
  id: string
  mandant_id: string
  booking_type: string
  status: string
  date_booking: string
  date_tax: string | null
  amount_cents: number
  currency: string
  document_number: string | null
  notes: string | null
  entry_number: number | null
  coa_id: string | null
  counter_coa_id: string | null
  tax_rate: string | null
  tax_amount_cents: number | null
  tax_key_code: number | null
  reversal_of_id: string | null
  created_by: string
}

export interface BookingListResponse {
  items: BookingResponse[]
  total: number
  page: number
  page_size: number
}

export interface EURLineItem {
  account_number: string
  account_name: string
  gross_cents: number
  tax_cents: number
  net_cents: number
  private_deduction_cents: number
  reportable_cents: number
}

export interface EURResponse {
  date_from: string
  date_to: string
  betriebseinnahmen_cents: number
  betriebsausgaben_cents: number
  ust_cents: number
  vst_19_cents: number
  vst_7_cents: number
  items: EURLineItem[]
}

export interface KontoauszugLine {
  booking_id: string
  date_booking: string
  document_number: string | null
  notes: string | null
  debit_cents: number
  credit_cents: number
  running_balance_cents: number
  entry_number: number | null
  status: string
}

export interface KontoauszugResponse {
  account_id: string
  account_number: string
  account_name: string
  date_from: string
  date_to: string
  opening_balance_cents: number
  closing_balance_cents: number
  lines: KontoauszugLine[]
}

export interface PeriodResponse {
  id: string
  mandant_id: string
  year: number
  month: number
  status: string
  locked_at: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AccessTokenResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  email: string
  is_active: boolean
}

export interface SetupStatusResponse {
  needs_setup: boolean
}

export interface SetupRequest {
  email: string
  password: string
  mandant_name: string
  skr_variant: 'skr03' | 'skr04' | 'skr07'
}

export interface SetupResponse {
  access_token: string
  refresh_token: string
}
