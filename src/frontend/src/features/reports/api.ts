import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import type { EURResponse, KontoauszugResponse } from '../../types/api'
import type {
  SaldenlisteResponse,
  BilanzResponse,
  GuvResponse,
  BWAResponse,
} from '../../types/reports'

export function useEUR(dateFrom: string, dateTo: string, enabled: boolean) {
  return useQuery({
    queryKey: ['eur', dateFrom, dateTo],
    queryFn: () =>
      api.get<EURResponse>('/reports/eur', {
        params: { date_from: dateFrom, date_to: dateTo },
      }).then((r) => r.data),
    enabled,
  })
}

export function useKontoauszug(
  accountId: string,
  dateFrom: string,
  dateTo: string,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['kontoauszug', accountId, dateFrom, dateTo],
    queryFn: () =>
      api.get<KontoauszugResponse>('/reports/account-statement', {
        params: { account_id: accountId, date_from: dateFrom, date_to: dateTo },
      }).then((r) => r.data),
    enabled,
  })
}

export function useSaldenliste(
  params: { date_from: string; date_to: string },
  enabled: boolean
) {
  return useQuery({
    queryKey: ['saldenliste', params.date_from, params.date_to],
    queryFn: () =>
      api.get<SaldenlisteResponse>('/reports/saldenliste', { params }).then((r) => r.data),
    enabled,
  })
}

export function useBilanz(params: { as_of_date: string }, enabled: boolean) {
  return useQuery({
    queryKey: ['bilanz', params.as_of_date],
    queryFn: () =>
      api.get<BilanzResponse>('/reports/bilanz', { params }).then((r) => r.data),
    enabled,
  })
}

export function useGuv(
  params: { date_from: string; date_to: string },
  enabled: boolean
) {
  return useQuery({
    queryKey: ['guv', params.date_from, params.date_to],
    queryFn: () =>
      api.get<GuvResponse>('/reports/guv', { params }).then((r) => r.data),
    enabled,
  })
}

export function useBwa(params: { year: number }, enabled: boolean) {
  return useQuery({
    queryKey: ['bwa', params.year],
    queryFn: () =>
      api.get<BWAResponse>('/reports/bwa', { params }).then((r) => r.data),
    enabled,
  })
}

/**
 * Triggers a CSV download from the given report endpoint.
 * Appends format=csv and any additional params to the query string.
 */
export function downloadReportCsv(
  endpoint: string,
  params: Record<string, string>
): void {
  const qs = new URLSearchParams({ format: 'csv', ...params }).toString()
  const token = localStorage.getItem('access_token') ?? ''
  // Use a hidden anchor with a fetch-based blob download to include auth header
  void fetch(`/api/v1/reports/${endpoint}?${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => res.blob())
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${endpoint}.csv`
      document.body.appendChild(anchor)
      anchor.click()
      document.body.removeChild(anchor)
      URL.revokeObjectURL(url)
    })
}
