import {
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd'
import { useState } from 'react'
import { useDepreciationSchedule, useBookDepreciation } from './api'
import type { Asset } from '../../types/asset'

function formatEur(cents: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(
    cents / 100
  )
}

export type DepreciationScheduleModalProps = {
  open: boolean
  onClose: () => void
  asset: Asset
}

export function DepreciationScheduleModal({
  open,
  onClose,
  asset,
}: DepreciationScheduleModalProps): JSX.Element {
  const { data: schedule = [], isLoading } = useDepreciationSchedule(asset.id)
  const bookDepreciation = useBookDepreciation()
  const [bookingRow, setBookingRow] = useState<string | null>(null)

  async function handleBook(entryId: string, year: number, month: number): Promise<void> {
    setBookingRow(entryId)
    try {
      await bookDepreciation.mutateAsync({
        id: asset.id,
        payload: { period_year: year, period_month: month },
      })
    } finally {
      setBookingRow(null)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Abschreibungsplan — {asset.name}
      </DialogTitle>
      <DialogContent>
        {isLoading ? (
          <Typography>Lädt…</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
                <TableCell>Jahr</TableCell>
                <TableCell>Monat</TableCell>
                <TableCell align="right">Betrag</TableCell>
                <TableCell align="right">Kumuliert</TableCell>
                <TableCell align="right">Restbuchwert</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Aktion</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {schedule.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.period_year}</TableCell>
                  <TableCell>{row.period_month}</TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                    {formatEur(row.amount_cents)}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                    {formatEur(row.cumulative_depreciation_cents)}
                  </TableCell>
                  <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                    {formatEur(row.net_book_value_cents)}
                  </TableCell>
                  <TableCell>
                    {row.is_posted ? (
                      <Chip label="Gebucht" color="success" size="small" />
                    ) : (
                      <Chip label="Offen" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    {!row.is_posted && (
                      <IconButton
                        size="small"
                        title="Abschreibung buchen"
                        disabled={bookingRow === row.id}
                        onClick={() => handleBook(row.id, row.period_year, row.period_month)}
                      >
                        {bookingRow === row.id ? (
                          <CircularProgress size={16} />
                        ) : (
                          <BookmarkAddIcon fontSize="small" />
                        )}
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {schedule.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7}>Kein Abschreibungsplan vorhanden.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Schließen</Button>
      </DialogActions>
    </Dialog>
  )
}
