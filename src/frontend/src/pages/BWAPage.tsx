import { useState } from 'react'
import {
  Box,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  CircularProgress,
} from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'
import { useBwa } from '../features/reports/api'
import { formatEuro } from '../lib/formatters'

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
  'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez',
]

function buildYearOptions(): number[] {
  const current = new Date().getFullYear()
  const years: number[] = []
  for (let y = 2020; y <= current + 1; y++) {
    years.push(y)
  }
  return years
}

export default function BWAPage() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [submitted, setSubmitted] = useState(false)

  const { data, isFetching } = useBwa({ year }, submitted)

  function handleYearChange(e: SelectChangeEvent<number>) {
    setYear(e.target.value as number)
    setSubmitted(false)
  }

  function handleSubmit() {
    setSubmitted(true)
  }

  // Build a lookup from month -> column for convenient rendering
  const colByMonth = new Map(
    (data?.columns ?? []).map((col) => [col.month, col])
  )

  function getRevenue(month: number): number {
    return colByMonth.get(month)?.revenue_cents ?? 0
  }

  function getEbit(month: number): number {
    return colByMonth.get(month)?.ebit_cents ?? 0
  }

  function getExpenses(month: number): number {
    const col = colByMonth.get(month)
    if (!col) return 0
    return col.material_costs_cents + col.personnel_costs_cents + col.other_costs_cents
  }

  const ytdRevenue = data?.ytd_revenue_cents ?? 0
  const ytdEbit = data?.ytd_ebit_cents ?? 0
  const ytdExpenses = ytdRevenue - ytdEbit

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>
        BWA — Betriebswirtschaftliche Auswertung
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'flex-start' }}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="bwa-year-label">Jahr</InputLabel>
          <Select<number>
            labelId="bwa-year-label"
            label="Jahr"
            value={year}
            onChange={handleYearChange}
          >
            {buildYearOptions().map((y) => (
              <MenuItem key={y} value={y}>
                {y}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="contained" onClick={handleSubmit}>
          Abrufen
        </Button>
      </Box>

      {isFetching && <CircularProgress />}

      {data && !isFetching && (
        <Box sx={{ overflowX: 'auto' }}>
          <Table size="small" sx={{ minWidth: 900 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', minWidth: 140 }}>Position</TableCell>
                {MONTH_NAMES.map((name) => (
                  <TableCell key={name} align="right" sx={{ fontFamily: 'monospace', minWidth: 90 }}>
                    {name}
                  </TableCell>
                ))}
                <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold', minWidth: 100 }}>
                  Gesamt
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {/* Revenue row */}
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Erlöse</TableCell>
                {MONTH_NAMES.map((_, idx) => (
                  <TableCell key={idx} align="right" sx={{ fontFamily: 'monospace' }}>
                    {formatEuro(getRevenue(idx + 1))}
                  </TableCell>
                ))}
                <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                  {formatEuro(ytdRevenue)}
                </TableCell>
              </TableRow>

              {/* Expenses row */}
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Aufwendungen</TableCell>
                {MONTH_NAMES.map((_, idx) => (
                  <TableCell key={idx} align="right" sx={{ fontFamily: 'monospace' }}>
                    {formatEuro(getExpenses(idx + 1))}
                  </TableCell>
                ))}
                <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                  {formatEuro(ytdExpenses)}
                </TableCell>
              </TableRow>

              {/* EBIT row */}
              <TableRow sx={{ bgcolor: 'grey.100' }}>
                <TableCell sx={{ fontWeight: 'bold' }}>Ergebnis (EBIT)</TableCell>
                {MONTH_NAMES.map((_, idx) => (
                  <TableCell key={idx} align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {formatEuro(getEbit(idx + 1))}
                  </TableCell>
                ))}
                <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                  {formatEuro(ytdEbit)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Box>
      )}
    </Box>
  )
}
