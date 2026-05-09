# Phase 2 Full UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full React UI for WebBuchhaltung — Buchungsjournal, Kontenplan, Kontoauszug, EÜR-Bericht, and DATEV-Export — on top of the completed Phase 1 backend API.

**Architecture:** Feature-based folder structure (`src/features/<domain>/`) with a shared Axios instance (`src/lib/api.ts`) handling auth headers and token refresh. All server state via TanStack Query hooks defined in `src/features/<domain>/api.ts`. All forms via React Hook Form + Zod. German locale formatting in `src/lib/formatters.ts`.

**Tech Stack:** React 18, TypeScript 5 (strict), MUI v6, TanStack Query v5, React Hook Form + Zod, Zustand, Axios, Vite, Vitest

**Branch:** `feature/frontend-phase2` (branch off `main`)

---

## File Map

**New files:**
- `frontend/vitest.config.ts` — Vitest configuration
- `frontend/src/lib/api.ts` — Axios instance with auth interceptors + token refresh
- `frontend/src/lib/formatters.ts` — German locale formatters (Euro, date, account number)
- `frontend/src/lib/__tests__/formatters.test.ts` — formatter unit tests
- `frontend/src/types/api.ts` — TypeScript types matching OpenAPI schema
- `frontend/src/store/auth.ts` — Zustand store for tokens + mandant
- `frontend/src/features/auth/api.ts` — login/refresh mutation hooks
- `frontend/src/features/bookings/api.ts` — booking query/mutation hooks
- `frontend/src/features/bookings/BookingList.tsx` — paginated booking table
- `frontend/src/features/bookings/BookingForm.tsx` — create booking (RHF+Zod)
- `frontend/src/features/accounts/api.ts` — account query/mutation hooks
- `frontend/src/features/accounts/AccountList.tsx` — account table with edit
- `frontend/src/features/reports/api.ts` — EÜR + Kontoauszug hooks
- `frontend/src/features/reports/EURReport.tsx` — EÜR report component
- `frontend/src/features/reports/Kontoauszug.tsx` — account statement component
- `frontend/src/features/datev/api.ts` — DATEV export hook
- `frontend/src/features/datev/DatevExport.tsx` — export form + download
- `frontend/src/pages/BookingsPage.tsx` — journal page
- `frontend/src/pages/AccountsPage.tsx` — chart of accounts page
- `frontend/src/pages/KontoauszugPage.tsx` — account statement page
- `frontend/src/pages/EURPage.tsx` — EÜR report page
- `frontend/src/pages/DatevPage.tsx` — DATEV export page

**Modified files:**
- `frontend/package.json` — add vitest, @testing-library/react, @vitest/coverage-v8
- `frontend/vite.config.ts` — add test configuration
- `frontend/src/App.tsx` — add all routes, integrate auth store
- `frontend/src/components/Layout.tsx` — sidebar navigation
- `frontend/src/pages/LoginPage.tsx` — replace useState with RHF+Zod, mandant auto-switch
- `frontend/src/pages/DashboardPage.tsx` — real-data summary widgets

---

## Task 1: Vitest Setup + German Formatters

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/lib/formatters.ts`
- Create: `frontend/src/lib/__tests__/formatters.test.ts`

- [ ] **Step 1: Add vitest to package.json**

Replace the `devDependencies` block and add a `test` script. Full updated `frontend/package.json`:

```json
{
  "name": "webbuchhaltung-frontend",
  "private": true,
  "version": "0.2.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "generate-api": "openapi-typescript http://localhost:8000/openapi.json -o src/types/schema.d.ts"
  },
  "dependencies": {
    "@mui/material": "^6.0.0",
    "@mui/icons-material": "^6.0.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "@tanstack/react-query": "^5.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "zustand": "^4.5.0",
    "react-hook-form": "^7.51.0",
    "zod": "^3.23.0",
    "@hookform/resolvers": "^3.3.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "openapi-typescript": "^6.7.0",
    "vitest": "^1.6.0",
    "@vitest/coverage-v8": "^1.6.0",
    "@testing-library/react": "^15.0.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^24.0.0"
  }
}
```

- [ ] **Step 2: Create `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
```

- [ ] **Step 3: Write failing formatter tests**

Create `frontend/src/lib/__tests__/formatters.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { formatEuro, formatDate, formatAccountNumber, euroToCents, centsToEuro } from '../formatters'

describe('formatEuro', () => {
  it('formats 119000 cents as 1.190,00 €', () => {
    expect(formatEuro(119000)).toBe('1.190,00 €')
  })
  it('formats 100 cents as 1,00 €', () => {
    expect(formatEuro(100)).toBe('1,00 €')
  })
  it('formats negative cents', () => {
    expect(formatEuro(-5000)).toBe('-50,00 €')
  })
})

describe('formatDate', () => {
  it('formats ISO date as DD.MM.YYYY', () => {
    expect(formatDate('2026-01-15')).toBe('15.01.2026')
  })
})

describe('formatAccountNumber', () => {
  it('pads 4-digit number unchanged', () => {
    expect(formatAccountNumber('1200')).toBe('1200')
  })
  it('pads 3-digit number with leading zero', () => {
    expect(formatAccountNumber('800')).toBe('0800')
  })
})

describe('euroToCents', () => {
  it('converts 1190.00 to 119000', () => {
    expect(euroToCents('1190.00')).toBe(119000)
  })
  it('converts comma decimal 1190,00 to 119000', () => {
    expect(euroToCents('1190,00')).toBe(119000)
  })
  it('rounds correctly', () => {
    expect(euroToCents('0.005')).toBe(1)
  })
})

describe('centsToEuro', () => {
  it('converts 119000 to "1190.00"', () => {
    expect(centsToEuro(119000)).toBe('1190.00')
  })
})
```

- [ ] **Step 4: Run — expect failures**

```bash
cd frontend && npm install && npx vitest run src/lib/__tests__/formatters.test.ts
```

Expected: `Cannot find module '../formatters'`

- [ ] **Step 5: Create `frontend/src/lib/formatters.ts`**

```typescript
const euroFormatter = new Intl.NumberFormat('de-DE', {
  style: 'currency',
  currency: 'EUR',
})

const dateFormatter = new Intl.DateTimeFormat('de-DE')

export function formatEuro(cents: number): string {
  return euroFormatter.format(cents / 100)
}

export function formatDate(dateStr: string): string {
  return dateFormatter.format(new Date(dateStr + 'T00:00:00'))
}

export function formatAccountNumber(num: string): string {
  return num.padStart(4, '0')
}

