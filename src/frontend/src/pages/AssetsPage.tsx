import {
  Box,
  Button,
  Chip,
  IconButton,
  Pagination,
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
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline'
import { useState } from 'react'
import { useAssets } from '../features/assets/api'
import { AssetFormDialog } from '../features/assets/AssetFormDialog'
import { DepreciationScheduleModal } from '../features/assets/DepreciationScheduleModal'
import { DisposeAssetDialog } from '../features/assets/DisposeAssetDialog'
import type { Asset } from '../types/asset'

function formatEur(cents: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(
    cents / 100
  )
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('de-DE').format(new Date(iso))
}

export default function AssetsPage(): JSX.Element {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useAssets(page)

  const [formOpen, setFormOpen] = useState(false)
  const [editAsset, setEditAsset] = useState<Asset | undefined>(undefined)
  const [scheduleAsset, setScheduleAsset] = useState<Asset | null>(null)
  const [disposeAsset, setDisposeAsset] = useState<Asset | null>(null)

  function openCreate(): void {
    setEditAsset(undefined)
    setFormOpen(true)
  }

  function openEdit(asset: Asset): void {
    setEditAsset(asset)
    setFormOpen(true)
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Anlagenverzeichnis</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          Neues Anlagegut
        </Button>
      </Stack>

      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Nr.</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Kaufdatum</TableCell>
            <TableCell align="right">Anschaffungskosten</TableCell>
            <TableCell align="right">Restbuchwert</TableCell>
            <TableCell>Status</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={7}>Lädt…</TableCell>
            </TableRow>
          ) : (
            (data?.items ?? []).map((asset) => (
              <TableRow key={asset.id} hover>
                <TableCell sx={{ fontFamily: 'monospace' }}>{asset.asset_number}</TableCell>
                <TableCell>{asset.name}</TableCell>
                <TableCell>{formatDate(asset.purchase_date)}</TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEur(asset.purchase_amount_cents)}
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEur(asset.net_book_value_cents)}
                </TableCell>
                <TableCell>
                  {asset.status === 'active' ? (
                    <Chip label="Aktiv" color="primary" size="small" />
                  ) : (
                    <Chip label="Abgeschrieben" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  <Stack direction="row" gap={0.5}>
                    {asset.status === 'active' && (
                      <Tooltip title="Bearbeiten">
                        <IconButton size="small" onClick={() => openEdit(asset)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Abschreibungsplan">
                      <IconButton size="small" onClick={() => setScheduleAsset(asset)}>
                        <CalendarMonthIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {asset.status === 'active' && (
                      <Tooltip title="Abgang">
                        <IconButton
                          size="small"
                          color="warning"
                          onClick={() => setDisposeAsset(asset)}
                        >
                          <RemoveCircleOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            ))
          )}
          {!isLoading && (data?.items ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={7}>Keine Anlagegüter vorhanden.</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {totalPages > 1 && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_e, p) => setPage(p)}
          />
        </Box>
      )}

      <AssetFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        asset={editAsset}
      />

      {scheduleAsset && (
        <DepreciationScheduleModal
          open={!!scheduleAsset}
          onClose={() => setScheduleAsset(null)}
          asset={scheduleAsset}
        />
      )}

      {disposeAsset && (
        <DisposeAssetDialog
          open={!!disposeAsset}
          onClose={() => setDisposeAsset(null)}
          asset={disposeAsset}
        />
      )}
    </Box>
  )
}
