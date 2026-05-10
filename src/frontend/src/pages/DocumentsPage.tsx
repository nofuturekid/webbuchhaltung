import { useState } from 'react'
import {
  Box,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Pagination,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useDocuments, useUploadDocument, useProcessDocument } from '../features/documents/api'
import { UploadDropzone } from '../features/documents/UploadDropzone'
import { ExtractionReviewPanel } from '../features/documents/ExtractionReviewPanel'
import type { DocumentRecord, DocumentStatus } from '../types/document'

function formatEur(cents: number | null): string {
  if (cents === null) return '—'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100)
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('de-DE').format(new Date(iso))
}

type StatusFilter = DocumentStatus | 'all'

const STATUS_FILTERS: { label: string; value: StatusFilter }[] = [
  { label: 'Alle', value: 'all' },
  { label: 'Hochgeladen', value: 'uploaded' },
  { label: 'Verarbeitet', value: 'processed' },
  { label: 'Gebucht', value: 'booked' },
  { label: 'Abgelehnt', value: 'rejected' },
]

function StatusChip({ status }: { status: DocumentStatus }): JSX.Element {
  const MAP: Record<DocumentStatus, { label: string; color: 'default' | 'warning' | 'success' | 'error' }> = {
    uploaded: { label: 'Hochgeladen', color: 'default' },
    processed: { label: 'Verarbeitet', color: 'warning' },
    booked: { label: 'Gebucht', color: 'success' },
    rejected: { label: 'Abgelehnt', color: 'error' },
  }
  const { label, color } = MAP[status]
  return <Chip label={label} color={color} size="small" />
}

export default function DocumentsPage(): JSX.Element {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [reviewDoc, setReviewDoc] = useState<DocumentRecord | null>(null)

  const uploadMutation = useUploadDocument()
  const processMutation = useProcessDocument()

  const { data, isLoading } = useDocuments(
    page,
    statusFilter === 'all' ? undefined : statusFilter
  )

  async function handleUpload(file: File): Promise<void> {
    const doc = await uploadMutation.mutateAsync({ file })
    await processMutation.mutateAsync(doc.id)
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" mb={2}>
        Belegerfassung
      </Typography>

      {/* Upload section */}
      <Box mb={3}>
        <UploadDropzone
          onUpload={handleUpload}
          isLoading={uploadMutation.isPending || processMutation.isPending}
        />
      </Box>

      {/* Status filter chips */}
      <Stack direction="row" spacing={1} mb={2}>
        {STATUS_FILTERS.map(({ label, value }) => (
          <Chip
            key={value}
            label={label}
            variant={statusFilter === value ? 'filled' : 'outlined'}
            color={statusFilter === value ? 'primary' : 'default'}
            onClick={() => {
              setStatusFilter(value)
              setPage(1)
            }}
            clickable
          />
        ))}
      </Stack>

      {/* Documents table */}
      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Dateiname</TableCell>
            <TableCell>Datum</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Betrag</TableCell>
            <TableCell>Aktionen</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={5}>Lädt…</TableCell>
            </TableRow>
          ) : (
            (data?.items ?? []).map((doc) => (
              <TableRow key={doc.id} hover>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {doc.filename}
                </TableCell>
                <TableCell>{formatDate(doc.created_at)}</TableCell>
                <TableCell>
                  <StatusChip status={doc.status} />
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEur(doc.extracted_json?.total_amount_cents ?? null)}
                </TableCell>
                <TableCell>
                  {doc.status === 'processed' && (
                    <Chip
                      label="Prüfen"
                      size="small"
                      color="primary"
                      variant="outlined"
                      clickable
                      onClick={() => setReviewDoc(doc)}
                    />
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
          {!isLoading && (data?.items ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={5}>Keine Belege vorhanden.</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {totalPages > 1 && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
          <Pagination count={totalPages} page={page} onChange={(_e, p) => setPage(p)} />
        </Box>
      )}

      {/* Review dialog */}
      <Dialog
        open={!!reviewDoc}
        onClose={() => setReviewDoc(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Beleg prüfen: {reviewDoc?.filename}</Typography>
            <IconButton onClick={() => setReviewDoc(null)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {reviewDoc && (
            <ExtractionReviewPanel
              doc={reviewDoc}
              onConfirm={() => setReviewDoc(null)}
              onReject={() => setReviewDoc(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  )
}
