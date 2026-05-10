import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import type { AuditLogParams, AuditLogResponse } from '../../types/admin'

const AUDIT_LOG_KEY = 'audit-log'

export function useAuditLog(params: AuditLogParams) {
  const { page = 1, table, action, date_from, date_to } = params

  const searchParams = new URLSearchParams()
  searchParams.set('page', String(page))
  if (table) searchParams.set('table', table)
  if (action && action !== 'all') searchParams.set('action', action)
  if (date_from) searchParams.set('date_from', date_from)
  if (date_to) searchParams.set('date_to', date_to)

  const qs = searchParams.toString()

  return useQuery<AuditLogResponse>({
    queryKey: [AUDIT_LOG_KEY, params],
    queryFn: () =>
      api.get<AuditLogResponse>(`/admin/audit-log?${qs}`).then((r) => r.data),
  })
}
