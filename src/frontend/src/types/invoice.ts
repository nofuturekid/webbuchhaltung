export type InvoiceStatus = 'draft' | 'issued' | 'cancelled'

export interface Customer {
  id: string
  mandant_id: string
  name: string
  street: string | null
  postal_code: string | null
  city: string | null
  country: string
  vat_id: string | null
  email: string | null
}

export interface CustomerCreate {
  name: string
  street?: string
  postal_code?: string
  city?: string
  country?: string
  vat_id?: string
  email?: string
}

export interface LineItemCreate {
  position: number
  description: string
  quantity: number
  unit?: string
  unit_price_cents: number
  vat_rate: number
}

export interface LineItem extends LineItemCreate {
  id: string
  invoice_id: string
  net_total_cents: number | null
  vat_amount_cents: number | null
}

export interface InvoiceCreate {
  customer_id: string
  issue_date?: string
  due_date?: string
  notes?: string
  line_items: LineItemCreate[]
}

export interface InvoiceListItem {
  id: string
  invoice_number: string
  status: InvoiceStatus
  customer_id: string
  issue_date: string | null
  due_date: string | null
  gross_total_cents: number | null
  currency: string
}

export interface Invoice {
  id: string
  mandant_id: string
  customer_id: string
  invoice_number: string
  status: InvoiceStatus
  issue_date: string | null
  due_date: string | null
  currency: string
  net_total_cents: number | null
  vat_total_cents: number | null
  gross_total_cents: number | null
  notes: string | null
  booking_id: string | null
  line_items: LineItem[]
}

export interface InvoiceListResponse {
  items: InvoiceListItem[]
  total: number
  page: number
  page_size: number
}

export interface InvoiceTemplate {
  id: string
  mandant_id: string
  primary_color: string
  font_family: string
  header_text: string | null
  footer_text: string | null
  payment_terms_text: string
}

export interface InvoiceSequence {
  id: string
  mandant_id: string
  prefix: string
  next_number: number
  year_reset: boolean
  last_reset_year: number | null
}