export function euroToCents(euro: string): number {
  return Math.round(parseFloat(euro.replace(',', '.')) * 100)
}

export function centsToEuro(cents: number): string {
  return (cents / 100).toFixed(2)
}
```

- [ ] **Step 6: Run — expect all pass**

```bash
npx vitest run src/lib/__tests__/formatters.test.ts
```

Expected: `5 tests passed`

- [ ] **Step 7: Commit**

```bash
cd /path/to/WebBuchhaltung
git add frontend/package.json frontend/vitest.config.ts \
        frontend/src/lib/formatters.ts frontend/src/lib/__tests__/formatters.test.ts
git commit -m "feat(frontend): Add Vitest, German formatters with tests"
```

---

## Task 2: TypeScript API Types

**Files:**
- Create: `frontend/src/types/api.ts`

- [ ] **Step 1: Create `frontend/src/types/api.ts`**

```typescript
export interface MandantResponse {
  id: string
  name: string
  steuernummer: string | null
  ust_id: string | null
  datev_beraternummer: string | null
  datev_mandantennummer: string | null
  fiscal_year_start: number
  skr_variant: string
  is_active: boolean
}

export interface AccountResponse {
  id: string
  account_number: string
  name: string
  account_class: string
  tax_type: string | null
  skr_variant: string
  is_custom: boolean
  private_share_percent: number
  is_active: boolean
}

export interface BookingResponse {
  id: string
  mandant_id: string
  booking_type: string
  status: string
  date_booking: string
  date_tax: string | null
  amount_cents: number
  currency: string
  document_number: string | null
  notes: string | null
  entry_number: number | null
  coa_id: string | null
  counter_coa_id: string | null
  tax_rate: string | null
  tax_amount_cents: number | null
  tax_key_code: number | null
  reversal_of_id: string | null
  created_by: string
}

export interface BookingListResponse {
  items: BookingResponse[]
  total: number
  page: number
  page_size: number
}

export interface EURLineItem {
  account_number: string
  account_name: string
  gross_cents: number
  tax_cents: number
  net_cents: number
  private_deduction_cents: number
  reportable_cents: number
}

export interface EURResponse {
  date_from: string
  date_to: string
  betriebseinnahmen_cents: number
  betriebsausgaben_cents: number
  ust_cents: number
  vst_19_cents: number
  vst_7_cents: number
  items: EURLineItem[]
}

export interface KontoauszugLine {
  booking_id: string
  date_booking: string
  document_number: string | null
  notes: string | null
  debit_cents: number
  credit_cents: number
  running_balance_cents: number
  entry_number: number | null
  status: string
}

export interface KontoauszugResponse {
  account_id: string
  account_number: string
  account_name: string
  date_from: string
  date_to: string
  opening_balance_cents: number
  closing_balance_cents: number
  lines: KontoauszugLine[]
}

export interface PeriodResponse {
  id: string
  mandant_id: string
  year: number
  month: number
  status: string
  locked_at: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AccessTokenResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  email: string
  is_active: boolean
}
```

- [ ] **Step 2: Verify TypeScript accepts the file**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(frontend): Add TypeScript API types from OpenAPI schema"
```

---

