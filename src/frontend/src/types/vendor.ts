export type Vendor = {
  id: string
  name: string
  street: string | null
  postal_code: string | null
  city: string | null
  country: string
  vat_id: string | null
  email: string | null
  bank_iban: string | null
  bank_bic: string | null
  is_active: boolean
}

export type VendorCreate = Omit<Vendor, 'id' | 'is_active'>
export type VendorUpdate = Partial<VendorCreate>

export type VendorInvoiceStatus = 'draft' | 'posted' | 'paid' | 'cancelled'

export type VendorInvoice = {
  id: string
  vendor_id: string
  invoice_number: string
  invoice_date: string
  due_date: string | null
  amount_cents: number
  vat_amount_cents: number
  currency: string
  status: VendorInvoiceStatus
  booking_id: string | null
  document_id: string | null
  notes: string | null
}

export type VendorInvoiceCreate = {
  vendor_id: string
  invoice_number: string
  invoice_date: string
  due_date?: string | null
  amount_cents: number
  vat_amount_cents?: number
  currency?: string
  notes?: string | null
}

export type PostInvoiceRequest = {
  expense_coa_id: string
}

export type SepaExportRequest = {
  due_on_or_before: string
}
