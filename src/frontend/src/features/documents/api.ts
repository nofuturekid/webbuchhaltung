import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type {
  BookingSuggestion,
  ConfirmDocumentRequest,
  DocumentListResponse,
  DocumentRecord,
} from '../../types/document'

const DOCUMENTS_KEY = ['documents'] as const

export function useDocuments(page = 1, status?: string) {
  return useQuery<DocumentListResponse>({
    queryKey: [...DOCUMENTS_KEY, page, status],
    queryFn: () =>
      api
        .get<DocumentListResponse>('/documents/', { params: { page, ...(status ? { status } : {}) } })
        .then((r) => r.data),
  })
}

export function useDocument(id: string) {
  return useQuery<DocumentRecord>({
    queryKey: [...DOCUMENTS_KEY, id],
    queryFn: () => api.get<DocumentRecord>(`/documents/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useUploadDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file }: { file: File }) => {
      const formData = new FormData()
      formData.append('file', file)
      return api
        .post<DocumentRecord>('/documents/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        .then((r) => r.data)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  })
}

export function useProcessDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<DocumentRecord>(`/documents/${id}/process`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  })
}

export function useBookingSuggestion(id: string) {
  return useQuery<BookingSuggestion>({
    queryKey: [...DOCUMENTS_KEY, id, 'suggestion'],
    queryFn: () =>
      api.get<BookingSuggestion>(`/documents/${id}/suggestion`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useConfirmDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ConfirmDocumentRequest }) =>
      api.post<DocumentRecord>(`/documents/${id}/confirm`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  })
}

export function useRejectDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<DocumentRecord>(`/documents/${id}/reject`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
  })
}
