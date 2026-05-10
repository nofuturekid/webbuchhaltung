import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  InputLabel,
  FormControl,
  FormHelperText,
} from '@mui/material'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { useCreateVendorInvoice } from '../vendors/api'
import { useVendors } from '../vendors/api'

const vendorInvoiceSchema = z.object({
  vendor_id: z.string().min(1, 'Lieferant ist Pflichtfeld'),
  invoice_number: z.string().min(1, 'Belegnummer ist Pflichtfeld'),
  invoice_date: z.string().min(1, 'Belegdatum ist Pflichtfeld'),
  due_date: z.string().optional(),
  amount_euros: z
    .string()
    .min(1, 'Betrag ist Pflichtfeld')
    .refine((v) => !isNaN(parseFloat(v.replace(',', '.'))), 'Ungültiger Betrag'),
  vat_amount_euros: z
    .string()
    .optional()
    .refine(
      (v) => !v || !isNaN(parseFloat(v.replace(',', '.'))),
      'Ungültiger MwSt.-Betrag'
    ),
  notes: z.string().optional(),
})

type VendorInvoiceFormValues = z.infer<typeof vendorInvoiceSchema>

function eurosToCents(euros: string): number {
  return Math.round(parseFloat(euros.replace(',', '.')) * 100)
}

export type VendorInvoiceFormDialogProps = {
  open: boolean
  onClose: () => void
  defaultVendorId?: string
}

export function VendorInvoiceFormDialog({
  open,
  onClose,
  defaultVendorId,
}: VendorInvoiceFormDialogProps): JSX.Element {
  const { data: vendors = [] } = useVendors()
  const createInvoice = useCreateVendorInvoice()

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<VendorInvoiceFormValues>({
    resolver: zodResolver(vendorInvoiceSchema),
    defaultValues: {
      vendor_id: defaultVendorId ?? '',
      invoice_number: '',
      invoice_date: '',
      due_date: '',
      amount_euros: '',
      vat_amount_euros: '',
      notes: '',
    },
  })

  async function onSubmit(values: VendorInvoiceFormValues): Promise<void> {
    await createInvoice.mutateAsync({
      vendor_id: values.vendor_id,
      invoice_number: values.invoice_number,
      invoice_date: values.invoice_date,
      due_date: values.due_date || null,
      amount_cents: eurosToCents(values.amount_euros),
      vat_amount_cents: values.vat_amount_euros
        ? eurosToCents(values.vat_amount_euros)
        : 0,
      notes: values.notes || null,
    })
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Neue Eingangsrechnung</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          <Controller
            name="vendor_id"
            control={control}
            render={({ field }) => (
              <FormControl fullWidth error={!!errors.vendor_id}>
                <InputLabel required>Lieferant</InputLabel>
                <Select {...field} label="Lieferant">
                  {vendors.map((v) => (
                    <MenuItem key={v.id} value={v.id}>
                      {v.name}
                    </MenuItem>
                  ))}
                </Select>
                {errors.vendor_id && (
                  <FormHelperText>{errors.vendor_id.message}</FormHelperText>
                )}
              </FormControl>
            )}
          />
          <TextField
            {...register('invoice_number')}
            label="Belegnummer"
            required
            fullWidth
            error={!!errors.invoice_number}
            helperText={errors.invoice_number?.message}
          />
          <TextField
            {...register('invoice_date')}
            label="Belegdatum"
            type="date"
            required
            fullWidth
            InputLabelProps={{ shrink: true }}
            error={!!errors.invoice_date}
            helperText={errors.invoice_date?.message}
          />
          <TextField
            {...register('due_date')}
            label="Fälligkeitsdatum"
            type="date"
            fullWidth
            InputLabelProps={{ shrink: true }}
            error={!!errors.due_date}
            helperText={errors.due_date?.message}
          />
          <Stack direction="row" gap={2}>
            <TextField
              {...register('amount_euros')}
              label="Betrag (EUR)"
              required
              fullWidth
              inputProps={{ style: { textAlign: 'right', fontFamily: 'monospace' } }}
              error={!!errors.amount_euros}
              helperText={errors.amount_euros?.message ?? 'z.B. 119,00'}
            />
            <TextField
              {...register('vat_amount_euros')}
              label="MwSt.-Betrag (EUR)"
              fullWidth
              inputProps={{ style: { textAlign: 'right', fontFamily: 'monospace' } }}
              error={!!errors.vat_amount_euros}
              helperText={errors.vat_amount_euros?.message ?? 'z.B. 19,00'}
            />
          </Stack>
          <TextField
            {...register('notes')}
            label="Notizen"
            fullWidth
            multiline
            rows={2}
            error={!!errors.notes}
            helperText={errors.notes?.message}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isSubmitting}>
          Abbrechen
        </Button>
        <Button
          onClick={handleSubmit(onSubmit)}
          variant="contained"
          disabled={isSubmitting}
        >
          {isSubmitting ? <CircularProgress size={18} /> : (
            <Typography variant="button">Speichern</Typography>
          )}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
