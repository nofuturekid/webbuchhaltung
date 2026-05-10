import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from '@mui/material'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { usePostVendorInvoice } from '../vendors/api'
import { useAccounts } from '../accounts/api'

const postInvoiceSchema = z.object({
  expense_coa_id: z.string().min(1, 'Aufwandskonto ist Pflichtfeld'),
})

type PostInvoiceFormValues = z.infer<typeof postInvoiceSchema>

export type PostInvoiceDialogProps = {
  open: boolean
  onClose: () => void
  invoiceId: string
}

export function PostInvoiceDialog({
  open,
  onClose,
  invoiceId,
}: PostInvoiceDialogProps): JSX.Element {
  const { data: accounts = [] } = useAccounts()
  const postInvoice = usePostVendorInvoice()

  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<PostInvoiceFormValues>({
    resolver: zodResolver(postInvoiceSchema),
    defaultValues: { expense_coa_id: '' },
  })

  async function onSubmit(values: PostInvoiceFormValues): Promise<void> {
    await postInvoice.mutateAsync({ id: invoiceId, payload: values })
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Rechnung buchen</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Wählen Sie das Aufwandskonto für diese Eingangsrechnung.
          </Typography>
          <Controller
            name="expense_coa_id"
            control={control}
            render={({ field }) => (
              <FormControl fullWidth error={!!errors.expense_coa_id}>
                <InputLabel required>Aufwandskonto</InputLabel>
                <Select {...field} label="Aufwandskonto">
                  {accounts.map((account) => (
                    <MenuItem key={account.id} value={account.id}>
                      {account.account_number} — {account.name}
                    </MenuItem>
                  ))}
                </Select>
                {errors.expense_coa_id && (
                  <FormHelperText>{errors.expense_coa_id.message}</FormHelperText>
                )}
              </FormControl>
            )}
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
          {isSubmitting ? <CircularProgress size={18} /> : 'Buchen'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
