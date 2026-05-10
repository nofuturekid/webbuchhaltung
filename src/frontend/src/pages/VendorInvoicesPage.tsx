import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Select,
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
import AddIcon from '@mui/icons-material/Add'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  useVendorInvoices,
  usePayVendorInvoice,
  useCancelVendorInvoice,
  useSepaExport,
} from '../features/vendors/api'
import { useVendors } from '../features/vendors/api'
import { VendorInvoiceFormDialog } from '../features/vendor-invoices/VendorInvoiceFormDialog'
import { PostInvoiceDialog } from '../features/vendor-invoices/PostInvoiceDialog'
import { formatEuro, formatDate } from '../lib/formatters'
import type { VendorInvoice, VendorInvoiceStatus } from '../types/vendor'

const STATUS_LABELS: Record<VendorInvoiceStatus, string> = {
  draft: 'Entwurf',
  posted: 'Gebucht',
  paid: 'Bezahlt',
  cancelled: 'Storniert',
}

const STATUS_COLORS: Record<
  VendorInvoiceStatus,
  'default' | 'primary' | 'success' | 'error'
> = {
  draft: 'default',
  posted: 'primary',
  paid: 'success',
  cancelled: 'error',
}

type ConfirmAction = {
  type: 'pay' | 'cancel'
  invoice: VendorInvoice
}

