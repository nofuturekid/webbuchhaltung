import {
  Autocomplete,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  Stack,
  TextField,
} from '@mui/material'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { useAccounts } from '../accounts/api'
import { useCreateAsset, useUpdateAsset } from './api'
import type { Asset } from '../../types/asset'
import type { AccountResponse } from '../../types/api'

const assetSchema = z.object({
  name: z.string().min(1, 'Name ist Pflichtfeld'),
  description: z.string().optional(),
  purchase_date: z.string().min(1, 'Kaufdatum ist Pflichtfeld'),
  purchase_amount: z.number({ invalid_type_error: 'Betrag erforderlich' }).positive('Muss > 0 sein'),
  useful_life_months: z
    .number({ invalid_type_error: 'Nutzungsdauer erforderlich' })
    .int()
    .positive('Muss > 0 sein'),
  depreciation_method: z.enum(['linear', 'none']),
  residual_value: z.number({ invalid_type_error: 'Wert erforderlich' }).min(0),
  coa_id: z.string().uuid('Anlagekonto ist Pflichtfeld'),
  depreciation_coa_id: z.string().uuid('Abschreibungskonto ist Pflichtfeld'),
})

type AssetFormValues = z.infer<typeof assetSchema>

export type AssetFormDialogProps = {
  open: boolean
  onClose: () => void
  asset?: Asset
}

export function AssetFormDialog({ open, onClose, asset }: AssetFormDialogProps): JSX.Element {
  const { data: accounts = [] } = useAccounts()
  const createAsset = useCreateAsset()
  const updateAsset = useUpdateAsset()

  const assetAccounts = accounts.filter((a: AccountResponse) =>
    a.account_number.startsWith('0')
  )
  const depreciationAccounts = accounts.filter(
    (a: AccountResponse) =>
      a.account_number.startsWith('4') || a.account_number.startsWith('6')
  )

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<AssetFormValues>({
    resolver: zodResolver(assetSchema),
    defaultValues: asset
      ? {
          name: asset.name,
          description: asset.description ?? '',
          purchase_date: asset.purchase_date,
          purchase_amount: asset.purchase_amount_cents / 100,
          useful_life_months: asset.useful_life_months,
          depreciation_method: asset.depreciation_method,
          residual_value: asset.residual_value_cents / 100,
          coa_id: asset.coa_id,
          depreciation_coa_id: asset.depreciation_coa_id,
        }
      : {
          name: '',
          description: '',
          purchase_date: '',
          purchase_amount: 0,
          useful_life_months: 60,
          depreciation_method: 'linear',
          residual_value: 0,
          coa_id: '',
          depreciation_coa_id: '',
        },
  })

  async function onSubmit(values: AssetFormValues): Promise<void> {
    const payload = {
      name: values.name,
      description: values.description || undefined,
      purchase_date: values.purchase_date,
      purchase_amount_cents: Math.round(values.purchase_amount * 100),
      useful_life_months: values.useful_life_months,
      depreciation_method: values.depreciation_method,
      residual_value_cents: Math.round(values.residual_value * 100),
      coa_id: values.coa_id,
      depreciation_coa_id: values.depreciation_coa_id,
    }
    if (asset) {
      await updateAsset.mutateAsync({ id: asset.id, payload })
    } else {
      await createAsset.mutateAsync(payload)
    }
    onClose()
  }

  const selectedCoaAccount =
    accounts.find((a: AccountResponse) => a.id === (asset?.coa_id ?? '')) ?? null
  const selectedDeprAccount =
    accounts.find((a: AccountResponse) => a.id === (asset?.depreciation_coa_id ?? '')) ?? null

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{asset ? 'Anlagegut bearbeiten' : 'Neues Anlagegut'}</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                {...register('name')}
                label="Name"
                required
                fullWidth
                error={!!errors.name}
                helperText={errors.name?.message}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                {...register('description')}
                label="Beschreibung"
                multiline
                rows={2}
                fullWidth
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                {...register('purchase_date')}
                label="Kaufdatum"
                type="date"
                required
                fullWidth
                InputLabelProps={{ shrink: true }}
                error={!!errors.purchase_date}
                helperText={errors.purchase_date?.message}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                {...register('purchase_amount', { valueAsNumber: true })}
                label="Anschaffungskosten (€)"
                type="number"
                required
                fullWidth
                inputProps={{ step: '0.01', min: '0' }}
                error={!!errors.purchase_amount}
                helperText={errors.purchase_amount?.message}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                {...register('useful_life_months', { valueAsNumber: true })}
                label="Nutzungsdauer (Monate)"
                type="number"
                required
                fullWidth
                inputProps={{ min: '1' }}
                error={!!errors.useful_life_months}
                helperText={errors.useful_life_months?.message}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                {...register('residual_value', { valueAsNumber: true })}
                label="Restwert (€)"
                type="number"
                fullWidth
                inputProps={{ step: '0.01', min: '0' }}
                error={!!errors.residual_value}
                helperText={errors.residual_value?.message}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="depreciation_method"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    select
                    label="Abschreibungsmethode"
                    fullWidth
                    error={!!errors.depreciation_method}
                    helperText={errors.depreciation_method?.message}
                  >
                    <MenuItem value="linear">Linear</MenuItem>
                    <MenuItem value="none">Keine</MenuItem>
                  </TextField>
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="coa_id"
                control={control}
                render={({ field }) => (
                  <Autocomplete<AccountResponse>
                    options={assetAccounts}
                    getOptionLabel={(a) => `${a.account_number} ${a.name}`}
                    defaultValue={selectedCoaAccount}
                    onChange={(_e, val) => field.onChange(val?.id ?? '')}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Anlagekonto"
                        required
                        error={!!errors.coa_id}
                        helperText={errors.coa_id?.message}
                      />
                    )}
                  />
                )}
              />
            </Grid>
            <Grid item xs={12}>
              <Controller
                name="depreciation_coa_id"
                control={control}
                render={({ field }) => (
                  <Autocomplete<AccountResponse>
                    options={depreciationAccounts}
                    getOptionLabel={(a) => `${a.account_number} ${a.name}`}
                    defaultValue={selectedDeprAccount}
                    onChange={(_e, val) => field.onChange(val?.id ?? '')}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Abschreibungskonto"
                        required
                        error={!!errors.depreciation_coa_id}
                        helperText={errors.depreciation_coa_id?.message}
                      />
                    )}
                  />
                )}
              />
            </Grid>
          </Grid>
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
