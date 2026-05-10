import {
  Box,
  Button,
  Chip,
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
  Tooltip,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import PowerOffIcon from '@mui/icons-material/PowerOff'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import BusinessIcon from '@mui/icons-material/Business'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVendors, useDeactivateVendor } from '../features/vendors/api'
import { VendorFormDialog } from '../features/vendors/VendorFormDialog'
import type { Vendor } from '../types/vendor'

export default function VendorsPage(): JSX.Element {
  const navigate = useNavigate()
  const { data: vendors = [], isLoading } = useVendors()
  const deactivate = useDeactivateVendor()

  const [formOpen, setFormOpen] = useState(false)
  const [editVendor, setEditVendor] = useState<Vendor | undefined>(undefined)
  const [confirmDeactivate, setConfirmDeactivate] = useState<Vendor | null>(null)

  function openCreate(): void {
    setEditVendor(undefined)
    setFormOpen(true)
  }

  function openEdit(vendor: Vendor): void {
    setEditVendor(vendor)
    setFormOpen(true)
  }

  function handleDeactivateConfirm(): void {
    if (confirmDeactivate) {
      deactivate.mutate(confirmDeactivate.id)
      setConfirmDeactivate(null)
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Stack direction="row" alignItems="center" gap={1}>
          <BusinessIcon />
          <Typography variant="h5">Lieferanten</Typography>
        </Stack>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          Neuer Lieferant
        </Button>
      </Stack>

      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Name</TableCell>
            <TableCell>Ort</TableCell>
            <TableCell>USt-IdNr.</TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>IBAN</TableCell>
            <TableCell>Status</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={6}>Lädt…</TableCell>
            </TableRow>
          ) : vendors.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6}>Keine Lieferanten vorhanden.</TableCell>
            </TableRow>
          ) : (
            vendors.map((vendor) => (
              <TableRow key={vendor.id} hover>
                <TableCell>{vendor.name}</TableCell>
                <TableCell>
                  {[vendor.postal_code, vendor.city].filter(Boolean).join(' ') || '—'}
                </TableCell>
                <TableCell>{vendor.vat_id ?? '—'}</TableCell>
                <TableCell sx={{ fontFamily: 'monospace' }}>
                  {vendor.bank_iban ?? '—'}
                </TableCell>
                <TableCell>
                  {vendor.is_active ? (
                    <Chip label="Aktiv" color="primary" size="small" />
                  ) : (
                    <Chip label="Inaktiv" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  <Stack direction="row" gap={0.5}>
                    <Tooltip title="Rechnungen anzeigen">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() =>
                          navigate(`/vendor-invoices?vendor_id=${vendor.id}`)
                        }
                      >
                        <ReceiptLongIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Bearbeiten">
                      <IconButton size="small" onClick={() => openEdit(vendor)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {vendor.is_active && (
                      <Tooltip title="Deaktivieren">
                        <IconButton
                          size="small"
                          color="warning"
                          onClick={() => setConfirmDeactivate(vendor)}
                        >
                          <PowerOffIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <VendorFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        vendor={editVendor}
      />

      <Dialog
        open={!!confirmDeactivate}
        onClose={() => setConfirmDeactivate(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Lieferant deaktivieren</DialogTitle>
        <DialogContent>
          <Typography>
            Soll <strong>{confirmDeactivate?.name}</strong> wirklich deaktiviert werden?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDeactivate(null)}>Abbrechen</Button>
          <Button
            onClick={handleDeactivateConfirm}
            color="warning"
            variant="contained"
            disabled={deactivate.isPending}
          >
            Deaktivieren
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
