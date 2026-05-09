import { useState } from 'react'
import {
  Box, Typography, TextField, Button, Autocomplete,
} from '@mui/material'
import { useAccounts } from '../features/accounts/api'
import { useKontoauszug } from '../features/reports/api'
import KontoauszugComponent from '../features/reports/Kontoauszug'
import type { AccountResponse } from '../types/api'

function currentYearRange() {
  const y = new Date().getFullYear()
  return { from: `${y}-01-01`, to: `${y}-12-31` }
}

export default function KontoauszugPage() {
  const range = currentYearRange()
  const [accountId, setAccountId] = useState('')
  const [dateFrom, setDateFrom] = useState(range.from)
  const [dateTo, setDateTo] = useState(range.to)
  const [submitted, setSubmitted] = useState(false)

  const { data: accounts = [] } = useAccounts()
  const { data, isFetching } = useKontoauszug(
    accountId, dateFrom, dateTo,
    submitted && !!accountId
  )

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Kontoauszug</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Autocomplete
          options={accounts.filter((a) => a.is_active)}
          getOptionLabel={(a: AccountResponse) => `${a.account_number.padStart(4, '0')} – ${a.name}`}
          onChange={(_, v) => { setAccountId(v?.id ?? ''); setSubmitted(false) }}
          sx={{ width: 300 }}
          renderInput={(params) => <TextField {...params} label="Konto" size="small" />}
        />
        <TextField
          label="Von"
          type="date"
          size="small"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          label="Bis"
          type="date"
          size="small"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <Button
          variant="contained"
          onClick={() => setSubmitted(true)}
          disabled={!accountId}
        >
          Anzeigen
        </Button>
      </Box>
      {isFetching && <Typography>Lade…</Typography>}
      {data && !isFetching && <KontoauszugComponent data={data} />}
    </Box>
  )
}
