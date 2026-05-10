export type DepreciationMethod = 'linear' | 'none'
export type AssetStatus = 'active' | 'disposed'

export interface Asset {
  id: string
  mandant_id: string
  asset_number: string
  name: string
  description: string | null
  purchase_date: string
  purchase_amount_cents: number
  useful_life_months: number
  depreciation_method: DepreciationMethod
  residual_value_cents: number
  disposal_date: string | null
  disposal_amount_cents: number | null
  coa_id: string
  depreciation_coa_id: string
  status: AssetStatus
  created_by: string
  total_depreciated_cents: number
  net_book_value_cents: number
}

export interface AssetCreate {
  name: string
  description?: string
  purchase_date: string
  purchase_amount_cents: number
  useful_life_months: number
  depreciation_method: DepreciationMethod
  residual_value_cents: number
  coa_id: string
  depreciation_coa_id: string
}

export interface AssetUpdate {
  name?: string
  description?: string
  purchase_date?: string
  purchase_amount_cents?: number
  useful_life_months?: number
  depreciation_method?: DepreciationMethod
  residual_value_cents?: number
  coa_id?: string
  depreciation_coa_id?: string
}

export interface AssetListResponse {
  items: Asset[]
  total: number
  page: number
  page_size: number
}

export interface DepreciationScheduleEntry {
  id: string
  asset_id: string
  period_year: number
  period_month: number
  amount_cents: number
  cumulative_depreciation_cents: number
  net_book_value_cents: number
  booking_id: string | null
  is_posted: boolean
}

export interface BookDepreciationRequest {
  period_year?: number
  period_month?: number
}

export interface DisposeAssetRequest {
  disposal_date: string
  disposal_amount_cents: number
}
