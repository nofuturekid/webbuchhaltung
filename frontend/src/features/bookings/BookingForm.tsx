import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Box, Paper, Typography, TextField, Button,
  Autocomplete, MenuItem, Alert, Grid2 as Grid,
} from '@mui/material'
import { useAccounts } from '../accounts/api'
import { useCreateBooking } from './api'
import { euroToCents } from '../../lib/formatters'
import type { AccountResponse } from '../../types/api'

const schema = z.object({
  date_booking: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Format: JJJJ-MM-TT'),
  amount: z
    .string()
    .min(1, 'Betrag erforderlich')
    .refine((v) => !isNaN(parseFloat(v.replace(',', '.'))), 'Ungültiger Betrag'),
  document_number: z.string().max(12).optional().or(z.literal('')),
  notes: z.string().max(60).optional().or(z.literal('')),
  coa_id: z.string().uuid('Konto wählen'),
  counter_coa_id: z.string().uuid('Gegenkonto wählen'),
  tax_rate: z.enum(['', '0.19', '0.07']),
})

type FormValues = z.infer<typeof schema>

export type BookingFormProps = {
  onSuccess: () => void
}

export default function BookingForm({ onSuccess }: BookingFormProps) {
  const { data: accounts = [] } = useAccounts()
  const create = useCreateBooking()

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      date_booking: new Date().toISOString().slice(0, 10),
      amount: '',
      document_number: '',
      notes: '',
      coa_id: '',
      counter_coa_id: '',
      tax_rate: '',
    },
  })

  const amountValue = watch('amount')
  const taxRateValue = watch('tax_rate')

  function computeTaxCents(): number | undefined {
    if (!taxRateValue) return undefined
    const gross = euroToCents(amountValue || '0')
    const rate = parseFloat(taxRateValue)
    return Math.round((gross * rate) / (1 + rate))
  }

  async function onSubmit(values: FormValues): Promise<void> {
    const amount_cents = euroToCents(values.amount)
    const tax_amount_cents = computeTaxCents()
    await create.mutateAsync({
      date_booking: values.date_booking,
      amount_cents,
      coa_id: values.coa_id,
      counter_coa_id: values.counter_coa_id,
      document_number: values.document_number || undefined,
      notes: values.notes || undefined,
      tax_rate: values.tax_rate || undefined,
      tax_amount_cents: tax_amount_cents ?? undefined,
    })
    onSuccess()
  }

  const accountOptions = accounts.filter((a) => a.is_active)

  function accountLabel(a: AccountResponse): string {
    return `${a.account_number.padStart(4, '0')} – ${a.name}`
  }

  const taxCents = computeTaxCents()

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>Neue Buchung</Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 3 }}>
            <TextField
              label="Buchungsdatum"
              type="date"
              fullWidth
              {...register('date_booking')}
              error={!!errors.date_booking}
              helperText={errors.date_booking?.message}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 3 }}>
            <TextField
              label="Betrag (€)"
              fullWidth
              {...register('amount')}
              error={!!errors.amount}
              helperText={errors.amount?.message}
              placeholder="0,00"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 2 }}>
            <TextField
              label="Steuersatz"
              select
              fullWidth
              defaultValue=""
              {...register('tax_rate')}
            >
              <MenuItem value="">Kein</MenuItem>
              <MenuItem value="0.19">19 % USt/VSt</MenuItem>
              <MenuItem value="0.07">7 % USt/VSt</MenuItem>
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, sm: 2 }}>
            <TextField
              label="Steuerbetrag"
              fullWidth
              value={taxCents !== undefined ? (taxCents / 100).toFixed(2) : ''}
              slotProps={{ input: { readOnly: true }, inputLabel: { shrink: true } }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 2 }}>
            <TextField
              label="Belegnummer"
              fullWidth
              {...register('document_number')}
              error={!!errors.document_number}
              helperText={errors.document_number?.message}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Controller
              name="coa_id"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  options={accountOptions}
                  getOptionLabel={accountLabel}
                  onChange={(_, v) => field.onChange(v?.id ?? '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Konto (Soll)"
                      error={!!errors.coa_id}
                      helperText={errors.coa_id?.message}
                    />
                  )}
                />
              )}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Controller
              name="counter_coa_id"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  options={accountOptions}
                  getOptionLabel={accountLabel}
                  onChange={(_, v) => field.onChange(v?.id ?? '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Gegenkonto (Haben)"
                      error={!!errors.counter_coa_id}
                      helperText={errors.counter_coa_id?.message}
                    />
                  )}
                />
              )}
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <TextField
              label="Buchungstext"
              fullWidth
              {...register('notes')}
              error={!!errors.notes}
              helperText={errors.notes?.message}
            />
          </Grid>
        </Grid>
        {create.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {create.error instanceof Error ? create.error.message : 'Fehler beim Speichern.'}
          </Alert>
        )}
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          <Button type="submit" variant="contained" loading={create.isPending}>
            Speichern
          </Button>
          <Button variant="outlined" onClick={() => onSuccess()}>
            Abbrechen
          </Button>
        </Box>
      </Box>
    </Paper>
  )
}
