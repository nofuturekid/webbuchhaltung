import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type { Invoice, InvoiceCreate, InvoiceListItem } from '../../types/invoice'

interface InvoiceFilters {
  status_filter?: string
  customer_id?: string
  date_from?: string
  date_to?: string
}

export function useInvoices(filters: InvoiceFilters = {}) {
  return useQuery<InvoiceListItem[]>({
    queryKey: ['invoices', filters],
    queryFn: async () => {
      const { data } = await api.get('/invoices', { params: filters })
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

export async function downloadInvoicePdf(id: string, invoiceNumber: string): Promise<void> {
  const response = await api.get(`/invoices/${id}/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${invoiceNumber}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
