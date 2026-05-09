import {
  Table, TableHead, TableBody, TableRow, TableCell,
  Typography, Chip, Box,
} from '@mui/material'
import { formatEuro, formatDate } from '../../lib/formatters'
import type { KontoauszugResponse } from '../../types/api'

interface Props {
  data: KontoauszugResponse
}

export default function Kontoauszug({ data }: Props) {
  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 4, mb: 2 }}>
        <Typography variant="body2">
          <strong>Konto:</strong> {data.account_number} – {data.account_name}
        </Typography>
        <Typography variant="body2">
          <strong>Anfangssaldo:</strong> {formatEuro(data.opening_balance_cents)}
        </Typography>
        <Typography variant="body2">
          <strong>Endsaldo:</strong> {formatEuro(data.closing_balance_cents)}
        </Typography>
      </Box>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Nr.</TableCell>
            <TableCell>Datum</TableCell>
            <TableCell>Beleg</TableCell>
            <TableCell>Text</TableCell>
            <TableCell align="right">Soll</TableCell>
            <TableCell align="right">Haben</TableCell>
            <TableCell align="right">Saldo</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.lines.map((line) => (
            <TableRow key={line.booking_id} hover>
              <TableCell sx={{ fontFamily: 'monospace' }}>{line.entry_number ?? '–'}</TableCell>
              <TableCell>{formatDate(line.date_booking)}</TableCell>
              <TableCell>{line.document_number ?? '–'}</TableCell>
              <TableCell>{line.notes ?? '–'}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {line.debit_cents ? formatEuro(line.debit_cents) : ''}
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {line.credit_cents ? formatEuro(line.credit_cents) : ''}
              </TableCell>
              <TableCell
                align="right"
                sx={{
                  fontFamily: 'monospace',
                  color: line.running_balance_cents < 0 ? 'error.main' : 'inherit',
                }}
              >
                {formatEuro(line.running_balance_cents)}
              </TableCell>
              <TableCell>
                <Chip
                  label={line.status === 'posted' ? 'Gebucht' : line.status}
                  size="small"
                  color={line.status === 'posted' ? 'success' : 'default'}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  )
}