export default function VendorInvoicesPage(): JSX.Element {
  const [searchParams] = useSearchParams()

  const [statusFilter, setStatusFilter] = useState('')
  const [vendorFilter, setVendorFilter] = useState(searchParams.get('vendor_id') ?? '')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [newInvoiceOpen, setNewInvoiceOpen] = useState(false)
  const [postInvoice, setPostInvoice] = useState<{ id: string; vatAmountCents: number } | null>(null)
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null)

  const [sepaDialogOpen, setSepaDialogOpen] = useState(false)
  const [sepaDueDate, setSepaDueDate] = useState('')

  const { data: invoices = [], isLoading } = useVendorInvoices({
    status: statusFilter || undefined,
    vendor_id: vendorFilter || undefined,
    due_from: dateFrom || undefined,
    due_to: dateTo || undefined,
  })

  const { data: vendors = [] } = useVendors()
  const payInvoice = usePayVendorInvoice()
  const cancelInvoice = useCancelVendorInvoice()
  const sepaExport = useSepaExport()

  const vendorMap = new Map(vendors.map((v) => [v.id, v.name]))

  function handleConfirm(): void {
    if (!confirmAction) return
    if (confirmAction.type === 'pay') {
      payInvoice.mutate(confirmAction.invoice.id)
    } else {
      cancelInvoice.mutate(confirmAction.invoice.id)
    }
    setConfirmAction(null)
  }

  function handleSepaExport(): void {
    if (!sepaDueDate) return
    sepaExport.mutate({ due_on_or_before: sepaDueDate })
    setSepaDialogOpen(false)
  }

  const showSepaButton = statusFilter === 'posted' || statusFilter === '' || statusFilter === 'all'

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Eingangsrechnungen</Typography>
        <Stack direction="row" gap={1}>
          {showSepaButton && (
            <Button
              variant="outlined"
              startIcon={<FileDownloadIcon />}
              onClick={() => setSepaDialogOpen(true)}
            >
              SEPA-Export
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setNewInvoiceOpen(true)}
          >
            Neue Rechnung
          </Button>
        </Stack>
      </Stack>

      {/* Filter bar */}
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
          <MenuItem value="posted">Gebucht</MenuItem>
          <MenuItem value="paid">Bezahlt</MenuItem>
          <MenuItem value="cancelled">Storniert</MenuItem>
        </Select>

        <Select
          value={vendorFilter}
          onChange={(e) => setVendorFilter(e.target.value)}
          displayEmpty
          size="small"
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">Alle Lieferanten</MenuItem>
          {vendors.map((v) => (
            <MenuItem key={v.id} value={v.id}>
              {v.name}
            </MenuItem>
          ))}
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
            <TableCell>Lieferant</TableCell>
            <TableCell>Belegnummer</TableCell>
            <TableCell>Datum</TableCell>
            <TableCell>Fälligkeit</TableCell>
            <TableCell align="right">Betrag</TableCell>
            <TableCell align="right">MwSt.</TableCell>
            <TableCell>Status</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={8}>Lädt…</TableCell>
            </TableRow>
          ) : invoices.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8}>Keine Eingangsrechnungen vorhanden.</TableCell>
            </TableRow>
          ) : (
            invoices.map((invoice) => (
              <TableRow key={invoice.id} hover>
                <TableCell>{vendorMap.get(invoice.vendor_id) ?? invoice.vendor_id}</TableCell>
                <TableCell>{invoice.invoice_number}</TableCell>
                <TableCell>{formatDate(invoice.invoice_date)}</TableCell>
                <TableCell>{invoice.due_date ? formatDate(invoice.due_date) : '—'}</TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(invoice.amount_cents)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(invoice.vat_amount_cents)}
                </TableCell>
                <TableCell>
                  <Chip
                    label={STATUS_LABELS[invoice.status]}
                    color={STATUS_COLORS[invoice.status]}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Stack direction="row" gap={0.5}>
                    {invoice.status === 'draft' && (
                      <>
                        <Tooltip title="Buchen">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => setPostInvoice({ id: invoice.id, vatAmountCents: invoice.vat_amount_cents ?? 0 })}
                          >
                            <BookmarkAddIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Stornieren">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() =>
                              setConfirmAction({ type: 'cancel', invoice })
                            }
                          >
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                    {invoice.status === 'posted' && (
                      <>
                        <Tooltip title="Als bezahlt markieren">
                          <IconButton
                            size="small"
                            color="success"
                            onClick={() =>
                              setConfirmAction({ type: 'pay', invoice })
                            }
                          >
                            <CheckCircleIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Stornieren">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() =>
                              setConfirmAction({ type: 'cancel', invoice })
                            }
                          >
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Create invoice dialog */}
      <VendorInvoiceFormDialog
        open={newInvoiceOpen}
        onClose={() => setNewInvoiceOpen(false)}
        defaultVendorId={vendorFilter || undefined}
      />

      {/* Post invoice dialog */}
      {postInvoice && (
        <PostInvoiceDialog
          open={!!postInvoice}
          onClose={() => setPostInvoice(null)}
          invoiceId={postInvoice.id}
          vatAmountCents={postInvoice.vatAmountCents}
        />
      )}

      {/* Pay / Cancel confirm dialog */}
      <Dialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {confirmAction?.type === 'pay' ? 'Rechnung bezahlen' : 'Rechnung stornieren'}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {confirmAction?.type === 'pay'
              ? 'Rechnung als bezahlt markieren?'
              : 'Rechnung unwiderruflich stornieren?'}
          </Typography>
          {confirmAction && (
            <Typography variant="body2" color="text.secondary" mt={1}>
              Belegnr.: {confirmAction.invoice.invoice_number} —{' '}
              {formatEuro(confirmAction.invoice.amount_cents)}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmAction(null)}>Abbrechen</Button>
          <Button
            onClick={handleConfirm}
            variant="contained"
            color={confirmAction?.type === 'pay' ? 'success' : 'error'}
            disabled={payInvoice.isPending || cancelInvoice.isPending}
          >
            {confirmAction?.type === 'pay' ? 'Bezahlt' : 'Stornieren'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* SEPA export dialog */}
      <Dialog
        open={sepaDialogOpen}
        onClose={() => setSepaDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>SEPA-Export</DialogTitle>
        <DialogContent>
          <Stack gap={2} sx={{ mt: 1 }}>
            <Typography variant="body2">
              Exportiert alle gebuchten Zahlungen mit Fälligkeitsdatum bis zum gewählten
              Datum als SEPA-XML (pain.001).
            </Typography>
            <TextField
              label="Fällig bis"
              type="date"
              fullWidth
              value={sepaDueDate}
              onChange={(e) => setSepaDueDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSepaDialogOpen(false)}>Abbrechen</Button>
          <Button
            onClick={handleSepaExport}
            variant="contained"
            disabled={!sepaDueDate || sepaExport.isPending}
            startIcon={<FileDownloadIcon />}
          >
            Exportieren
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
