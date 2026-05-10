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
import { useCreateBankAccount, useUpdateBankAccount } from './api'
import type { BankAccount } from '../../types/bank'

// IBAN: 15-34 alphanumeric characters (client-side only)
const ibanRegex = /^[A-Z0-9]{15,34}$/

const bankAccountSchema = z.object({
  name: z.string().min(1, 'Name ist Pflichtfeld'),
  iban: z
    .string()
    .min(1, 'IBAN ist Pflichtfeld')
    .transform((v) => v.replace(/\s/g, '').toUpperCase())
    .pipe(z.string().regex(ibanRegex, 'IBAN muss 15-34 alphanumerische Zeichen haben')),
  bic: z.string().optional(),
  currency: z.string().default('EUR'),
})

type BankAccountFormValues = z.infer<typeof bankAccountSchema>

export type BankAccountFormDialogProps = {
  open: boolean
  onClose: () => void
  account?: BankAccount
}

export function BankAccountFormDialog({
  open,
  onClose,
  account,
}: BankAccountFormDialogProps): JSX.Element {
  const createAccount = useCreateBankAccount()
  const updateAccount = useUpdateBankAccount()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<BankAccountFormValues>({
    resolver: zodResolver(bankAccountSchema),
    defaultValues: account
      ? {
          name: account.name,
          iban: account.iban,
          bic: account.bic ?? '',
          currency: account.currency,
        }
      : {
          name: '',
          iban: '',
          bic: '',
          currency: 'EUR',
        },
  })

  async function onSubmit(values: BankAccountFormValues): Promise<void> {
    const payload = {
      name: values.name,
      iban: values.iban,
      bic: values.bic || undefined,
      currency: values.currency || 'EUR',
    }
    if (account) {
      await updateAccount.mutateAsync({ id: account.id, payload })
    } else {
      await createAccount.mutateAsync(payload)
    }
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{account ? 'Bankkonto bearbeiten' : 'Neues Bankkonto'}</DialogTitle>
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
            {...register('iban')}
            label="IBAN"
            required
            fullWidth
            inputProps={{ style: { textTransform: 'uppercase', fontFamily: 'monospace' } }}
            error={!!errors.iban}
            helperText={errors.iban?.message ?? 'Leerzeichen werden automatisch entfernt'}
          />
          <TextField
            {...register('bic')}
            label="BIC (optional)"
            fullWidth
            inputProps={{ style: { fontFamily: 'monospace' } }}
            error={!!errors.bic}
            helperText={errors.bic?.message}
          />
          <TextField
            {...register('currency')}
            label="Währung"
            fullWidth
            error={!!errors.currency}
            helperText={errors.currency?.message}
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
