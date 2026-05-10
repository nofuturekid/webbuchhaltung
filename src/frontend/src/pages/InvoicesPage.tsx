import { Add as AddIcon } from '@mui/icons-material'
import {
  Box,
  Chip,
  Fab,
  MenuItem,
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
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatEuro, formatDate } from '../lib/formatters'
import { useInvoices } from '../features/invoices/api'
import { InvoiceFormDialog } from '../features/invoices/InvoiceFormDialog'
import type { InvoiceStatus } from '../types/invoice'

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

  const { data = [], isLoading } = useInvoices({
    status_filter: statusFilter || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  })

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" mb={2}>Rechnungen</Typography>

      <Stack direction="row" gap={2} flexWrap="wrap" mb={2}>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
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
          onChange={(e) => setDateFrom(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
      </Stack>

      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Nummer</TableCell>
            <TableCell>Kunden-ID</TableCell>
            <TableCell>Datum</TableCell>
            <TableCell>Fällig</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Brutto</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={6}>Lädt…</TableCell>
            </TableRow>
          ) : data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6}>Keine Rechnungen vorhanden.</TableCell>
            </TableRow>
          ) : (
            data.map((invoice) => (
              <TableRow
                key={invoice.id}
                hover
                onClick={() => navigate(`/invoices/${invoice.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{invoice.invoice_number}</TableCell>
                <TableCell>{invoice.customer_id}</TableCell>
                <TableCell>{invoice.issue_date ? formatDate(invoice.issue_date) : '—'}</TableCell>
                <TableCell>{invoice.due_date ? formatDate(invoice.due_date) : '—'}</TableCell>
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
