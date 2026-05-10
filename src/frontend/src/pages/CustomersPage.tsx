import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useCreateCustomer, useCustomers, useDeleteCustomer, useUpdateCustomer } from '../features/customers/api'
import type { Customer } from '../types/invoice'

const customerSchema = z.object({
  name: z.string().min(1, 'Name ist Pflichtfeld'),
  street: z.string().optional(),
  postal_code: z.string().optional(),
  city: z.string().optional(),
  country: z.string().default('DE'),
  vat_id: z.string().optional(),
  email: z.string().email('Ungültige E-Mail').optional().or(z.literal('')),
})

type CustomerForm = z.infer<typeof customerSchema>

export default function CustomersPage(): JSX.Element {
  const { data: customers = [], isLoading } = useCustomers()
  const createCustomer = useCreateCustomer()
  const updateCustomer = useUpdateCustomer()
  const deleteCustomer = useDeleteCustomer()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Customer | null>(null)

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<CustomerForm>({
    resolver: zodResolver(customerSchema),
    defaultValues: { country: 'DE' },
  })

  function openCreate(): void {
    setEditing(null)
    reset({ name: '', street: '', postal_code: '', city: '', country: 'DE', vat_id: '', email: '' })
    setDialogOpen(true)
  }

  function openEdit(customer: Customer): void {
    setEditing(customer)
    reset({
      name: customer.name,
      street: customer.street ?? '',
      postal_code: customer.postal_code ?? '',
      city: customer.city ?? '',
      country: customer.country,
      vat_id: customer.vat_id ?? '',
      email: customer.email ?? '',
    })
    setDialogOpen(true)
  }

  async function onSubmit(values: CustomerForm): Promise<void> {
    const payload = { ...values, email: values.email || undefined }
    if (editing) {
      await updateCustomer.mutateAsync({ id: editing.id, payload })
    } else {
      await createCustomer.mutateAsync(payload)
    }
    setDialogOpen(false)
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Kunden</Typography>
        <Button variant="contained" onClick={openCreate}>Neuen Kunden anlegen</Button>
      </Stack>

      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Name</TableCell>
            <TableCell>Stadt</TableCell>
            <TableCell>E-Mail</TableCell>
            <TableCell>USt-IdNr.</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow><TableCell colSpan={5}>Lädt…</TableCell></TableRow>
          ) : (
            customers.map((c) => (
              <TableRow key={c.id} hover>
                <TableCell>{c.name}</TableCell>
                <TableCell>{[c.postal_code, c.city].filter(Boolean).join(' ') || '—'}</TableCell>
                <TableCell>{c.email ?? '—'}</TableCell>
                <TableCell>{c.vat_id ?? '—'}</TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => openEdit(c)}><EditIcon fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => deleteCustomer.mutate(c.id)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? 'Kunde bearbeiten' : 'Neuen Kunden anlegen'}</DialogTitle>
        <DialogContent>
          <Stack gap={2} sx={{ mt: 1 }}>
            <TextField {...register('name')} label="Name" required fullWidth error={!!errors.name} helperText={errors.name?.message} />
            <TextField {...register('street')} label="Straße" fullWidth />
            <Stack direction="row" gap={2}>
              <TextField {...register('postal_code')} label="PLZ" sx={{ width: 120 }} />
              <TextField {...register('city')} label="Ort" fullWidth />
            </Stack>
            <TextField {...register('country')} label="Land" sx={{ width: 80 }} />
            <TextField {...register('vat_id')} label="USt-IdNr." fullWidth />
            <TextField {...register('email')} label="E-Mail" fullWidth error={!!errors.email} helperText={errors.email?.message} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Abbrechen</Button>
          <Button onClick={handleSubmit(onSubmit)} variant="contained" disabled={isSubmitting}>
            Speichern
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
