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
import { useDisposeAsset } from './api'
import type { Asset } from '../../types/asset'

const disposeSchema = z.object({
  disposal_date: z.string().min(1, 'Datum ist Pflichtfeld'),
  disposal_amount: z.number({ invalid_type_error: 'Betrag erforderlich' }).min(0),
})

type DisposeFormValues = z.infer<typeof disposeSchema>

export type DisposeAssetDialogProps = {
  open: boolean
  onClose: () => void
  asset: Asset
}

export function DisposeAssetDialog({
  open,
  onClose,
  asset,
}: DisposeAssetDialogProps): JSX.Element {
  const disposeAsset = useDisposeAsset()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DisposeFormValues>({
    resolver: zodResolver(disposeSchema),
    defaultValues: {
      disposal_date: '',
      disposal_amount: 0,
    },
  })

  async function onSubmit(values: DisposeFormValues): Promise<void> {
    await disposeAsset.mutateAsync({
      id: asset.id,
      payload: {
        disposal_date: values.disposal_date,
        disposal_amount_cents: Math.round(values.disposal_amount * 100),
      },
    })
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Anlagegut abgehen — {asset.name}</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          <TextField
            {...register('disposal_date')}
            label="Abgangsdatum"
            type="date"
            required
            fullWidth
            InputLabelProps={{ shrink: true }}
            error={!!errors.disposal_date}
            helperText={errors.disposal_date?.message}
          />
          <TextField
            {...register('disposal_amount', { valueAsNumber: true })}
            label="Erlös (€)"
            type="number"
            fullWidth
            inputProps={{ step: '0.01', min: '0' }}
            error={!!errors.disposal_amount}
            helperText={errors.disposal_amount?.message}
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
          color="warning"
          disabled={isSubmitting}
        >
          {isSubmitting ? <CircularProgress size={18} /> : 'Abgang buchen'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
