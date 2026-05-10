import { Box, Typography, Grid, Paper, Divider } from '@mui/material'
import { useBookings } from '../features/bookings/api'
import { useEUR } from '../features/reports/api'
import { formatEuro } from '../lib/formatters'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

interface StatCardProps {
  label: string
  value: string
  color?: string
}

function StatCard({ label, value, color }: StatCardProps) {
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

  const profit = eur ? eur.betriebseinnahmen_cents - eur.betriebsausgaben_cents : null

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