## Task 3: Axios API Instance + Auth Store

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/store/auth.ts`

- [ ] **Step 1: Create `frontend/src/store/auth.ts`**

```typescript
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
```

- [ ] **Step 2: Create `frontend/src/lib/api.ts`**

```typescript
import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const status = error.response?.status
    if (status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post<{ access_token: string }>(
            '/api/v1/auth/refresh',
            { refresh_token: refresh }
          )
          localStorage.setItem('access_token', data.access_token)
          error.config.headers.Authorization = `Bearer ${data.access_token}`
          return api.request(error.config)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/store/auth.ts
git commit -m "feat(frontend): Add Axios API instance with token refresh and Zustand auth store"
```

---

## Task 4: Login Page — RHF + Zod + Mandant Auto-Switch

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/features/auth/api.ts`

- [ ] **Step 1: Create `frontend/src/features/auth/api.ts`**

```typescript
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'
import api from '../../lib/api'
import type { TokenResponse, AccessTokenResponse, MandantResponse } from '../../types/api'

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      const { data: tokens } = await axios.post<TokenResponse>('/api/v1/auth/login', creds)
      // Fetch mandants using the login token (no mandant scope yet)
      const { data: mandants } = await axios.get<MandantResponse[]>('/api/v1/mandants', {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      })
      if (mandants.length === 0) {
        throw new Error('Kein Mandant zugewiesen. Bitte Administrator kontaktieren.')
      }
      // Switch to first mandant to get a mandant-scoped token
      const { data: switched } = await axios.post<AccessTokenResponse>(
        `/api/v1/mandants/${mandants[0].id}/switch`,
        {},
        { headers: { Authorization: `Bearer ${tokens.access_token}` } }
      )
      return { accessToken: switched.access_token, refreshToken: tokens.refresh_token }
    },
  })
}
```

- [ ] **Step 2: Replace `frontend/src/pages/LoginPage.tsx`**

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material'
import { useLoginMutation } from '../features/auth/api'
import { useAuthStore } from '../store/auth'

const schema = z.object({
  email: z.string().email('Ungültige E-Mail-Adresse'),
  password: z.string().min(1, 'Passwort erforderlich'),
})

type FormValues = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })
  const login = useLoginMutation()

  async function onSubmit(values: FormValues) {
    const result = await login.mutateAsync(values)
    setTokens(result.accessToken, result.refreshToken)
    navigate('/')
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Paper sx={{ p: 4, width: 360 }}>
        <Typography variant="h5" gutterBottom>WebBuchhaltung</Typography>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="E-Mail"
            type="email"
            {...register('email')}
            error={!!errors.email}
            helperText={errors.email?.message}
          />
          <TextField
            label="Passwort"
            type="password"
            {...register('password')}
            error={!!errors.password}
            helperText={errors.password?.message}
          />
          {login.isError && (
            <Alert severity="error">
              {login.error instanceof Error ? login.error.message : 'Anmeldung fehlgeschlagen.'}
            </Alert>
          )}
          <Button type="submit" variant="contained" loading={login.isPending}>
            Anmelden
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
```

- [ ] **Step 3: Build to verify TypeScript**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx frontend/src/features/auth/api.ts
git commit -m "feat(frontend): Login with RHF+Zod, mandant auto-switch on login"
```

---

## Task 5: Layout — Sidebar Navigation

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Replace `frontend/src/components/Layout.tsx`**

```tsx
import type { ReactNode } from 'react'
import {
  Box, AppBar, Toolbar, Typography, Drawer, List,
  ListItemButton, ListItemIcon, ListItemText, Divider, IconButton,
} from '@mui/material'
import BookIcon from '@mui/icons-material/MenuBook'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import BarChartIcon from '@mui/icons-material/BarChart'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import LogoutIcon from '@mui/icons-material/Logout'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const DRAWER_WIDTH = 220

const NAV_ITEMS = [
  { label: 'Buchungsjournal', path: '/bookings', icon: <BookIcon /> },
  { label: 'Kontenplan', path: '/accounts', icon: <AccountBalanceIcon /> },
  { label: 'Kontoauszug', path: '/kontoauszug', icon: <ReceiptLongIcon /> },
  { label: 'EÜR', path: '/eur', icon: <BarChartIcon /> },
  { label: 'DATEV Export', path: '/datev', icon: <FileDownloadIcon /> },
]

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>WebBuchhaltung</Typography>
          <IconButton color="inherit" onClick={handleLogout} title="Abmelden">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <List>
          {NAV_ITEMS.map((item) => (
            <ListItemButton
              key={item.path}
              selected={location.pathname.startsWith(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
        <Divider />
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8, ml: `${DRAWER_WIDTH}px` }}>
        {children}
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat(frontend): Add sidebar navigation to Layout"
```

---

## Task 6: App Routes

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/BookingsPage.tsx` (stub)
- Create: `frontend/src/pages/AccountsPage.tsx` (stub)
- Create: `frontend/src/pages/KontoauszugPage.tsx` (stub)
- Create: `frontend/src/pages/EURPage.tsx` (stub)
- Create: `frontend/src/pages/DatevPage.tsx` (stub)

- [ ] **Step 1: Create stub pages**

`frontend/src/pages/BookingsPage.tsx`:
```tsx
import { Typography } from '@mui/material'
export default function BookingsPage() {
  return <Typography variant="h4">Buchungsjournal</Typography>
}
```

`frontend/src/pages/AccountsPage.tsx`:
```tsx
import { Typography } from '@mui/material'
export default function AccountsPage() {
  return <Typography variant="h4">Kontenplan</Typography>
}
```

`frontend/src/pages/KontoauszugPage.tsx`:
```tsx
import { Typography } from '@mui/material'
export default function KontoauszugPage() {
  return <Typography variant="h4">Kontoauszug</Typography>
}
```

`frontend/src/pages/EURPage.tsx`:
```tsx
import { Typography } from '@mui/material'
export default function EURPage() {
  return <Typography variant="h4">EÜR</Typography>
}
```

`frontend/src/pages/DatevPage.tsx`:
```tsx
import { Typography } from '@mui/material'
export default function DatevPage() {
  return <Typography variant="h4">DATEV Export</Typography>
}
```

- [ ] **Step 2: Replace `frontend/src/App.tsx`**

```tsx
import type { ReactNode } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import BookingsPage from './pages/BookingsPage'
import AccountsPage from './pages/AccountsPage'
import KontoauszugPage from './pages/KontoauszugPage'
import EURPage from './pages/EURPage'
import DatevPage from './pages/DatevPage'
import Layout from './components/Layout'
import { useAuthStore } from './store/auth'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { accessToken, mandantId } = useAuthStore()
  if (!accessToken) return <Navigate to="/login" replace />
  if (!mandantId) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route index element={<DashboardPage />} />
                <Route path="bookings/*" element={<BookingsPage />} />
                <Route path="accounts" element={<AccountsPage />} />
                <Route path="kontoauszug" element={<KontoauszugPage />} />
                <Route path="eur" element={<EURPage />} />
                <Route path="datev" element={<DatevPage />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/
git commit -m "feat(frontend): Add all page routes and stub pages"
```

---

## Task 7: Buchungsjournal — List View

**Files:**
- Create: `frontend/src/features/bookings/api.ts`
- Create: `frontend/src/features/bookings/BookingList.tsx`
- Modify: `frontend/src/pages/BookingsPage.tsx`

- [ ] **Step 1: Create `frontend/src/features/bookings/api.ts`**

```typescript
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
```

- [ ] **Step 2: Create `frontend/src/features/bookings/BookingList.tsx`**

```tsx
import {
  Table, TableHead, TableBody, TableRow, TableCell,
  Chip, IconButton, Tooltip, Box, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import UndoIcon from '@mui/icons-material/Undo'
import DeleteIcon from '@mui/icons-material/Delete'
import { formatEuro, formatDate, formatAccountNumber } from '../../lib/formatters'
import { useBookings, usePostBooking, useReverseBooking, useDeleteBooking } from './api'
import type { BookingResponse } from '../../types/api'

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  draft: 'warning',
  posted: 'success',
  reversed: 'error',
}

function StatusChip({ status }: { status: string }) {
  const labels: Record<string, string> = {
    draft: 'Entwurf',
    posted: 'Gebucht',
    reversed: 'Storniert',
  }
  return <Chip label={labels[status] ?? status} color={STATUS_COLORS[status] ?? 'default'} size="small" />
}

export default function BookingList() {
  const { data, isLoading } = useBookings()
  const post = usePostBooking()
  const reverse = useReverseBooking()
  const del = useDeleteBooking()

  if (isLoading) return <Typography>Lade…</Typography>
  if (!data?.items.length) return <Typography color="text.secondary">Keine Buchungen vorhanden.</Typography>

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Nr.</TableCell>
          <TableCell>Datum</TableCell>
          <TableCell>Beleg</TableCell>
          <TableCell>Konto</TableCell>
          <TableCell>Gegenkonto</TableCell>
          <TableCell align="right">Betrag</TableCell>
          <TableCell>Status</TableCell>
          <TableCell />
        </TableRow>
      </TableHead>
      <TableBody>
        {data.items.map((b: BookingResponse) => (
          <TableRow key={b.id} hover>
            <TableCell sx={{ fontFamily: 'monospace' }}>{b.entry_number ?? '–'}</TableCell>
            <TableCell>{formatDate(b.date_booking)}</TableCell>
            <TableCell>{b.document_number ?? '–'}</TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>
              {b.coa_id ? formatAccountNumber(b.coa_id.slice(-4)) : '–'}
            </TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>
              {b.counter_coa_id ? formatAccountNumber(b.counter_coa_id.slice(-4)) : '–'}
            </TableCell>
            <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
              {formatEuro(b.amount_cents)}
            </TableCell>
            <TableCell><StatusChip status={b.status} /></TableCell>
            <TableCell>
              <Box sx={{ display: 'flex', gap: 0 }}>
                {b.status === 'draft' && (
                  <>
                    <Tooltip title="Buchen">
                      <IconButton size="small" onClick={() => post.mutate(b.id)}>
                        <CheckCircleIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Löschen">
                      <IconButton size="small" onClick={() => del.mutate(b.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </>
                )}
                {b.status === 'posted' && (
                  <Tooltip title="Stornieren">
                    <IconButton size="small" onClick={() => reverse.mutate(b.id)}>
                      <UndoIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

**Important:** The `BookingList` shows account IDs, not account numbers. That will be fixed in Task 8 when we have the full accounts list available via context. For now `b.coa_id.slice(-4)` is a placeholder.

- [ ] **Step 3: Update `frontend/src/pages/BookingsPage.tsx`**

```tsx
import { Box, Typography, Button } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { useState } from 'react'
import BookingList from '../features/bookings/BookingList'
import BookingForm from '../features/bookings/BookingForm'

export default function BookingsPage() {
  const [showForm, setShowForm] = useState(false)

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <Typography variant="h4" sx={{ flexGrow: 1 }}>Buchungsjournal</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setShowForm(!showForm)}
        >
          Neue Buchung
        </Button>
      </Box>
      {showForm && <BookingForm onSuccess={() => setShowForm(false)} />}
      <BookingList />
    </Box>
  )
}
```

Note: `BookingForm` is created in Task 8. This will cause a TypeScript error until then. Temporarily comment out the BookingForm import and usage, then restore in Task 8:

```tsx
// import BookingForm from '../features/bookings/BookingForm'
// {showForm && <BookingForm onSuccess={() => setShowForm(false)} />}
```

- [ ] **Step 4: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds (with BookingForm import commented out)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/bookings/api.ts \
        frontend/src/features/bookings/BookingList.tsx \
        frontend/src/pages/BookingsPage.tsx
git commit -m "feat(frontend): Add Buchungsjournal list with post/reverse/delete actions"
```

---

## Task 8: Buchungsmaske — Create Form

**Files:**
- Create: `frontend/src/features/accounts/api.ts`
- Create: `frontend/src/features/bookings/BookingForm.tsx`
- Modify: `frontend/src/pages/BookingsPage.tsx` (uncomment BookingForm)

- [ ] **Step 1: Create `frontend/src/features/accounts/api.ts`**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import type { AccountResponse } from '../../types/api'

export const ACCOUNTS_KEY = ['accounts'] as const

export function useAccounts() {
  return useQuery({
    queryKey: ACCOUNTS_KEY,
    queryFn: () => api.get<AccountResponse[]>('/accounts').then((r) => r.data),
    staleTime: 5 * 60 * 1000, // accounts change rarely
  })
}

export function useUpdateAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { private_share_percent: number } }) =>
      api.patch<AccountResponse>(`/accounts/${id}`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ACCOUNTS_KEY }),
  })
}
```

- [ ] **Step 2: Create `frontend/src/features/bookings/BookingForm.tsx`**

```tsx
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Box, Paper, Typography, TextField, Button,
  Autocomplete, MenuItem, Alert, Grid,
} from '@mui/material'
import { useAccounts } from '../accounts/api'
import { useCreateBooking } from './api'
import { euroToCents } from '../../lib/formatters'
import type { AccountResponse } from '../../types/api'

const schema = z.object({
  date_booking: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Format: JJJJ-MM-TT'),
  amount: z
    .string()
    .min(1, 'Betrag erforderlich')
    .refine((v) => !isNaN(parseFloat(v.replace(',', '.'))), 'Ungültiger Betrag'),
  document_number: z.string().max(12).optional().or(z.literal('')),
  notes: z.string().max(60).optional().or(z.literal('')),
  coa_id: z.string().uuid('Konto wählen'),
  counter_coa_id: z.string().uuid('Gegenkonto wählen'),
  tax_rate: z.enum(['', '0.19', '0.07']),
})

type FormValues = z.infer<typeof schema>

interface Props {
  onSuccess: () => void
}

export default function BookingForm({ onSuccess }: Props) {
  const { data: accounts = [] } = useAccounts()
  const create = useCreateBooking()

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      date_booking: new Date().toISOString().slice(0, 10),
      amount: '',
      document_number: '',
      notes: '',
      coa_id: '',
      counter_coa_id: '',
      tax_rate: '',
    },
  })

  const amountValue = watch('amount')
  const taxRateValue = watch('tax_rate')

  function computeTaxCents(): number | undefined {
    if (!taxRateValue || taxRateValue === '') return undefined
    const gross = euroToCents(amountValue || '0')
    const rate = parseFloat(taxRateValue)
    return Math.round((gross * rate) / (1 + rate))
  }

  async function onSubmit(values: FormValues) {
    const amount_cents = euroToCents(values.amount)
    const tax_amount_cents = computeTaxCents()
    await create.mutateAsync({
      date_booking: values.date_booking,
      amount_cents,
      coa_id: values.coa_id,
      counter_coa_id: values.counter_coa_id,
      document_number: values.document_number || undefined,
      notes: values.notes || undefined,
      tax_rate: values.tax_rate || undefined,
      tax_amount_cents: tax_amount_cents ?? undefined,
    })
    onSuccess()
  }

  const accountOptions = accounts.filter((a) => a.is_active)

  function accountLabel(a: AccountResponse) {
    return `${a.account_number.padStart(4, '0')} – ${a.name}`
  }

  const taxCents = computeTaxCents()

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>Neue Buchung</Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={3}>
            <TextField
              label="Buchungsdatum"
              type="date"
              fullWidth
              {...register('date_booking')}
              error={!!errors.date_booking}
              helperText={errors.date_booking?.message}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              label="Betrag (€)"
              fullWidth
              {...register('amount')}
              error={!!errors.amount}
              helperText={errors.amount?.message}
              placeholder="0,00"
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField
              label="Steuersatz"
              select
              fullWidth
              defaultValue=""
              {...register('tax_rate')}
            >
              <MenuItem value="">Kein</MenuItem>
              <MenuItem value="0.19">19 % USt/VSt</MenuItem>
              <MenuItem value="0.07">7 % USt/VSt</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField
              label="Steuerbetrag"
              fullWidth
              value={taxCents !== undefined ? (taxCents / 100).toFixed(2) : ''}
              InputProps={{ readOnly: true }}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField
              label="Belegnummer"
              fullWidth
              {...register('document_number')}
              error={!!errors.document_number}
              helperText={errors.document_number?.message}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="coa_id"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  options={accountOptions}
                  getOptionLabel={accountLabel}
                  onChange={(_, v) => field.onChange(v?.id ?? '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Konto (Soll)"
                      error={!!errors.coa_id}
                      helperText={errors.coa_id?.message}
                    />
                  )}
                />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="counter_coa_id"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  options={accountOptions}
                  getOptionLabel={accountLabel}
                  onChange={(_, v) => field.onChange(v?.id ?? '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Gegenkonto (Haben)"
                      error={!!errors.counter_coa_id}
                      helperText={errors.counter_coa_id?.message}
                    />
                  )}
                />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Buchungstext"
              fullWidth
              {...register('notes')}
              error={!!errors.notes}
              helperText={errors.notes?.message}
            />
          </Grid>
        </Grid>
        {create.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {create.error instanceof Error ? create.error.message : 'Fehler beim Speichern.'}
          </Alert>
        )}
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          <Button type="submit" variant="contained" loading={create.isPending}>
            Speichern
          </Button>
          <Button variant="outlined" onClick={() => onSuccess()}>
            Abbrechen
          </Button>
        </Box>
      </Box>
    </Paper>
  )
}
```

- [ ] **Step 3: Restore BookingForm in BookingsPage**

Uncomment (or replace the stub) in `frontend/src/pages/BookingsPage.tsx`:

```tsx
import { Box, Typography, Button } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { useState } from 'react'
import BookingList from '../features/bookings/BookingList'
import BookingForm from '../features/bookings/BookingForm'

export default function BookingsPage() {
  const [showForm, setShowForm] = useState(false)

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <Typography variant="h4" sx={{ flexGrow: 1 }}>Buchungsjournal</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setShowForm(!showForm)}
        >
          Neue Buchung
        </Button>
      </Box>
      {showForm && <BookingForm onSuccess={() => setShowForm(false)} />}
      <BookingList />
    </Box>
  )
}
```

- [ ] **Step 4: Fix BookingList to show real account numbers**

Also update `frontend/src/features/bookings/BookingList.tsx` to accept an `accounts` prop. Replace the file with this version that resolves account IDs to numbers:

```tsx
import {
  Table, TableHead, TableBody, TableRow, TableCell,
  Chip, IconButton, Tooltip, Box, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import UndoIcon from '@mui/icons-material/Undo'
import DeleteIcon from '@mui/icons-material/Delete'
import { formatEuro, formatDate, formatAccountNumber } from '../../lib/formatters'
import { useBookings, usePostBooking, useReverseBooking, useDeleteBooking } from './api'
import { useAccounts } from '../accounts/api'
import type { BookingResponse } from '../../types/api'

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  draft: 'warning',
  posted: 'success',
  reversed: 'error',
}

function StatusChip({ status }: { status: string }) {
  const labels: Record<string, string> = {
    draft: 'Entwurf',
    posted: 'Gebucht',
    reversed: 'Storniert',
  }
  return <Chip label={labels[status] ?? status} color={STATUS_COLORS[status] ?? 'default'} size="small" />
}

export default function BookingList() {
  const { data, isLoading } = useBookings()
  const { data: accounts = [] } = useAccounts()
  const post = usePostBooking()
  const reverse = useReverseBooking()
  const del = useDeleteBooking()

  const accountMap = new Map(accounts.map((a) => [a.id, a.account_number]))

  if (isLoading) return <Typography>Lade…</Typography>
  if (!data?.items.length) return <Typography color="text.secondary">Keine Buchungen vorhanden.</Typography>

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Nr.</TableCell>
          <TableCell>Datum</TableCell>
          <TableCell>Beleg</TableCell>
          <TableCell>Konto</TableCell>
          <TableCell>Gegenkonto</TableCell>
          <TableCell align="right">Betrag</TableCell>
          <TableCell>Status</TableCell>
          <TableCell />
        </TableRow>
      </TableHead>
      <TableBody>
        {data.items.map((b: BookingResponse) => (
          <TableRow key={b.id} hover>
            <TableCell sx={{ fontFamily: 'monospace' }}>{b.entry_number ?? '–'}</TableCell>
            <TableCell>{formatDate(b.date_booking)}</TableCell>
            <TableCell>{b.document_number ?? '–'}</TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>
              {b.coa_id ? formatAccountNumber(accountMap.get(b.coa_id) ?? '???') : '–'}
            </TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>
              {b.counter_coa_id ? formatAccountNumber(accountMap.get(b.counter_coa_id) ?? '???') : '–'}
            </TableCell>
            <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
              {formatEuro(b.amount_cents)}
            </TableCell>
            <TableCell><StatusChip status={b.status} /></TableCell>
            <TableCell>
              <Box sx={{ display: 'flex', gap: 0 }}>
                {b.status === 'draft' && (
                  <>
                    <Tooltip title="Buchen">
                      <IconButton size="small" onClick={() => post.mutate(b.id)}>
                        <CheckCircleIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Löschen">
                      <IconButton size="small" onClick={() => del.mutate(b.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </>
                )}
                {b.status === 'posted' && (
                  <Tooltip title="Stornieren">
                    <IconButton size="small" onClick={() => reverse.mutate(b.id)}>
                      <UndoIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

- [ ] **Step 5: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/accounts/api.ts \
        frontend/src/features/bookings/BookingForm.tsx \
        frontend/src/features/bookings/BookingList.tsx \
        frontend/src/pages/BookingsPage.tsx
git commit -m "feat(frontend): Add Buchungsmaske with account autocomplete and tax calculation"
```

---

## Task 9: Kontenplan — Account List + Edit Private Share

**Files:**
- Create: `frontend/src/features/accounts/AccountList.tsx`
- Modify: `frontend/src/pages/AccountsPage.tsx`

- [ ] **Step 1: Create `frontend/src/features/accounts/AccountList.tsx`**

```tsx
import { useState } from 'react'
import {
  Table, TableHead, TableBody, TableRow, TableCell,
  TextField, IconButton, Tooltip, Typography, Chip,
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import { useAccounts, useUpdateAccount } from './api'
import { formatAccountNumber } from '../../lib/formatters'
import type { AccountResponse } from '../../types/api'

function EditablePrivateShare({ account }: { account: AccountResponse }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(String(account.private_share_percent))
  const update = useUpdateAccount()

  async function save() {
    const pct = parseInt(value, 10)
    if (isNaN(pct) || pct < 0 || pct > 100) return
    await update.mutateAsync({ id: account.id, body: { private_share_percent: pct } })
    setEditing(false)
  }

  if (!editing) {
    return (
      <span>
        {account.private_share_percent}%
        <Tooltip title="Bearbeiten">
          <IconButton size="small" onClick={() => setEditing(true)}>
            <EditIcon fontSize="inherit" />
          </IconButton>
        </Tooltip>
      </span>
    )
  }

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <TextField
        size="small"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        sx={{ width: 72 }}
        inputProps={{ min: 0, max: 100 }}
        type="number"
      />
      <IconButton size="small" onClick={save}><CheckIcon fontSize="inherit" /></IconButton>
      <IconButton size="small" onClick={() => setEditing(false)}><CloseIcon fontSize="inherit" /></IconButton>
    </span>
  )
}

export default function AccountList() {
  const { data: accounts = [], isLoading } = useAccounts()

  if (isLoading) return <Typography>Lade…</Typography>

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Konto</TableCell>
          <TableCell>Bezeichnung</TableCell>
          <TableCell>Klasse</TableCell>
          <TableCell>Privatanteil</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {accounts.filter((a) => a.is_active).map((a) => (
          <TableRow key={a.id} hover>
            <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
              {formatAccountNumber(a.account_number)}
            </TableCell>
            <TableCell>{a.name}</TableCell>
            <TableCell>
              <Chip label={a.account_class} size="small" variant="outlined" />
            </TableCell>
            <TableCell>
              <EditablePrivateShare account={a} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

- [ ] **Step 2: Update `frontend/src/pages/AccountsPage.tsx`**

```tsx
import { Box, Typography } from '@mui/material'
import AccountList from '../features/accounts/AccountList'

export default function AccountsPage() {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Kontenplan</Typography>
      <AccountList />
    </Box>
  )
}
```

- [ ] **Step 3: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/accounts/AccountList.tsx frontend/src/pages/AccountsPage.tsx
git commit -m "feat(frontend): Add Kontenplan with inline private share editing"
```

---

## Task 10: Kontoauszug — Account Statement

**Files:**
- Create: `frontend/src/features/reports/api.ts`
- Create: `frontend/src/features/reports/Kontoauszug.tsx`
- Modify: `frontend/src/pages/KontoauszugPage.tsx`

- [ ] **Step 1: Create `frontend/src/features/reports/api.ts`**

```typescript
import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import type { EURResponse, KontoauszugResponse } from '../../types/api'

export function useEUR(dateFrom: string, dateTo: string, enabled: boolean) {
  return useQuery({
    queryKey: ['eur', dateFrom, dateTo],
    queryFn: () =>
      api.get<EURResponse>('/reports/eur', {
        params: { date_from: dateFrom, date_to: dateTo },
      }).then((r) => r.data),
    enabled,
  })
}

export function useKontoauszug(
  accountId: string,
  dateFrom: string,
  dateTo: string,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['kontoauszug', accountId, dateFrom, dateTo],
    queryFn: () =>
      api.get<KontoauszugResponse>('/reports/account-statement', {
        params: { account_id: accountId, date_from: dateFrom, date_to: dateTo },
      }).then((r) => r.data),
    enabled,
  })
}
```

- [ ] **Step 2: Create `frontend/src/features/reports/Kontoauszug.tsx`**

```tsx
import {
  Table, TableHead, TableBody, TableRow, TableCell,
  Typography, Chip, Box,
} from '@mui/material'
import { formatEuro, formatDate } from '../../lib/formatters'
import type { KontoauszugResponse } from '../../types/api'

interface Props {
  data: KontoauszugResponse
}

export default function Kontoauszug({ data }: Props) {
  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 4, mb: 2 }}>
        <Typography variant="body2">
          <strong>Konto:</strong> {data.account_number} – {data.account_name}
        </Typography>
        <Typography variant="body2">
          <strong>Anfangssaldo:</strong> {formatEuro(data.opening_balance_cents)}
        </Typography>
        <Typography variant="body2">
          <strong>Endsaldo:</strong> {formatEuro(data.closing_balance_cents)}
        </Typography>
      </Box>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Nr.</TableCell>
            <TableCell>Datum</TableCell>
            <TableCell>Beleg</TableCell>
            <TableCell>Text</TableCell>
            <TableCell align="right">Soll</TableCell>
            <TableCell align="right">Haben</TableCell>
            <TableCell align="right">Saldo</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.lines.map((line) => (
            <TableRow key={line.booking_id} hover>
              <TableCell sx={{ fontFamily: 'monospace' }}>{line.entry_number ?? '–'}</TableCell>
              <TableCell>{formatDate(line.date_booking)}</TableCell>
              <TableCell>{line.document_number ?? '–'}</TableCell>
              <TableCell>{line.notes ?? '–'}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {line.debit_cents ? formatEuro(line.debit_cents) : ''}
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {line.credit_cents ? formatEuro(line.credit_cents) : ''}
              </TableCell>
              <TableCell
                align="right"
                sx={{
                  fontFamily: 'monospace',
                  color: line.running_balance_cents < 0 ? 'error.main' : 'inherit',
                }}
              >
                {formatEuro(line.running_balance_cents)}
              </TableCell>
              <TableCell>
                <Chip
                  label={line.status === 'posted' ? 'Gebucht' : line.status}
                  size="small"
                  color={line.status === 'posted' ? 'success' : 'default'}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  )
}
```

- [ ] **Step 3: Replace `frontend/src/pages/KontoauszugPage.tsx`**

```tsx
import { useState } from 'react'
import {
  Box, Typography, TextField, Button, Autocomplete,
} from '@mui/material'
import { useAccounts } from '../features/accounts/api'
import { useKontoauszug } from '../features/reports/api'
import KontoauszugComponent from '../features/reports/Kontoauszug'
import type { AccountResponse } from '../types/api'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

export default function KontoauszugPage() {
  const range = currentYearRange()
  const [accountId, setAccountId] = useState('')
  const [dateFrom, setDateFrom] = useState(range.from)
  const [dateTo, setDateTo] = useState(range.to)
  const [submitted, setSubmitted] = useState(false)

  const { data: accounts = [] } = useAccounts()
  const { data, isFetching } = useKontoauszug(
    accountId, dateFrom, dateTo,
    submitted && !!accountId
  )

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Kontoauszug</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Autocomplete
          options={accounts.filter((a) => a.is_active)}
          getOptionLabel={(a: AccountResponse) => `${a.account_number.padStart(4, '0')} – ${a.name}`}
          onChange={(_, v) => { setAccountId(v?.id ?? ''); setSubmitted(false) }}
          sx={{ width: 300 }}
          renderInput={(params) => <TextField {...params} label="Konto" size="small" />}
        />
        <TextField
          label="Von"
          type="date"
          size="small"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <Button
          variant="contained"
          onClick={() => setSubmitted(true)}
          disabled={!accountId}
        >
          Anzeigen
        </Button>
      </Box>
      {isFetching && <Typography>Lade…</Typography>}
      {data && !isFetching && <KontoauszugComponent data={data} />}
    </Box>
  )
}
```

- [ ] **Step 4: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/reports/api.ts \
        frontend/src/features/reports/Kontoauszug.tsx \
        frontend/src/pages/KontoauszugPage.tsx
git commit -m "feat(frontend): Add Kontoauszug with account selector and date range"
```

---

## Task 11: EÜR Bericht

**Files:**
- Create: `frontend/src/features/reports/EURReport.tsx`
- Modify: `frontend/src/pages/EURPage.tsx`

- [ ] **Step 1: Create `frontend/src/features/reports/EURReport.tsx`**

```tsx
import {
  Table, TableHead, TableBody, TableRow, TableCell,
  TableFooter, Typography, Box, Paper, Grid,
} from '@mui/material'
import { formatEuro } from '../../lib/formatters'
import type { EURResponse } from '../../types/api'

interface Props {
  data: EURResponse
}

export default function EURReport({ data }: Props) {
  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Betriebseinnahmen (netto)</Typography>
            <Typography variant="h6">{formatEuro(data.betriebseinnahmen_cents)}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Betriebsausgaben (netto)</Typography>
            <Typography variant="h6" color="error.main">{formatEuro(data.betriebsausgaben_cents)}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Gewinn</Typography>
            <Typography
              variant="h6"
              color={data.betriebseinnahmen_cents - data.betriebsausgaben_cents >= 0 ? 'success.main' : 'error.main'}
            >
              {formatEuro(data.betriebseinnahmen_cents - data.betriebsausgaben_cents)}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">USt (§ 19 EStG)</Typography>
            <Typography variant="h6">{formatEuro(data.ust_cents)}</Typography>
          </Paper>
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mb: 1 }}>Positionen</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Konto</TableCell>
            <TableCell>Bezeichnung</TableCell>
            <TableCell align="right">Brutto</TableCell>
            <TableCell align="right">Steuer</TableCell>
            <TableCell align="right">Netto</TableCell>
            <TableCell align="right">Privatanteil</TableCell>
            <TableCell align="right">Anrechenbar</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.items.map((item) => (
            <TableRow key={item.account_number} hover>
              <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                {item.account_number.padStart(4, '0')}
              </TableCell>
              <TableCell>{item.account_name}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{formatEuro(item.gross_cents)}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{formatEuro(item.tax_cents)}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{formatEuro(item.net_cents)}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {item.private_deduction_cents ? formatEuro(item.private_deduction_cents) : '–'}
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                {formatEuro(item.reportable_cents)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell colSpan={6}><strong>Gesamt anrechenbar</strong></TableCell>
            <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
              {formatEuro(data.betriebseinnahmen_cents - data.betriebsausgaben_cents)}
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    </Box>
  )
}
```

- [ ] **Step 2: Replace `frontend/src/pages/EURPage.tsx`**

```tsx
import { useState } from 'react'
import { Box, Typography, TextField, Button } from '@mui/material'
import { useEUR } from '../features/reports/api'
import EURReport from '../features/reports/EURReport'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

export default function EURPage() {
  const range = currentYearRange()
  const [dateFrom, setDateFrom] = useState(range.from)
  const [dateTo, setDateTo] = useState(range.to)
  const [submitted, setSubmitted] = useState(false)

  const { data, isFetching } = useEUR(dateFrom, dateTo, submitted)

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>EÜR — Einnahmenüberschussrechnung</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'flex-start' }}>
        <TextField
          label="Von"
          type="date"
          size="small"
          value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); setSubmitted(false) }}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); setSubmitted(false) }}
          InputLabelProps={{ shrink: true }}
        />
        <Button variant="contained" onClick={() => setSubmitted(true)}>
          Berechnen
        </Button>
      </Box>
      {isFetching && <Typography>Lade…</Typography>}
      {data && !isFetching && <EURReport data={data} />}
    </Box>
  )
}
```

- [ ] **Step 3: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/reports/EURReport.tsx frontend/src/pages/EURPage.tsx
git commit -m "feat(frontend): Add EÜR report with Betriebseinnahmen/ausgaben summary"
```

