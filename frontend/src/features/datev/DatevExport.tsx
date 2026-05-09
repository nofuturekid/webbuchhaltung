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
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
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
