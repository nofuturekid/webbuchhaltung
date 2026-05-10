import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type {
  Asset,
  AssetCreate,
  AssetListResponse,
  AssetUpdate,
  BookDepreciationRequest,
  DepreciationScheduleEntry,
  DisposeAssetRequest,
} from '../../types/asset'

const ASSETS_KEY = ['assets'] as const

export function useAssets(page = 1) {
  return useQuery<AssetListResponse>({
    queryKey: [...ASSETS_KEY, page],
    queryFn: () =>
      api.get<AssetListResponse>('/assets', { params: { page } }).then((r) => r.data),
  })
}

export function useAsset(id: string) {
  return useQuery<Asset>({
    queryKey: [...ASSETS_KEY, id],
    queryFn: () => api.get<Asset>(`/assets/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: AssetCreate) =>
      api.post<Asset>('/assets', payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}

export function useUpdateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AssetUpdate }) =>
      api.patch<Asset>(`/assets/${id}`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}

export function useDeleteAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/assets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}

export function useDepreciationSchedule(assetId: string) {
  return useQuery<DepreciationScheduleEntry[]>({
    queryKey: [...ASSETS_KEY, assetId, 'depreciation-schedule'],
    queryFn: () =>
      api
        .get<DepreciationScheduleEntry[]>(`/assets/${assetId}/depreciation-schedule`)
        .then((r) => r.data),
    enabled: !!assetId,
  })
}

export function useBookDepreciation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: BookDepreciationRequest }) =>
      api.post(`/assets/${id}/book-depreciation`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}

export function useDisposeAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DisposeAssetRequest }) =>
      api.post<Asset>(`/assets/${id}/dispose`, payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}