---

## Task 12: DATEV Export

**Files:**
- Create: `frontend/src/features/datev/api.ts`
- Create: `frontend/src/features/datev/DatevExport.tsx`
- Modify: `frontend/src/pages/DatevPage.tsx`

- [ ] **Step 1: Create `frontend/src/features/datev/api.ts`**

```typescript
import api from '../../lib/api'

export async function downloadDatevExport(dateFrom: string, dateTo: string): Promise<void> {
  const response = await api.post(
    '/datev/export',
    { date_from: dateFrom, date_to: dateTo },
    { responseType: 'blob' }
  )
  const url = URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `EXTF_${dateFrom}_${dateTo}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: Create `frontend/src/features/datev/DatevExport.tsx`**

```tsx
import { useState } from 'react'
import {
  Box, TextField, Button, Typography, Alert,
} from '@mui/material'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import { downloadDatevExport } from './api'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

export default function DatevExport() {
  const range = currentYearRange()
  const [dateFrom, setDateFrom] = useState(range.from)
  const [dateTo, setDateTo] = useState(range.to)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleExport() {
    setError('')
    setLoading(true)
    try {
      await downloadDatevExport(dateFrom, dateTo)
    } catch {
      setError('Export fehlgeschlagen. Bitte Zeitraum prüfen.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ maxWidth: 480 }}>
      <Typography variant="body1" sx={{ mb: 3 }}>
        Exportiert gebuchte Buchungen als DATEV EXTF v700 CSV-Datei (CP1252-kodiert).
        Diese Datei kann direkt in DATEV Unternehmen online oder DATEV Kanzlei-Rechnungswesen importiert werden.
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <TextField
          label="Von"
          type="date"
          size="small"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Button
        variant="contained"
        startIcon={<FileDownloadIcon />}
        onClick={handleExport}
        loading={loading}
      >
        DATEV CSV herunterladen
      </Button>
    </Box>
  )
}
```

