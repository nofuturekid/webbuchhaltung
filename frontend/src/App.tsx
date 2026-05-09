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
