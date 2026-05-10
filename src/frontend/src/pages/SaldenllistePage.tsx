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
  TableFooter,
  CircularProgress,
} from '@mui/material'
import { useSaldenliste, downloadReportCsv } from '../features/reports/api'
import { formatEuro, formatAccountNumber } from '../lib/formatters'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

export default function SaldenllistePage() {
  const range = currentYearRange()
  const [dateFrom, setDateFrom] = useState(range.from)
  const [dateTo, setDateTo] = useState(range.to)
  const [submitted, setSubmitted] = useState(false)

  const { data, isFetching } = useSaldenliste(
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
    downloadReportCsv('saldenliste', { date_from: dateFrom, date_to: dateTo })
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Saldenliste
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
              <TableCell>Konto-Nr.</TableCell>
              <TableCell>Kontoname</TableCell>
              <TableCell align="right">Eröffnungssaldo</TableCell>
              <TableCell align="right">Soll-Bewegung</TableCell>
              <TableCell align="right">Haben-Bewegung</TableCell>
              <TableCell align="right">Schlusssaldo</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.rows.map((row) => (
              <TableRow key={row.account_number}>
                <TableCell sx={{ fontFamily: 'monospace' }}>
                  {formatAccountNumber(row.account_number)}
                </TableCell>
                <TableCell>{row.account_name}</TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(row.opening_balance_cents)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(row.period_debit_cents)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(row.period_credit_cents)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(row.closing_balance_cents)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow sx={{ '& td': { fontWeight: 'bold' } }}>
              <TableCell colSpan={3}>Gesamt</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                {formatEuro(data.total_debit_cents)}
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                {formatEuro(data.total_credit_cents)}
              </TableCell>
              <TableCell />
            </TableRow>
          </TableFooter>
        </Table>
      )}
    </Box>
  )
}
