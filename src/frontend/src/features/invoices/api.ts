import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type { Invoice, InvoiceCreate, InvoiceListItem, InvoiceListResponse } from '../../types/invoice'

interface InvoiceFilters {
  status_filter?: string
  customer_id?: string
  date_from?: string
  date_to?: string
  q?: string
}

export function useInvoices(filters: InvoiceFilters = {}, page = 1, pageSize = 50) {
  return useQuery<InvoiceListResponse>({
    queryKey: ['invoices', filters, page, pageSize],
    queryFn: async () => {
      const { data } = await api.get('/invoices', {
        params: { ...filters, page, page_size: pageSize },
      })
      return data
    },
  })
}

export function useInvoice(id: string) {
  return useQuery<Invoice>({
    queryKey: ['invoices', id],
    queryFn: async () => {
      const { data } = await api.get<Invoice>(`/invoices/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InvoiceCreate) => {
      const { data } = await api.post<Invoice>('/invoices', payload)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useUpdateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<InvoiceCreate> }) => {
      const { data } = await api.put<Invoice>(`/invoices/${id}`, payload)
      return data
    },
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['invoices', id] })
    },
  })
}

export function useDeleteInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/invoices/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })
}

export function useIssueInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<Invoice>(`/invoices/${id}/issue`)
      return data
    },
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['invoices', id] })
    },
  })
}

export function useCancelInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<Invoice>(`/invoices/${id}/cancel`)
      return data
    },
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['invoices', id] })
    },
  })
}

export function useSendInvoiceEmail() {
  return useMutation({
    mutationFn: async ({ id, override_email }: { id: string; override_email?: string }) => {
      const { data } = await api.post(`/invoices/${id}/send-email`, { override_email })
      return data
    },
  })
}

// Returns all issued invoices (unpaid) — drives Offene Forderungen widget
export function useOpenReceivables(year: number) {
  const dateFrom = `${year}-01-01`
  const dateTo = `${year}-12-31`
  return useQuery<InvoiceListItem[]>({
    queryKey: ['invoices', 'open-receivables', year],
    queryFn: async () => {
      const { data } = await api.get('/invoices', {
        params: { status_filter: 'issued', date_from: dateFrom, date_to: dateTo },
      })
      // Handle either plain array or paginated { items, total } response
      const raw: unknown = data
      if (Array.isArray(raw)) return raw as InvoiceListItem[]
      if (raw !== null && typeof raw === 'object' && 'items' in raw) {
        const paginated = raw as { items?: InvoiceListItem[] }
        return paginated.items ?? []
      }
      return []
    },
  })
}

export async function downloadInvoicePdf(id: string, invoiceNumber: string): Promise<void> {
  const response = await api.get(`/invoices/${id}/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${invoiceNumber}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
