import { useState } from 'react'
import {
  Box,
  Typography,
  TextField,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  CircularProgress,
} from '@mui/material'
import { useGuv, downloadReportCsv } from '../features/reports/api'
import { formatEuro } from '../lib/formatters'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

export default function GuvPage() {
  const range = currentYearRange()
  const [dateFrom, setDateFrom] = useState(range.from)
  const [dateTo, setDateTo] = useState(range.to)
  const [submitted, setSubmitted] = useState(false)

  const { data, isFetching } = useGuv(
    { date_from: dateFrom, date_to: dateTo },
    submitted
  )

  function handleSubmit() {
    setSubmitted(true)
  }

  function handleDateFromChange(value: string) {
    setDateFrom(value)
    setSubmitted(false)
  }

  function handleDateToChange(value: string) {
    setDateTo(value)
    setSubmitted(false)
  }

  function handleCsvExport() {
    downloadReportCsv('guv', { date_from: dateFrom, date_to: dateTo })
  }

  const isProfit = data && data.result_cents >= 0

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Gewinn- und Verlustrechnung
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <TextField
          label="Von"
          type="date"
          size="small"
          value={dateFrom}
          onChange={(e) => handleDateFromChange(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => handleDateToChange(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <Button variant="contained" onClick={handleSubmit}>
          Abrufen
        </Button>
        {data && (
          <Button variant="outlined" onClick={handleCsvExport}>
            CSV exportieren
          </Button>
        )}
      </Box>

      {isFetching && <CircularProgress />}

      {data && !isFetching && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Position</TableCell>
              <TableCell>Konten</TableCell>
              <TableCell align="right">Betrag</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Revenue section */}
            <TableRow>
              <TableCell
                colSpan={3}
                sx={{ fontWeight: 'bold', bgcolor: 'grey.100', pt: 1 }}
              >
                Erträge
              </TableCell>
            </TableRow>
            {data.revenue_rows.map((row, idx) => (
              <TableRow key={`rev-${idx}`}>
                <TableCell sx={{ pl: 3 }}>{row.label}</TableCell>
                <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                  {row.account_numbers.join(', ')}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(row.amount_cents)}
                </TableCell>
              </TableRow>
            ))}
            <TableRow sx={{ bgcolor: 'grey.50' }}>
              <TableCell colSpan={2} sx={{ fontWeight: 'bold', pl: 3 }}>
                Summe Erträge
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                {formatEuro(data.revenue_total_cents)}
              </TableCell>
            </TableRow>

            {/* Expense section */}
            <TableRow>
              <TableCell
                colSpan={3}
                sx={{ fontWeight: 'bold', bgcolor: 'grey.100', pt: 1 }}
              >
                Aufwendungen
              </TableCell>
            </TableRow>
            {data.expense_rows.map((row, idx) => (
              <TableRow key={`exp-${idx}`}>
                <TableCell sx={{ pl: 3 }}>{row.label}</TableCell>
                <TableCell sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                  {row.account_numbers.join(', ')}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(row.amount_cents)}
                </TableCell>
              </TableRow>
            ))}
            <TableRow sx={{ bgcolor: 'grey.50' }}>
              <TableCell colSpan={2} sx={{ fontWeight: 'bold', pl: 3 }}>
                Summe Aufwendungen
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                {formatEuro(data.expense_total_cents)}
              </TableCell>
            </TableRow>

            {/* Result row */}
            <TableRow
              sx={{
                bgcolor: isProfit ? 'success.light' : 'error.light',
              }}
            >
              <TableCell colSpan={2} sx={{ fontWeight: 'bold' }}>
                Ergebnis
              </TableCell>
              <TableCell
                align="right"
                sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}
              >
                {formatEuro(data.result_cents)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )}
    </Box>
  )
}
