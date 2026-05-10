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
  vat_coa_id: z.string().optional(),
})

type PostInvoiceFormValues = z.infer<typeof postInvoiceSchema>

export type PostInvoiceDialogProps = {
  open: boolean
  onClose: () => void
  invoiceId: string
  /** Gross VAT amount in cents — when 0 the Vorsteuer select is hidden */
  vatAmountCents?: number
}

export function PostInvoiceDialog({
  open,
  onClose,
  invoiceId,
  vatAmountCents = 0,
}: PostInvoiceDialogProps): JSX.Element {
  const { data: accounts = [] } = useAccounts()
  const postInvoice = usePostVendorInvoice()

  const showVatSelect = vatAmountCents > 0

  // Vorsteuer accounts: SKR03 uses 157x range, SKR04 uses 140x range
  const vatAccounts = accounts.filter(
    (a) => a.account_number.startsWith('157') || a.account_number.startsWith('140'),
  )

  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<PostInvoiceFormValues>({
    resolver: zodResolver(postInvoiceSchema),
    defaultValues: { expense_coa_id: '', vat_coa_id: '' },
  })

  async function onSubmit(values: PostInvoiceFormValues): Promise<void> {
    const payload = {
      expense_coa_id: values.expense_coa_id,
      // Only send vat_coa_id when selected and non-empty
      ...(values.vat_coa_id ? { vat_coa_id: values.vat_coa_id } : {}),
    }
    await postInvoice.mutateAsync({ id: invoiceId, payload })
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
          {showVatSelect && (
            <Controller
              name="vat_coa_id"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.vat_coa_id}>
                  <InputLabel>Vorsteuer-Konto</InputLabel>
                  <Select {...field} label="Vorsteuer-Konto" displayEmpty>
                    <MenuItem value="">
                      <em>Kein Vorsteuerabzug</em>
                    </MenuItem>
                    {vatAccounts.map((account) => (
                      <MenuItem key={account.id} value={account.id}>
                        {account.account_number} — {account.name}
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>
                    Optional — nur bei Rechnungen mit Vorsteuerabzug (§15 UStG)
                  </FormHelperText>
                </FormControl>
              )}
            />
          )}
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
