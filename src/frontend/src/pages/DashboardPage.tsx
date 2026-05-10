import { Box, Typography, Grid, Paper, Divider, Select, MenuItem, FormControl, InputLabel } from '@mui/material'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useBookings } from '../features/bookings/api'
import { useEUR } from '../features/reports/api'
import { useOpenReceivables } from '../features/invoices/api'
import { useOpenPayables } from '../features/vendors/api'
import { formatEuro } from '../lib/formatters'

const CURRENT_YEAR = new Date().getFullYear()
const YEAR_OPTIONS = Array.from(
  { length: CURRENT_YEAR + 1 - 2020 + 1 },
  (_, i) => 2020 + i,
)

interface StatCardProps {
  label: string
  value: string
  color?: string
  onClick?: () => void
}

function StatCard({ label, value, color, onClick }: StatCardProps) {
  return (
    <Paper
      sx={{
        p: 2,
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { bgcolor: 'action.hover' } : {},
      }}
      onClick={onClick}
    >
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="h5" color={color}>{value}</Typography>
    </Paper>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [year, setYear] = useState(CURRENT_YEAR)

  const dateFrom = `${year}-01-01`
  const dateTo = `${year}-12-31`

  const { data: bookings } = useBookings(1, 50)
  const { data: eur } = useEUR(dateFrom, dateTo, true)
  const { data: openReceivables = [] } = useOpenReceivables(year)
  const { data: openPayables = [] } = useOpenPayables(year)

  const draftCount = bookings?.items.filter((b) => b.status === 'draft').length ?? 0
  const postedCount = bookings?.items.filter((b) => b.status === 'posted').length ?? 0

  const profit = eur ? eur.betriebseinnahmen_cents - eur.betriebsausgaben_cents : null

  const today = new Date().toISOString().split('T')[0]
  const overdueReceivables = openReceivables.filter(
    (inv) => inv.due_date !== null && inv.due_date < today,
  )

  const receivablesTotal = openReceivables.reduce(
    (sum, inv) => sum + (inv.gross_total_cents ?? 0),
    0,
  )
  const overdueTotal = overdueReceivables.reduce(
    (sum, inv) => sum + (inv.gross_total_cents ?? 0),
    0,
  )
  const payablesTotal = openPayables.reduce((sum, inv) => sum + inv.amount_cents, 0)

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <Typography variant="h4" sx={{ flexGrow: 1 }}>Dashboard</Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="year-select-label">Jahr</InputLabel>
          <Select
            labelId="year-select-label"
            value={year}
            label="Jahr"
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {YEAR_OPTIONS.map((y) => (
              <MenuItem key={y} value={y}>{y}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 1 }}>
        Jahresübersicht {year}
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
            value={profit !== null ? formatEuro(profit) : '…'}
            color={profit !== null ? (profit >= 0 ? 'success.main' : 'error.main') : undefined}
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
        Offene Posten
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <StatCard
            label="Offene Forderungen"
            value={
              openReceivables.length > 0
                ? `${openReceivables.length} · ${formatEuro(receivablesTotal)}`
                : '0'
            }
            color={openReceivables.length > 0 ? 'warning.main' : 'text.secondary'}
            onClick={() => navigate('/invoices?status=issued')}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard
            label="Überfällige Forderungen"
            value={
              overdueReceivables.length > 0
                ? `${overdueReceivables.length} · ${formatEuro(overdueTotal)}`
                : '0'
            }
            color={overdueReceivables.length > 0 ? 'error.main' : 'text.secondary'}
            onClick={() => navigate('/invoices?status=issued')}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard
            label="Offene Verbindlichkeiten"
            value={
              openPayables.length > 0
                ? `${openPayables.length} · ${formatEuro(payablesTotal)}`
                : '0'
            }
            color={openPayables.length > 0 ? 'warning.main' : 'text.secondary'}
            onClick={() => navigate('/vendor-invoices?status=posted')}
          />
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 1 }}>
        Buchungen
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={6} sm={3}>
          <StatCard
            label="Entwürfe"
            value={String(draftCount)}
            color={draftCount > 0 ? 'warning.main' : undefined}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard label="Gebucht" value={String(postedCount)} />
        </Grid>
      </Grid>
    </Box>
  )
}
