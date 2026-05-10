import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import type { EURResponse, KontoauszugResponse } from '../../types/api'

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
