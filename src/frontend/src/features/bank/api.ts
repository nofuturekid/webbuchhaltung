import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type {
  BankAccount,
  BankAccountCreate,
  BankAccountUpdate,
  BankTransaction,
  BankTransactionListResponse,
  ImportStatsResponse,
  MatchCandidate,
} from '../../types/bank'

const BANK_ACCOUNTS_KEY = ['bank-accounts'] as const
const BANK_TRANSACTIONS_KEY = ['bank-transactions'] as const

export function useBankAccounts() {
  return useQuery<BankAccount[]>({
    queryKey: [...BANK_ACCOUNTS_KEY],
    queryFn: () =>
      api.get<BankAccount[]>('/bank-accounts/').then((r) => r.data),
  })
}

export function useCreateBankAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: BankAccountCreate) =>
      api.post<BankAccount>('/bank-accounts/', payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BANK_ACCOUNTS_KEY }),
  })
}

export function useUpdateBankAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: BankAccountUpdate }) =>
      api.patch<BankAccount>(`/bank-accounts/${id}`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BANK_ACCOUNTS_KEY }),
  })
}

export function useDeactivateBankAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/bank-accounts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: BANK_ACCOUNTS_KEY }),
  })
}

export function useBankTransactions(accountId: string, status?: string) {
  return useQuery<BankTransactionListResponse>({
    queryKey: [...BANK_ACCOUNTS_KEY, accountId, 'transactions', status],
    queryFn: () =>
      api
        .get<BankTransactionListResponse>(`/bank-accounts/${accountId}/transactions`, {
          params: status ? { status } : {},
        })
        .then((r) => r.data),
    enabled: !!accountId,
  })
}

export function useImportMT940() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, file }: { accountId: string; file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      return api
        .post<ImportStatsResponse>(`/bank-accounts/${accountId}/import/mt940`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        .then((r) => r.data)
    },
    onSuccess: (_data, { accountId }) => {
      qc.invalidateQueries({ queryKey: [...BANK_ACCOUNTS_KEY, accountId, 'transactions'] })
    },
  })
}

export function useAutoMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (accountId: string) =>
      api
        .post<{ matched: number }>(`/bank-accounts/${accountId}/auto-match`)
        .then((r) => r.data),
    onSuccess: (_data, accountId) => {
      qc.invalidateQueries({ queryKey: [...BANK_ACCOUNTS_KEY, accountId, 'transactions'] })
    },
  })
}

export function useMatchTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, bookingId }: { id: string; bookingId: string }) =>
      api
        .post<BankTransaction>(`/bank-transactions/${id}/match`, { booking_id: bookingId })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: BANK_ACCOUNTS_KEY })
      qc.invalidateQueries({ queryKey: BANK_TRANSACTIONS_KEY })
    },
  })
}

export function useIgnoreTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<BankTransaction>(`/bank-transactions/${id}/ignore`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: BANK_ACCOUNTS_KEY })
      qc.invalidateQueries({ queryKey: BANK_TRANSACTIONS_KEY })
    },
  })
}

export function useUnmatchTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<BankTransaction>(`/bank-transactions/${id}/unmatch`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: BANK_ACCOUNTS_KEY })
      qc.invalidateQueries({ queryKey: BANK_TRANSACTIONS_KEY })
    },
  })
}

export function useMatchCandidates(transactionId: string) {
  return useQuery<MatchCandidate[]>({
    queryKey: [...BANK_TRANSACTIONS_KEY, transactionId, 'candidates'],
    queryFn: () =>
      api
        .get<MatchCandidate[]>(`/bank-transactions/${transactionId}/candidates`)
        .then((r) => r.data),
    enabled: !!transactionId,
  })
}
