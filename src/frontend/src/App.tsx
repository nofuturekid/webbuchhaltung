import { lazy, Suspense } from 'react'
import type { ReactNode } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { CircularProgress, Box } from '@mui/material'
import LoginPage from './pages/LoginPage'
import SetupPage from './pages/SetupPage'
import Layout from './components/Layout'
import { useAuthStore } from './store/auth'

const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const BookingsPage = lazy(() => import('./pages/BookingsPage'))
const AccountsPage = lazy(() => import('./pages/AccountsPage'))
const KontoauszugPage = lazy(() => import('./pages/KontoauszugPage'))
const EURPage = lazy(() => import('./pages/EURPage'))
const DatevPage = lazy(() => import('./pages/DatevPage'))
const InvoicesPage = lazy(() => import('./pages/InvoicesPage'))
const InvoiceDetailPage = lazy(() => import('./pages/InvoiceDetailPage'))
const CustomersPage = lazy(() => import('./pages/CustomersPage'))
const MandantSettingsPage = lazy(() => import('./pages/MandantSettingsPage'))
const AssetsPage = lazy(() => import('./pages/AssetsPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const BankAccountsPage = lazy(() => import('./pages/BankAccountsPage'))
const VendorsPage = lazy(() => import('./pages/VendorsPage'))
const VendorInvoicesPage = lazy(() => import('./pages/VendorInvoicesPage'))
const SaldenllistePage = lazy(() => import('./pages/SaldenllistePage'))
const BilanzPage = lazy(() => import('./pages/BilanzPage'))
const GuvPage = lazy(() => import('./pages/GuvPage'))
const BWAPage = lazy(() => import('./pages/BWAPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { accessToken, mandantId } = useAuthStore()
  if (!accessToken) return <Navigate to="/login" replace />
  if (!mandantId) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Suspense
      fallback={
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
          <CircularProgress />
        </Box>
      }
    >
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/setup" element={<SetupPage />} />
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
                  <Route path="invoices" element={<InvoicesPage />} />
                  <Route path="invoices/:id" element={<InvoiceDetailPage />} />
                  <Route path="customers" element={<CustomersPage />} />
                  <Route path="assets" element={<AssetsPage />} />
                  <Route path="documents" element={<DocumentsPage />} />
                  <Route path="bank" element={<BankAccountsPage />} />
                  <Route path="vendors" element={<VendorsPage />} />
                  <Route path="vendor-invoices" element={<VendorInvoicesPage />} />
                  <Route path="saldenliste" element={<SaldenllistePage />} />
                  <Route path="bilanz" element={<BilanzPage />} />
                  <Route path="guv" element={<GuvPage />} />
                  <Route path="bwa" element={<BWAPage />} />
                  <Route path="settings/mandant" element={<MandantSettingsPage />} />
                  <Route path="admin" element={<AdminPage />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  )
}
