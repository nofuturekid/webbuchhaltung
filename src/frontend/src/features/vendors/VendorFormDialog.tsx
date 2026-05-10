import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useCreateVendor, useUpdateVendor } from './api'
import type { Vendor } from '../../types/vendor'

// IBAN: 15-34 alphanumeric characters (client-side only)
const ibanRegex = /^[A-Z0-9]{15,34}$/

const vendorSchema = z.object({
  name: z.string().min(1, 'Name ist Pflichtfeld'),
  street: z.string().optional(),
  postal_code: z.string().optional(),
  city: z.string().optional(),
  country: z.string().default('DE'),
  vat_id: z.string().optional(),
  email: z
    .string()
    .email('Ungültige E-Mail-Adresse')
    .optional()
    .or(z.literal('')),
  bank_iban: z
    .string()
    .optional()
    .transform((v) => (v ? v.replace(/\s/g, '').toUpperCase() : v))
    .pipe(
      z
        .string()
        .regex(ibanRegex, 'IBAN muss 15-34 alphanumerische Zeichen haben')
        .optional()
        .or(z.literal(''))
    ),
  bank_bic: z.string().optional(),
})

type VendorFormValues = z.infer<typeof vendorSchema>

export type VendorFormDialogProps = {
  open: boolean
  onClose: () => void
  vendor?: Vendor
}

export function VendorFormDialog({ open, onClose, vendor }: VendorFormDialogProps): JSX.Element {
  const createVendor = useCreateVendor()
  const updateVendor = useUpdateVendor()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<VendorFormValues>({
    resolver: zodResolver(vendorSchema),
    defaultValues: vendor
      ? {
          name: vendor.name,
          street: vendor.street ?? '',
          postal_code: vendor.postal_code ?? '',
          city: vendor.city ?? '',
          country: vendor.country,
          vat_id: vendor.vat_id ?? '',
          email: vendor.email ?? '',
          bank_iban: vendor.bank_iban ?? '',
          bank_bic: vendor.bank_bic ?? '',
        }
      : {
          name: '',
          street: '',
          postal_code: '',
          city: '',
          country: 'DE',
          vat_id: '',
          email: '',
          bank_iban: '',
          bank_bic: '',
        },
  })

  async function onSubmit(values: VendorFormValues): Promise<void> {
    const payload = {
      name: values.name,
      street: values.street || null,
      postal_code: values.postal_code || null,
      city: values.city || null,
      country: values.country || 'DE',
      vat_id: values.vat_id || null,
      email: values.email || null,
      bank_iban: values.bank_iban || null,
      bank_bic: values.bank_bic || null,
    }
    if (vendor) {
      await updateVendor.mutateAsync({ id: vendor.id, payload })
    } else {
      await createVendor.mutateAsync(payload)
    }
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{vendor ? 'Lieferant bearbeiten' : 'Neuer Lieferant'}</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          <TextField
            {...register('name')}
            label="Name"
            required
            fullWidth
            error={!!errors.name}
            helperText={errors.name?.message}
          />
          <TextField
            {...register('street')}
            label="Straße"
            fullWidth
            error={!!errors.street}
            helperText={errors.street?.message}
          />
          <Stack direction="row" gap={2}>
            <TextField
              {...register('postal_code')}
              label="PLZ"
              sx={{ width: 120 }}
              error={!!errors.postal_code}
              helperText={errors.postal_code?.message}
            />
            <TextField
              {...register('city')}
              label="Ort"
              fullWidth
              error={!!errors.city}
              helperText={errors.city?.message}
            />
          </Stack>
          <TextField
            {...register('country')}
            label="Land"
            sx={{ width: 80 }}
            error={!!errors.country}
            helperText={errors.country?.message}
          />
          <TextField
            {...register('vat_id')}
            label="USt-IdNr."
            fullWidth
            error={!!errors.vat_id}
            helperText={errors.vat_id?.message}
          />
          <TextField
            {...register('email')}
            label="E-Mail"
            fullWidth
            error={!!errors.email}
            helperText={errors.email?.message}
          />
          <TextField
            {...register('bank_iban')}
            label="Bank IBAN"
            fullWidth
            inputProps={{ style: { textTransform: 'uppercase', fontFamily: 'monospace' } }}
            error={!!errors.bank_iban}
            helperText={errors.bank_iban?.message ?? 'Leerzeichen werden automatisch entfernt'}
          />
          <TextField
            {...register('bank_bic')}
            label="Bank BIC"
            fullWidth
            inputProps={{ style: { fontFamily: 'monospace' } }}
            error={!!errors.bank_bic}
            helperText={errors.bank_bic?.message}
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
          {isSubmitting ? <CircularProgress size={18} /> : 'Speichern'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
