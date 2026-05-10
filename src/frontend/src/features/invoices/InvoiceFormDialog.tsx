import {
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Drawer,
  FormHelperText,
  Grid,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { zodResolver } from '@hookform/resolvers/zod'
import { FormProvider, useForm } from 'react-hook-form'
import { z } from 'zod'
import { LineItemsTable } from './LineItemsTable'
import { useCustomers } from '../customers/api'
import { useCreateInvoice, useUpdateInvoice } from './api'
import type { Invoice } from '../../types/invoice'

const lineItemSchema = z.object({
  position: z.number(),
  description: z.string().min(1, 'Pflichtfeld'),
  quantity: z.number().positive('Muss > 0 sein'),
  unit: z.string().optional(),
  unit_price_cents: z.number().min(0),
  vat_rate: z.number(),
})

const invoiceSchema = z.object({
  customer_id: z.string().uuid('Kunde ist Pflichtfeld'),
  issue_date: z.string().optional(),
  due_date: z.string().optional(),
  notes: z.string().optional(),
  line_items: z.array(lineItemSchema).min(1, 'Mindestens eine Position erforderlich'),
})

export type InvoiceFormValues = z.infer<typeof invoiceSchema>

interface Props {
  open: boolean
  onClose: () => void
  existing?: Invoice
}

export function InvoiceFormDialog({ open, onClose, existing }: Props): JSX.Element {
  const { data: customers = [] } = useCustomers()
  const createInvoice = useCreateInvoice()
  const updateInvoice = useUpdateInvoice()

  const methods = useForm<InvoiceFormValues>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: existing
      ? {
          customer_id: existing.customer_id,
          issue_date: existing.issue_date ?? '',
          due_date: existing.due_date ?? '',
          notes: existing.notes ?? '',
          line_items: existing.line_items.map((li) => ({
            position: li.position,
            description: li.description,
            quantity: li.quantity,
            unit: li.unit ?? '',
            unit_price_cents: li.unit_price_cents,
            vat_rate: Number(li.vat_rate),
          })),
        }
      : {
          customer_id: '',
          issue_date: '',
          due_date: '',
          notes: '',
          line_items: [{ position: 1, description: '', quantity: 1, unit: '', unit_price_cents: 0, vat_rate: 0.19 }],
        },
  })

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = methods

  const selectedCustomerId = watch('customer_id')
  const selectedCustomer = customers.find((c) => c.id === selectedCustomerId) ?? null

  async function onSubmit(values: InvoiceFormValues): Promise<void> {
    const payload = {
      ...values,
      line_items: values.line_items.map((li, i) => ({ ...li, position: i + 1 })),
    }
    if (existing) {
      await updateInvoice.mutateAsync({ id: existing.id, payload })
    } else {
      await createInvoice.mutateAsync(payload)
    }
    onClose()
  }

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', md: '75%' } } }}>
      <FormProvider {...methods}>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="h6">{existing ? 'Rechnung bearbeiten' : 'Neue Rechnung'}</Typography>

          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Autocomplete
                options={customers}
                getOptionLabel={(c) => `${c.name}${c.city ? ` · ${c.city}` : ''}`}
                value={selectedCustomer}
                onChange={(_e, val) => setValue('customer_id', val?.id ?? '')}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Kunde"
                    required
                    error={!!errors.customer_id}
                    helperText={errors.customer_id?.message}
                  />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                {...register('issue_date')}
                label="Rechnungsdatum"
                type="date"
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                {...register('due_date')}
                label="Fälligkeitsdatum"
                type="date"
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                {...register('notes')}
                label="Notizen"
                multiline
                rows={2}
                fullWidth
              />
            </Grid>
          </Grid>

          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Positionen</Typography>
          <LineItemsTable />
          {errors.line_items?.root && (
            <FormHelperText error>{errors.line_items.root.message}</FormHelperText>
          )}

          <Stack direction="row" justifyContent="flex-end" gap={1} sx={{ mt: 'auto' }}>
            <Button onClick={onClose} disabled={isSubmitting}>Abbrechen</Button>
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? <CircularProgress size={18} /> : 'Als Entwurf speichern'}
            </Button>
          </Stack>
        </Box>
      </FormProvider>
    </Drawer>
  )
}
