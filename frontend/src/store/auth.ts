import { create } from 'zustand'

function parseMandantId(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return (payload.mandant_id as string) ?? null
  } catch {
    return null
  }
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  mandantId: string | null
  setTokens: (access: string, refresh: string) => void
  setAccessToken: (token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => {
  const stored = localStorage.getItem('access_token')
  return {
    accessToken: stored,
    refreshToken: localStorage.getItem('refresh_token'),
    mandantId: stored ? parseMandantId(stored) : null,
    setTokens(access, refresh) {
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)
      set({ accessToken: access, refreshToken: refresh, mandantId: parseMandantId(access) })
    },
    setAccessToken(token) {
      localStorage.setItem('access_token', token)
      set({ accessToken: token, mandantId: parseMandantId(token) })
    },
    logout() {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ accessToken: null, refreshToken: null, mandantId: null })
    },
  }
})
