import { useEffect, useRef, useState } from 'react'
import {
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Grid,
  LinearProgress,
  TextField,
  Typography,
} from '@mui/material'
import { useForm, Controller } from 'react-hook-form'
import { useAccounts } from '../accounts/api'
import { useBookingSuggestion, useConfirmDocument, useRejectDocument } from './api'
import type { DocumentRecord } from '../../types/document'
import type { ConfirmDocumentRequest } from '../../types/document'
import type { AccountResponse } from '../../types/api'

export type ExtractionReviewPanelProps = {
  doc: DocumentRecord
  onConfirm: () => void
  onReject: () => void
}

function formatEur(cents: number | null): string {
  if (cents === null) return '—'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100)
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('de-DE').format(new Date(iso))
}

interface ConfirmFormValues {
  debit_coa_id: string
  credit_coa_id: string
  amount_cents: number
  booking_text: string
  booking_date: string
  tax_key_code?: number
}

export function ExtractionReviewPanel({
  doc,
  onConfirm,
  onReject,
}: ExtractionReviewPanelProps): JSX.Element {
  const { data: suggestion, isLoading: suggestionLoading } = useBookingSuggestion(doc.id)
  const { data: accounts = [] } = useAccounts()
  const confirmMutation = useConfirmDocument()
  const rejectMutation = useRejectDocument()

  const [fileUrl, setFileUrl] = useState<string | null>(null)
  const objectUrlRef = useRef<string | null>(null)

  // Fetch document file as blob and create object URL
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    let cancelled = false

    fetch(`/api/v1/documents/${doc.id}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.blob())
      .then((blob) => {
        if (cancelled) return
        const url = URL.createObjectURL(blob)
        objectUrlRef.current = url
        setFileUrl(url)
      })
      .catch(() => {
        // file preview unavailable — not blocking
      })

    return () => {
      cancelled = true
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current)
        objectUrlRef.current = null
      }
    }
  }, [doc.id])

  const extraction = suggestion?.extraction ?? doc.extracted_json

  const { control, handleSubmit, reset } = useForm<ConfirmFormValues>({
    defaultValues: {
      debit_coa_id: '',
      credit_coa_id: '',
      amount_cents: extraction?.total_amount_cents ?? 0,
      booking_text: extraction?.booking_text ?? '',
      booking_date: new Date().toISOString().split('T')[0],
    },
  })

  // Pre-fill form when suggestion arrives
  useEffect(() => {
    if (!suggestion) return
    const ex = suggestion.extraction
    reset({
      debit_coa_id: suggestion.debit_coa_id ?? '',
      credit_coa_id: suggestion.credit_coa_id ?? '',
      amount_cents: ex.total_amount_cents ?? 0,
      booking_text: ex.booking_text ?? '',
      booking_date: ex.document_date ?? new Date().toISOString().split('T')[0],
    })
  }, [suggestion, reset])

  function findAccount(id: string): AccountResponse | null {
    return accounts.find((a) => a.id === id) ?? null
  }

  async function onSubmit(values: ConfirmFormValues): Promise<void> {
    const payload: ConfirmDocumentRequest = {
      debit_coa_id: values.debit_coa_id,
      credit_coa_id: values.credit_coa_id,
      amount_cents: Math.round(values.amount_cents),
      booking_text: values.booking_text,
      booking_date: values.booking_date,
      ...(values.tax_key_code !== undefined ? { tax_key_code: values.tax_key_code } : {}),
    }
    await confirmMutation.mutateAsync({ id: doc.id, payload })
    onConfirm()
  }

  async function handleReject(): Promise<void> {
    await rejectMutation.mutateAsync(doc.id)
    onReject()
  }

  const isPdf = doc.mime_type === 'application/pdf'

  return (
    <Grid container spacing={3} sx={{ minHeight: 500 }}>
      {/* Left: file preview */}
      <Grid item xs={12} md={6}>
        <Box
          sx={{
            height: 500,
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'grey.50',
          }}
        >
          {fileUrl ? (
            isPdf ? (
              <iframe
                src={fileUrl}
                title="Belegvorschau"
                width="100%"
                height="100%"
                style={{ border: 'none' }}
              />
            ) : (
              <img
                src={fileUrl}
                alt="Belegvorschau"
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
              />
            )
          ) : (
            <CircularProgress />
          )}
        </Box>
      </Grid>

      {/* Right: extraction data + form */}
      <Grid item xs={12} md={6}>
        {suggestionLoading ? (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
            {/* Readonly extraction fields */}
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Erkannte Daten
            </Typography>

            <Grid container spacing={1} mb={2}>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Lieferant
                </Typography>
                <Typography variant="body2">{extraction?.vendor_name ?? '—'}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Datum
                </Typography>
                <Typography variant="body2">{formatDate(extraction?.document_date ?? null)}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Betrag
                </Typography>
                <Typography variant="body2" fontFamily="monospace">
                  {formatEur(extraction?.total_amount_cents ?? null)}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  MwSt.
                </Typography>
                <Typography variant="body2" fontFamily="monospace">
                  {formatEur(extraction?.vat_amount_cents ?? null)}
                </Typography>
              </Grid>
            </Grid>

            <Box mb={2}>
              <Typography variant="caption" color="text.secondary">
                Konfidenzscore
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <LinearProgress
                  variant="determinate"
                  value={(extraction?.confidence_score ?? 0) * 100}
                  sx={{ flexGrow: 1 }}
                />
                <Typography variant="caption">
                  {Math.round((extraction?.confidence_score ?? 0) * 100)}%
                </Typography>
              </Box>
            </Box>

            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Buchung bestätigen
            </Typography>

            {/* Debit account */}
            <Controller
              name="debit_coa_id"
              control={control}
              rules={{ required: true }}
              render={({ field, fieldState }) => (
                <Autocomplete
                  options={accounts}
                  getOptionLabel={(a: AccountResponse) =>
                    `${a.account_number} – ${a.name}`
                  }
                  value={findAccount(field.value)}
                  onChange={(_e, val) => field.onChange(val?.id ?? '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Sollkonto"
                      size="small"
                      margin="dense"
                      error={!!fieldState.error}
                      required
                    />
                  )}
                />
              )}
            />

            {/* Credit account */}
            <Controller
              name="credit_coa_id"
              control={control}
              rules={{ required: true }}
              render={({ field, fieldState }) => (
                <Autocomplete
                  options={accounts}
                  getOptionLabel={(a: AccountResponse) =>
                    `${a.account_number} – ${a.name}`
                  }
                  value={findAccount(field.value)}
                  onChange={(_e, val) => field.onChange(val?.id ?? '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Habenkonto"
                      size="small"
                      margin="dense"
                      error={!!fieldState.error}
                      required
                    />
                  )}
                />
              )}
            />

            {/* Amount in EUR (display), stored as cents */}
            <Controller
              name="amount_cents"
              control={control}
              rules={{ required: true, min: 1 }}
              render={({ field, fieldState }) => (
                <TextField
                  label="Betrag (EUR)"
                  size="small"
                  margin="dense"
                  fullWidth
                  type="number"
                  inputProps={{ step: '0.01', min: '0' }}
                  value={field.value / 100}
                  onChange={(e) => field.onChange(Math.round(parseFloat(e.target.value) * 100))}
                  error={!!fieldState.error}
                  required
                />
              )}
            />

            {/* Booking text */}
            <Controller
              name="booking_text"
              control={control}
              rules={{ required: true, maxLength: 60 }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Buchungstext"
                  size="small"
                  margin="dense"
                  fullWidth
                  inputProps={{ maxLength: 60 }}
                  error={!!fieldState.error}
                  required
                />
              )}
            />

            {/* Booking date */}
            <Controller
              name="booking_date"
              control={control}
              rules={{ required: true }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Buchungsdatum"
                  size="small"
                  margin="dense"
                  fullWidth
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  error={!!fieldState.error}
                  required
                />
              )}
            />

            {/* Actions */}
            <Box display="flex" gap={2} mt={3}>
              <Button
                type="submit"
                variant="contained"
                disabled={confirmMutation.isPending}
                startIcon={
                  confirmMutation.isPending ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : undefined
                }
              >
                Bestätigen
              </Button>
              <Button
                variant="outlined"
                color="error"
                onClick={handleReject}
                disabled={rejectMutation.isPending}
                startIcon={
                  rejectMutation.isPending ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : undefined
                }
              >
                Ablehnen
              </Button>
            </Box>
          </Box>
        )}
      </Grid>
    </Grid>
  )
}