- [ ] **Step 3: Replace `frontend/src/pages/DatevPage.tsx`**

```tsx
import { Box, Typography } from '@mui/material'
import DatevExport from '../features/datev/DatevExport'

export default function DatevPage() {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>DATEV Export</Typography>
      <DatevExport />
    </Box>
  )
}
```

- [ ] **Step 4: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/datev/api.ts \
        frontend/src/features/datev/DatevExport.tsx \
        frontend/src/pages/DatevPage.tsx
git commit -m "feat(frontend): Add DATEV EXTF CSV export with download"
```

---

## Task 13: Dashboard — Summary Widgets

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Replace `frontend/src/pages/DashboardPage.tsx`**

```tsx
import { Box, Typography, Grid, Paper, Divider } from '@mui/material'
import { useBookings } from '../features/bookings/api'
import { useEUR } from '../features/reports/api'
import { formatEuro } from '../lib/formatters'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="h5" color={color}>{value}</Typography>
    </Paper>
  )
}

export default function DashboardPage() {
  const range = currentYearRange()
  const { data: bookings } = useBookings(1, 50)
  const { data: eur } = useEUR(range.from, range.to, true)

  const draftCount = bookings?.items.filter((b) => b.status === 'draft').length ?? 0
  const postedCount = bookings?.items.filter((b) => b.status === 'posted').length ?? 0

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>Dashboard</Typography>

      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 1 }}>
        Jahresübersicht {new Date().getFullYear()}
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <StatCard
            label="Betriebseinnahmen (netto)"
            value={eur ? formatEuro(eur.betriebseinnahmen_cents) : '…'}
          />
        </Grid>
        <Grid item xs={12} sm={3}>
          <StatCard
            label="Betriebsausgaben (netto)"
            value={eur ? formatEuro(eur.betriebsausgaben_cents) : '…'}
            color="error.main"
          />
        </Grid>
        <Grid item xs={12} sm={3}>
          <StatCard
            label="Gewinn"
            value={eur ? formatEuro(eur.betriebseinnahmen_cents - eur.betriebsausgaben_cents) : '…'}
            color={
              eur && eur.betriebseinnahmen_cents >= eur.betriebsausgaben_cents
                ? 'success.main'
                : 'error.main'
            }
          />
        </Grid>
        <Grid item xs={12} sm={3}>
          <StatCard
            label="USt"
            value={eur ? formatEuro(eur.ust_cents) : '…'}
          />
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 1 }}>
        Buchungen
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={6} sm={3}>
          <StatCard label="Entwürfe" value={String(draftCount)} color={draftCount > 0 ? 'warning.main' : undefined} />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard label="Gebucht" value={String(postedCount)} />
        </Grid>
      </Grid>
    </Box>
  )
}
```

- [ ] **Step 2: Full build + tests**

```bash
cd frontend && npm run test && npm run build
```

Expected: all formatter tests pass, build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): Add Dashboard with live EÜR summary and booking counts"
```

