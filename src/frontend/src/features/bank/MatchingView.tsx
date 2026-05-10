import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import BlockIcon from '@mui/icons-material/Block'
import LinkIcon from '@mui/icons-material/Link'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'
import {
  useBankTransactions,
  useIgnoreTransaction,
  useMatchTransaction,
  useAutoMatch,
} from './api'
import type { BankTransaction } from '../../types/bank'

function formatEur(cents: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(
    cents / 100
  )
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('de-DE').format(new Date(iso))
}

type ManualMatchDialogProps = {
  open: boolean
  transaction: BankTransaction | null
  onClose: () => void
}

function ManualMatchDialog({ open, transaction, onClose }: ManualMatchDialogProps): JSX.Element {
  const [bookingId, setBookingId] = useState('')
  const [error, setError] = useState('')
  const matchTransaction = useMatchTransaction()

  async function handleMatch(): Promise<void> {
    if (!transaction) return
    const trimmed = bookingId.trim()
    if (!trimmed) {
      setError('Buchungs-ID ist Pflichtfeld')
      return
    }
    setError('')
    await matchTransaction.mutateAsync({ id: transaction.id, bookingId: trimmed })
    setBookingId('')
    onClose()
  }

  function handleClose(): void {
    setBookingId('')
    setError('')
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>Manuell abgleichen</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          {transaction && (
            <Typography variant="body2" color="text.secondary">
              Transaktion: {formatEur(transaction.amount_cents)} am{' '}
              {formatDate(transaction.transaction_date)}
            </Typography>
          )}
          <TextField
            label="Buchungs-ID"
            value={bookingId}
            onChange={(e) => setBookingId(e.target.value)}
            error={!!error}
            helperText={error}
            fullWidth
            autoFocus
            inputProps={{ style: { fontFamily: 'monospace' } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={matchTransaction.isPending}>
          Abbrechen
        </Button>
        <Button
          variant="contained"
          onClick={handleMatch}
          disabled={matchTransaction.isPending}
          startIcon={
            matchTransaction.isPending ? <CircularProgress size={16} color="inherit" /> : undefined
          }
        >
          Abgleichen
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export type MatchingViewProps = {
  accountId: string
}

export function MatchingView({ accountId }: MatchingViewProps): JSX.Element {
  const { data, isLoading } = useBankTransactions(accountId, 'unmatched')
  const ignoreTransaction = useIgnoreTransaction()
  const autoMatch = useAutoMatch()

  const [matchTarget, setMatchTarget] = useState<BankTransaction | null>(null)
  const [autoMatchResult, setAutoMatchResult] = useState<number | null>(null)

  async function handleAutoMatch(): Promise<void> {
    setAutoMatchResult(null)
    const result = await autoMatch.mutateAsync(accountId)
    setAutoMatchResult(result.matched)
  }

  const transactions = data?.items ?? []

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="subtitle1" fontWeight="bold">
          Nicht abgeglichene Transaktionen
        </Typography>
        <Button
          variant="outlined"
          startIcon={
            autoMatch.isPending ? (
              <CircularProgress size={16} />
            ) : (
              <AutoFixHighIcon />
            )
          }
          onClick={handleAutoMatch}
          disabled={autoMatch.isPending || isLoading}
        >
          Auto-Abgleich
        </Button>
      </Stack>

      {autoMatchResult !== null && (
        <Alert severity="success" onClose={() => setAutoMatchResult(null)} sx={{ mb: 2 }}>
          {autoMatchResult} Transaktionen automatisch abgeglichen
        </Alert>
      )}

      {autoMatch.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Auto-Abgleich fehlgeschlagen.
        </Alert>
      )}

      <Table size="small">
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Datum</TableCell>
            <TableCell align="right">Betrag</TableCell>
            <TableCell>Verwendungszweck</TableCell>
            <TableCell>Gegenseite</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={5}>
                <CircularProgress size={20} />
              </TableCell>
            </TableRow>
          ) : transactions.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5}>Keine nicht abgeglichenen Transaktionen.</TableCell>
            </TableRow>
          ) : (
            transactions.map((tx) => (
              <TableRow key={tx.id} hover>
                <TableCell>{formatDate(tx.transaction_date)}</TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontFamily: 'monospace',
                    color: tx.amount_cents < 0 ? 'error.main' : 'success.main',
                  }}
                >
                  {formatEur(tx.amount_cents)}
                </TableCell>
                <TableCell sx={{ maxWidth: 200 }}>
                  <Typography variant="body2" noWrap title={tx.purpose ?? ''}>
                    {tx.purpose ?? '—'}
                  </Typography>
                </TableCell>
                <TableCell sx={{ maxWidth: 180 }}>
                  <Typography variant="body2" noWrap title={tx.counterpart_name ?? ''}>
                    {tx.counterpart_name ?? '—'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Stack direction="row" gap={0.5}>
                    <Tooltip title="Ignorieren">
                      <IconButton
                        size="small"
                        color="warning"
                        disabled={ignoreTransaction.isPending}
                        onClick={() => ignoreTransaction.mutate(tx.id)}
                      >
                        <BlockIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Manuell abgleichen">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => setMatchTarget(tx)}
                      >
                        <LinkIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <ManualMatchDialog
        open={!!matchTarget}
        transaction={matchTarget}
        onClose={() => setMatchTarget(null)}
      />
    </Box>
  )
}
