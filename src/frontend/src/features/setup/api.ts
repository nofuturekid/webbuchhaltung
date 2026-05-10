import { useMutation, useQuery } from '@tanstack/react-query'
import type { UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import api from '../../lib/api'
import type { SetupStatusResponse, SetupRequest, SetupResponse } from '../../types/api'

export function useSystemStatus(): UseQueryResult<SetupStatusResponse> {
  return useQuery({
    queryKey: ['setup-status'],
    queryFn: async () => {
      const { data } = await api.get<SetupStatusResponse>('/setup/status')
      return data
    },
    staleTime: 30_000,
    retry: false,
  })
}

export function useSetupMutation(): UseMutationResult<SetupResponse, Error, SetupRequest> {
  return useMutation({
    mutationFn: async (body: SetupRequest) => {
      const { data } = await api.post<SetupResponse>('/setup', body)
      return data
    },
  })
}
