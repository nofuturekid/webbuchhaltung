import { useMutation } from '@tanstack/react-query'
import axios from 'axios'
import type { TokenResponse, AccessTokenResponse, MandantResponse } from '../../types/api'

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      const { data: tokens } = await axios.post<TokenResponse>('/api/v1/auth/login', creds)
      const { data: mandants } = await axios.get<MandantResponse[]>('/api/v1/mandants', {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      })
      if (mandants.length === 0) {
        throw new Error('Kein Mandant zugewiesen. Bitte Administrator kontaktieren.')
      }
      const { data: switched } = await axios.post<AccessTokenResponse>(
        `/api/v1/mandants/${mandants[0].id}/switch`,
        {},
        { headers: { Authorization: `Bearer ${tokens.access_token}` } }
      )
      return { accessToken: switched.access_token, refreshToken: tokens.refresh_token }
    },
  })
}