---

## Task 14: Full Stack Verification

- [ ] **Step 1: Start the stack**

```bash
docker compose up --build -d
docker compose exec backend uv run alembic upgrade head
```

Seed admin user if fresh DB (see `CLAUDE.md` testing section).

- [ ] **Step 2: Manual walkthrough**

Open http://localhost:3000

1. Login with `admin@example.com` / `admin123`
2. Dashboard shows: EÜR summary loads (0 if no bookings), booking counts show 0
3. Navigate to Buchungsjournal → "Neue Buchung" → fill in date, amount, select Konto + Gegenkonto → Speichern → booking appears in list as Entwurf
4. Click ✓ (Buchen) → status changes to Gebucht, entry_number appears
5. Click ↩ (Stornieren) → reversal booking appears, original marked Storniert
6. Navigate to Kontenplan → accounts listed, click edit on private_share_percent → change, save
7. Navigate to Kontoauszug → select Konto 1200, pick date range → account statement renders with running balance
8. Navigate to EÜR → pick date range → report shows Betriebseinnahmen/ausgaben
9. Navigate to DATEV Export → pick date range → CSV downloads, opens in Excel/LibreOffice
10. Dashboard now shows correct EÜR values from booked entries

- [ ] **Step 3: Run all tests one more time**

```bash
cd backend && uv run pytest tests/ -q
cd frontend && npm run test
```

