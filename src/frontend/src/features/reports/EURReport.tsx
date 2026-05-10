import {
  Table, TableHead, TableBody, TableRow, TableCell,
  TableFooter, Typography, Box, Paper, Grid,
} from '@mui/material'
import { formatEuro } from '../../lib/formatters'
import type { EURResponse } from '../../types/api'

interface Props {
  data: EURResponse
}

export default function EURReport({ data }: Props) {
  const profit = data.betriebseinnahmen_cents - data.betriebsausgaben_cents

  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Betriebseinnahmen (netto)</Typography>
            <Typography variant="h6">{formatEuro(data.betriebseinnahmen_cents)}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Betriebsausgaben (netto)</Typography>
            <Typography variant="h6" color="error.main">{formatEuro(data.betriebsausgaben_cents)}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Gewinn</Typography>
            <Typography variant="h6" color={profit >= 0 ? 'success.main' : 'error.main'}>
              {formatEuro(profit)}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">USt (§ 19 EStG)</Typography>
            <Typography variant="h6">{formatEuro(data.ust_cents)}</Typography>
          </Paper>
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mb: 1 }}>Positionen</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Konto</TableCell>
            <TableCell>Bezeichnung</TableCell>
            <TableCell align="right">Brutto</TableCell>
            <TableCell align="right">Steuer</TableCell>
            <TableCell align="right">Netto</TableCell>
            <TableCell align="right">Privatanteil</TableCell>
            <TableCell align="right">Anrechenbar</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.items.map((item) => (
            <TableRow key={item.account_number} hover>
              <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                {item.account_number.padStart(4, '0')}
              </TableCell>
              <TableCell>{item.account_name}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{formatEuro(item.gross_cents)}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{formatEuro(item.tax_cents)}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>{formatEuro(item.net_cents)}</TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                {item.private_deduction_cents ? formatEuro(item.private_deduction_cents) : '–'}
              </TableCell>
              <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                {formatEuro(item.reportable_cents)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell colSpan={6}><strong>Gesamt anrechenbar</strong></TableCell>
            <TableCell align="right" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
              {formatEuro(profit)}
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    </Box>
  )
}
