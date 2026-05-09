import {
  Table, TableHead, TableBody, TableRow, TableCell,
  Chip, IconButton, Tooltip, Box, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import UndoIcon from '@mui/icons-material/Undo'
import DeleteIcon from '@mui/icons-material/Delete'
import { formatEuro, formatDate } from '../../lib/formatters'
import { useBookings, usePostBooking, useReverseBooking, useDeleteBooking } from './api'
import type { BookingResponse } from '../../types/api'

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success' | 'error'> = {
  draft: 'warning',
  posted: 'success',
  reversed: 'error',
}

function StatusChip({ status }: { status: string }) {
  const labels: Record<string, string> = {
    draft: 'Entwurf',
    posted: 'Gebucht',
    reversed: 'Storniert',
  }
  return <Chip label={labels[status] ?? status} color={STATUS_COLORS[status] ?? 'default'} size="small" />
}

export default function BookingList() {
  const { data, isLoading } = useBookings()
  const post = usePostBooking()
  const reverse = useReverseBooking()
  const del = useDeleteBooking()

  if (isLoading) return <Typography>Lade…</Typography>
  if (!data?.items.length) return <Typography color="text.secondary">Keine Buchungen vorhanden.</Typography>

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Nr.</TableCell>
          <TableCell>Datum</TableCell>
          <TableCell>Beleg</TableCell>
          <TableCell>Konto</TableCell>
          <TableCell>Gegenkonto</TableCell>
          <TableCell align="right">Betrag</TableCell>
          <TableCell>Status</TableCell>
          <TableCell />
        </TableRow>
      </TableHead>
      <TableBody>
        {data.items.map((b: BookingResponse) => (
          <TableRow key={b.id} hover>
            <TableCell sx={{ fontFamily: 'monospace' }}>{b.entry_number ?? '–'}</TableCell>
            <TableCell>{formatDate(b.date_booking)}</TableCell>
            <TableCell>{b.document_number ?? '–'}</TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>{b.coa_id ?? '–'}</TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>{b.counter_coa_id ?? '–'}</TableCell>
            <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
              {formatEuro(b.amount_cents)}
            </TableCell>
            <TableCell><StatusChip status={b.status} /></TableCell>
            <TableCell>
              <Box sx={{ display: 'flex', gap: 0 }}>
                {b.status === 'draft' && (
                  <>
                    <Tooltip title="Buchen">
                      <IconButton size="small" onClick={() => post.mutate(b.id)}>
                        <CheckCircleIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Löschen">
                      <IconButton size="small" onClick={() => del.mutate(b.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </>
                )}
                {b.status === 'posted' && (
                  <Tooltip title="Stornieren">
                    <IconButton size="small" onClick={() => reverse.mutate(b.id)}>
                      <UndoIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
