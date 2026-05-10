import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type { BookingListResponse, BookingResponse } from '../../types/api'

export const BOOKINGS_KEY = ['bookings'] as const

export function useBookings(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: [...BOOKINGS_KEY, page, pageSize],
    queryFn: () =>
      api.get<BookingListResponse>('/bookings', {
        params: { page, page_size: pageSize },
      }).then((r) => r.data),
  })
}

export function usePostBooking() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<BookingResponse>(`/bookings/${id}/post`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOOKINGS_KEY }),
  })
}

export function useReverseBooking() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<BookingResponse>(`/bookings/${id}/reverse`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOOKINGS_KEY }),
  })
}

export function useDeleteBooking() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/bookings/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOOKINGS_KEY }),
  })
}

export function useCreateBooking() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<BookingResponse>('/bookings', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOOKINGS_KEY }),
  })
}
