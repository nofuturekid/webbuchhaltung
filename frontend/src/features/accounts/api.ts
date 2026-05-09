import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type { AccountResponse } from '../../types/api'

export const ACCOUNTS_KEY = ['accounts'] as const

export function useAccounts() {
  return useQuery({
    queryKey: ACCOUNTS_KEY,
    queryFn: () => api.get<AccountResponse[]>('/accounts').then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

export function useUpdateAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { private_share_percent: number } }) =>
      api.patch<AccountResponse>(`/accounts/${id}`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ACCOUNTS_KEY }),
  })
}
