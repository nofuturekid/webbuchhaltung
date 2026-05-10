import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  Grid,
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
import { useNavigate, useParams } from 'react-router-dom'
import { formatEuro, formatDate } from '../lib/formatters'
import {
  downloadInvoicePdf,
  useCancelInvoice,
  useDeleteInvoice,
  useInvoice,
  useIssueInvoice,
  useSendInvoiceEmail,
} from '../features/invoices/api'
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

export default function InvoiceDetailPage(): JSX.Element {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: invoice, isLoading } = useInvoice(id!)

  const issueInvoice = useIssueInvoice()
  const cancelInvoice = useCancelInvoice()
  const deleteInvoice = useDeleteInvoice()
  const sendEmail = useSendInvoiceEmail()

  const [editOpen, setEditOpen] = useState(false)
  const [issueConfirm, setIssueConfirm] = useState(false)
  const [cancelConfirm, setCancelConfirm] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)
  const [overrideEmail, setOverrideEmail] = useState('')
  const [pdfLoading, setPdfLoading] = useState(false)

  if (isLoading || !invoice) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
  }

  async function handleIssue(): Promise<void> {
    await issueInvoice.mutateAsync(invoice!.id)
    setIssueConfirm(false)
  }

  async function handleCancel(): Promise<void> {
    await cancelInvoice.mutateAsync(invoice!.id)
    setCancelConfirm(false)
  }

  async function handleDelete(): Promise<void> {
    await deleteInvoice.mutateAsync(invoice!.id)
    navigate('/invoices')
  }

  async function handlePdf(): Promise<void> {
    setPdfLoading(true)
    try {
      await downloadInvoicePdf(invoice!.id, invoice!.invoice_number)
    } finally {
      setPdfLoading(false)
    }
  }

  async function handleSendEmail(): Promise<void> {
    await sendEmail.mutateAsync({ id: invoice!.id, override_email: overrideEmail || undefined })
    setEmailDialogOpen(false)
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Stack direction="row" gap={2} alignItems="center">
          <Typography variant="h5">{invoice.invoice_number}</Typography>
          <Chip
            label={STATUS_LABELS[invoice.status]}
            color={STATUS_COLORS[invoice.status]}
          />
        </Stack>

        <Stack direction="row" gap={1}>
          {invoice.status === 'draft' && (
            <>
              <Button variant="outlined" onClick={() => setEditOpen(true)}>Bearbeiten</Button>
              <Button variant="contained" color="success" onClick={() => setIssueConfirm(true)}>
                Ausstellen
              </Button>
              <Button color="error" onClick={() => setDeleteConfirm(true)}>Löschen</Button>
            </>
          )}
          {invoice.status === 'issued' && (
            <>
              <Button variant="outlined" onClick={handlePdf} disabled={pdfLoading}>
                {pdfLoading ? <CircularProgress size={18} /> : 'PDF herunterladen'}
              </Button>
              <Button variant="outlined" onClick={() => setEmailDialogOpen(true)}>E-Mail senden</Button>
              <Button color="error" onClick={() => setCancelConfirm(true)}>Stornieren</Button>
            </>
          )}
        </Stack>
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle2" color="text.secondary">Rechnungsdetails</Typography>
          <Divider sx={{ my: 1 }} />
          <Stack gap={1}>
            <Typography><strong>Datum:</strong> {invoice.issue_date ? formatDate(invoice.issue_date) : '—'}</Typography>
            <Typography><strong>Fällig:</strong> {invoice.due_date ? formatDate(invoice.due_date) : '—'}</Typography>
            <Typography><strong>Währung:</strong> {invoice.currency}</Typography>
            {invoice.booking_id && (
              <Typography><strong>Buchung:</strong> {invoice.booking_id}</Typography>
            )}
            {invoice.notes && <Typography><strong>Notizen:</strong> {invoice.notes}</Typography>}
          </Stack>
        </Grid>
      </Grid>

      <Typography variant="subtitle1" sx={{ mt: 3, mb: 1, fontWeight: 'bold' }}>Positionen</Typography>
      <Table size="small">
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Pos.</TableCell>
            <TableCell>Beschreibung</TableCell>
            <TableCell align="right">Menge</TableCell>
            <TableCell>Einheit</TableCell>
            <TableCell align="right">EP netto</TableCell>
            <TableCell align="right">MwSt</TableCell>
            <TableCell align="right">Betrag</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {invoice.line_items.map((li) => (
            <TableRow key={li.id}>
              <TableCell>{li.position}</TableCell>
              <TableCell>{li.description}</TableCell>
              <TableCell align="right">{Number(li.quantity).toFixed(3)}</TableCell>
              <TableCell>{li.unit ?? '—'}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {formatEuro(li.unit_price_cents)}
              </TableCell>
              <TableCell align="right">{Math.round(Number(li.vat_rate) * 100)} %</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {formatEuro((li.net_total_cents ?? 0) + (li.vat_amount_cents ?? 0))}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Stack alignItems="flex-end" mt={2} gap={0.5}>
        <Typography>Netto: <strong>{formatEuro(invoice.net_total_cents ?? 0)}</strong></Typography>
        <Typography>MwSt: <strong>{formatEuro(invoice.vat_total_cents ?? 0)}</strong></Typography>
        <Divider sx={{ width: 200 }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
          Brutto: {formatEuro(invoice.gross_total_cents ?? 0)}
        </Typography>
      </Stack>

      {/* Confirm dialogs */}
      <Dialog open={issueConfirm} onClose={() => setIssueConfirm(false)}>
        <DialogTitle>Rechnung ausstellen?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Die Rechnung wird ausgestellt und eine Buchung erstellt. Dieser Vorgang kann nicht direkt rückgängig gemacht werden.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIssueConfirm(false)}>Abbrechen</Button>
          <Button onClick={handleIssue} variant="contained" color="success" autoFocus>
            Ausstellen
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={cancelConfirm} onClose={() => setCancelConfirm(false)}>
        <DialogTitle>Rechnung stornieren?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Eine Stornobuchung wird erstellt. Die Rechnung wird als storniert markiert.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelConfirm(false)}>Abbrechen</Button>
          <Button onClick={handleCancel} variant="contained" color="error" autoFocus>
            Stornieren
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteConfirm} onClose={() => setDeleteConfirm(false)}>
        <DialogTitle>Entwurf löschen?</DialogTitle>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(false)}>Abbrechen</Button>
          <Button onClick={handleDelete} color="error" autoFocus>Löschen</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={emailDialogOpen} onClose={() => setEmailDialogOpen(false)}>
        <DialogTitle>E-Mail senden</DialogTitle>
        <DialogContent>
          <TextField
            label="Empfänger (leer = Kunden-E-Mail)"
            value={overrideEmail}
            onChange={(e) => setOverrideEmail(e.target.value)}
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEmailDialogOpen(false)}>Abbrechen</Button>
          <Button onClick={handleSendEmail} variant="contained" disabled={sendEmail.isPending}>
            {sendEmail.isPending ? <CircularProgress size={18} /> : 'Senden'}
          </Button>
        </DialogActions>
      </Dialog>

      {invoice.status === 'draft' && (
        <InvoiceFormDialog open={editOpen} onClose={() => setEditOpen(false)} existing={invoice} />
      )}
    </Box>
  )
}
