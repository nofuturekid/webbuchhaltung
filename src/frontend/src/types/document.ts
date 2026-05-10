export type DocumentStatus = 'uploaded' | 'processed' | 'booked' | 'rejected'

export interface ExtractionResult {
  vendor_name: string | null
  document_date: string | null
  total_amount_cents: number | null
  vat_amount_cents: number | null
  suggested_debit_account: string | null
  suggested_credit_account: string | null
  booking_text: string | null
  confidence_score: number
}

export interface DocumentRecord {
  id: string
  mandant_id: string
  filename: string
  storage_path: string
  mime_type: string
  file_size_bytes: number
  status: DocumentStatus
  extracted_json: ExtractionResult | null
  booking_id: string | null
  created_by: string
  created_at: string // ISO datetime
}

export interface BookingSuggestion {
  extraction: ExtractionResult
  debit_coa_id: string | null
  credit_coa_id: string | null
}

export interface ConfirmDocumentRequest {
  debit_coa_id: string
  credit_coa_id: string
  amount_cents: number
  booking_text: string
  booking_date: string // ISO date
  tax_key_code?: number
}

export interface DocumentListResponse {
  items: DocumentRecord[]
  total: number
  page: number
  page_size: number
}
