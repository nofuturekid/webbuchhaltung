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
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); setSubmitted(false) }}
          slotProps={{ inputLabel: { shrink: true } }}
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
