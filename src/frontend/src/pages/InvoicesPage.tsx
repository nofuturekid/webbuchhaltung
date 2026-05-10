import { Add as AddIcon } from '@mui/icons-material'
import SearchIcon from '@mui/icons-material/Search'
import {
  Box,
  Chip,
  Fab,
  InputAdornment,
  MenuItem,
  Pagination,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatEuro, formatDate } from '../lib/formatters'
import { useInvoices } from '../features/invoices/api'
import { InvoiceFormDialog } from '../features/invoices/InvoiceFormDialog'
import type { InvoiceStatus } from '../types/invoice'

const PAGE_SIZE = 50

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: 'Entwurf',
  issued: 'Ausgestellt',
  cancelled: 'Storniert',
}

const STATUS_COLORS: Record<InvoiceStatus, 'default' | 'primary' | 'error'> = {
  draft: 'default',
  issued: 'primary',
  cancelled: 'error',
}

export default function InvoicesPage(): JSX.Element {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [q, setQ] = useState('')

  // Debounce search input 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(searchInput)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const { data, isLoading } = useInvoices(
    {
      status_filter: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      q: q || undefined,
    },
    page,
    PAGE_SIZE,
  )

  const rows = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  function handleStatusChange(value: string): void {
    setStatusFilter(value)
    setPage(1)
  }

  function handleDateFromChange(value: string): void {
    setDateFrom(value)
    setPage(1)
  }

  function handleDateToChange(value: string): void {
    setDateTo(value)
    setPage(1)
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" mb={2}>Rechnungen</Typography>

      <Stack direction="row" gap={2} flexWrap="wrap" mb={2}>
        <Select
          value={statusFilter}
          onChange={(e) => handleStatusChange(e.target.value)}
          displayEmpty
          size="small"
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">Alle Status</MenuItem>
          <MenuItem value="draft">Entwurf</MenuItem>
          <MenuItem value="issued">Ausgestellt</MenuItem>
          <MenuItem value="cancelled">Storniert</MenuItem>
        </Select>
        <TextField
          label="Von"
          type="date"
          size="small"
          value={dateFrom}
          onChange={(e) => handleDateFromChange(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => handleDateToChange(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Suche (Rechnungsnr., Kunde)"
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          sx={{ minWidth: 240 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Stack>

      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Nummer</TableCell>
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Kunden-ID</TableCell>
            <TableCell>Datum</TableCell>
            <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Fällig</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Brutto</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={6}>Lädt…</TableCell>
            </TableRow>
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6}>Keine Rechnungen vorhanden.</TableCell>
            </TableRow>
          ) : (
            rows.map((invoice) => (
              <TableRow
                key={invoice.id}
                hover
                onClick={() => navigate(`/invoices/${invoice.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{invoice.invoice_number}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>{invoice.customer_id}</TableCell>
                <TableCell>{invoice.issue_date ? formatDate(invoice.issue_date) : '—'}</TableCell>
                <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>{invoice.due_date ? formatDate(invoice.due_date) : '—'}</TableCell>
                <TableCell>
                  <Chip
                    label={STATUS_LABELS[invoice.status]}
                    color={STATUS_COLORS[invoice.status]}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {invoice.gross_total_cents != null ? formatEuro(invoice.gross_total_cents) : '—'}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {totalPages > 1 && (
        <Box mt={2} display="flex" flexDirection="column" alignItems="center" gap={1}>
          <Typography variant="body2" color="text.secondary">
            Seite {page} von {totalPages} — {total} Einträge
          </Typography>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, p) => setPage(p)}
            color="primary"
          />
        </Box>
      )}

      <Fab
        color="primary"
        onClick={() => setOpen(true)}
        sx={{ position: 'fixed', bottom: 32, right: 32 }}
      >
        <AddIcon />
      </Fab>

      <InvoiceFormDialog open={open} onClose={() => setOpen(false)} />
    </Box>
  )
}