Expected: 66 backend tests pass, formatter tests pass

- [ ] **Step 4: Final commit + push + PR**

```bash
git add -A
git commit -m "feat(frontend): Phase 2 complete — full UI for Buchungsjournal, Kontenplan, Berichte, DATEV"
git push -u origin feature/frontend-phase2
gh pr create --title "feat: Phase 2 full UI" --body "$(cat <<'EOF'
## Summary
- Axios API instance with JWT auth + token auto-refresh
- Zustand auth store replacing direct localStorage access
- Login page with React Hook Form + Zod validation + mandant auto-switch
- Sidebar navigation (Layout)
- Buchungsjournal: list with post/reverse/delete, booking form with account autocomplete and tax auto-calculation
- Kontenplan: account list with inline private_share_percent editing
- Kontoauszug: account statement with date range picker and running balance
- EÜR report: Betriebseinnahmen/ausgaben/USt summary + position detail table
- DATEV export: EXTF v700 CSV download
- Dashboard: live EÜR + booking count widgets
- German formatters (Euro, date, account number) with Vitest tests

## Test Plan
- [ ] `cd backend && uv run pytest tests/ -q` — 66 tests pass
- [ ] `cd frontend && npm run test` — formatter tests pass
- [ ] `npm run build` — TypeScript compiles without errors
- [ ] Manual walkthrough: login → create booking → post → EÜR → DATEV export

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Buchungsjournal (list + create + post + reverse)
- ✅ Kontenplan (list + private share edit)
- ✅ Kontoauszug (account statement + running balance)
- ✅ EÜR Bericht (income/expense report)
- ✅ DATEV Export (CSV download)
- ✅ Axios instance with auth + token refresh
- ✅ Zustand auth store
- ✅ RHF+Zod on all forms
- ✅ German locale formatters
- ✅ Sidebar navigation

**Placeholder scan:** None found. All steps have complete code.

**Type consistency check:**
- `AccountResponse.id` used as `coa_id` value in BookingForm ✅
- `useAccounts()` returns `AccountResponse[]` used in BookingList and BookingForm ✅
- `useEUR(dateFrom, dateTo, enabled)` — signature consistent across api.ts, EURPage, DashboardPage ✅
- `useKontoauszug(accountId, dateFrom, dateTo, enabled)` — consistent ✅
- `downloadDatevExport(dateFrom, dateTo)` — consistent ✅
