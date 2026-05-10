import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type {
  Vendor,
  VendorCreate,
  VendorUpdate,
  VendorInvoice,
  VendorInvoiceCreate,
  PostInvoiceRequest,
  SepaExportRequest,
} from '../../types/vendor'

const VENDORS_KEY = ['vendors'] as const
const VENDOR_INVOICES_KEY = ['vendor-invoices'] as const

export function useVendors() {
  return useQuery<Vendor[]>({
    queryKey: [...VENDORS_KEY],
    queryFn: () => api.get<Vendor[]>('/vendors/').then((r) => r.data),
  })
}

export function useCreateVendor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: VendorCreate) =>
      api.post<Vendor>('/vendors/', payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDORS_KEY }),
  })
}

export function useUpdateVendor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: VendorUpdate }) =>
      api.patch<Vendor>(`/vendors/${id}`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDORS_KEY }),
  })
}

export function useDeactivateVendor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/vendors/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDORS_KEY }),
  })
}

export type VendorInvoiceFilters = {
  status?: string
  vendor_id?: string
  due_from?: string
  due_to?: string
}

export function useVendorInvoices(filters?: VendorInvoiceFilters) {
  return useQuery<VendorInvoice[]>({
    queryKey: [...VENDOR_INVOICES_KEY, filters],
    queryFn: () =>
      api
        .get<VendorInvoice[]>('/vendor-invoices/', {
          params: {
            ...(filters?.status ? { status: filters.status } : {}),
            ...(filters?.vendor_id ? { vendor_id: filters.vendor_id } : {}),
            ...(filters?.due_from ? { due_from: filters.due_from } : {}),
            ...(filters?.due_to ? { due_to: filters.due_to } : {}),
          },
        })
        .then((r) => r.data),
  })
}

export function useCreateVendorInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: VendorInvoiceCreate) =>
      api.post<VendorInvoice>('/vendor-invoices/', payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDOR_INVOICES_KEY }),
  })
}

export function usePostVendorInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PostInvoiceRequest }) =>
      api.post<VendorInvoice>(`/vendor-invoices/${id}/post`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDOR_INVOICES_KEY }),
  })
}

export function usePayVendorInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<VendorInvoice>(`/vendor-invoices/${id}/pay`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDOR_INVOICES_KEY }),
  })
}

export function useCancelVendorInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<VendorInvoice>(`/vendor-invoices/${id}/cancel`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VENDOR_INVOICES_KEY }),
  })
}

export function useSepaExport() {
  return useMutation({
    mutationFn: async (payload: SepaExportRequest): Promise<void> => {
      const response = await api.post('/vendor-invoices/sepa-export', payload, {
        responseType: 'blob',
      })
      const blob = new Blob([response.data as BlobPart], { type: 'application/xml' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `sepa-pain001-${payload.due_on_or_before}.xml`
      document.body.appendChild(anchor)
      anchor.click()
      document.body.removeChild(anchor)
      URL.revokeObjectURL(url)
    },
  })
}
