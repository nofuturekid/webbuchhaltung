import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material'
import {
  Box,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useFieldArray, useFormContext, useWatch } from 'react-hook-form'
import { formatEuro } from '../../lib/formatters'
import type { InvoiceFormValues } from './InvoiceFormDialog'

const VAT_RATES = [
  { label: '19 %', value: 0.19 },
  { label: '7 %', value: 0.07 },
  { label: '0 %', value: 0.0 },
]

function computeGross(qty: number, price: number, rate: number): number {
  const net = Math.round(qty * price)
  const vat = Math.round(net * rate)
  return net + vat
}

export function LineItemsTable(): JSX.Element {
  const { register, control, formState: { errors } } = useFormContext<InvoiceFormValues>()
  const { fields, append, remove } = useFieldArray({ control, name: 'line_items' })
  const watchedItems = useWatch({ control, name: 'line_items' })

  const netTotal = watchedItems?.reduce((acc, item) => {
    return acc + Math.round((Number(item.quantity) || 0) * (Number(item.unit_price_cents) || 0))
  }, 0) ?? 0

  const vatByRate = watchedItems?.reduce<Record<string, number>>((acc, item) => {
    const net = Math.round((Number(item.quantity) || 0) * (Number(item.unit_price_cents) || 0))
    const rate = String(item.vat_rate)
    acc[rate] = (acc[rate] ?? 0) + Math.round(net * (Number(item.vat_rate) || 0))
    return acc
  }, {}) ?? {}

  const grossTotal = netTotal + Object.values(vatByRate).reduce((a, b) => a + b, 0)

  return (
    <Box>
      <Table size="small" component={Paper} sx={{ mb: 1 }}>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold', bgcolor: 'grey.100' } }}>
            <TableCell sx={{ width: 40 }}>Pos.</TableCell>
            <TableCell>Beschreibung</TableCell>
            <TableCell sx={{ width: 80 }}>Menge</TableCell>
            <TableCell sx={{ width: 80 }}>Einheit</TableCell>
            <TableCell sx={{ width: 120 }}>EP (Cent)</TableCell>
            <TableCell sx={{ width: 100 }}>MwSt</TableCell>
            <TableCell align="right" sx={{ width: 110 }}>Brutto</TableCell>
            <TableCell sx={{ width: 40 }} />
          </TableRow>
        </TableHead>
        <TableBody>
          {fields.map((field, index) => {
            const item = watchedItems?.[index]
            const gross = computeGross(
              Number(item?.quantity) || 0,
              Number(item?.unit_price_cents) || 0,
              Number(item?.vat_rate) || 0,
            )
            return (
              <TableRow key={field.id}>
                <TableCell>{index + 1}</TableCell>
                <TableCell>
                  <TextField
                    {...register(`line_items.${index}.description`)}
                    size="small"
                    fullWidth
                    error={!!errors.line_items?.[index]?.description}
                    placeholder="Beschreibung"
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    {...register(`line_items.${index}.quantity`, { valueAsNumber: true })}
                    size="small"
                    type="number"
                    inputProps={{ step: '0.001', min: '0' }}
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    {...register(`line_items.${index}.unit`)}
                    size="small"
                    placeholder="Std."
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    {...register(`line_items.${index}.unit_price_cents`, { valueAsNumber: true })}
                    size="small"
                    type="number"
                    inputProps={{ min: '0' }}
                    placeholder="Cent"
                  />
                </TableCell>
                <TableCell>
                  <Select
                    {...register(`line_items.${index}.vat_rate`, { valueAsNumber: true })}
                    size="small"
                    defaultValue={0.19}
                  >
                    {VAT_RATES.map((r) => (
                      <MenuItem key={r.value} value={r.value}>{r.label}</MenuItem>
                    ))}
                  </Select>
                </TableCell>
                <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                  {formatEuro(gross)}
                </TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => remove(index)} color="error">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
        <IconButton
          onClick={() =>
            append({ position: fields.length + 1, description: '', quantity: 1, unit: '', unit_price_cents: 0, vat_rate: 0.19 })
          }
          color="primary"
          size="small"
        >
          <AddIcon /> <Typography variant="caption" sx={{ ml: 0.5 }}>Position hinzufügen</Typography>
        </IconButton>

        <Box sx={{ textAlign: 'right', minWidth: 200 }}>
          <Typography variant="body2">Netto: <strong>{formatEuro(netTotal)}</strong></Typography>
          {Object.entries(vatByRate).map(([rate, vatCents]) => (
            <Typography key={rate} variant="body2">
              MwSt. {Math.round(parseFloat(rate) * 100)} %: <strong>{formatEuro(vatCents)}</strong>
            </Typography>
          ))}
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', borderTop: 1, borderColor: 'divider', pt: 0.5, mt: 0.5 }}>
            Brutto: {formatEuro(grossTotal)}
          </Typography>
        </Box>
      </Stack>
    </Box>
  )
}
