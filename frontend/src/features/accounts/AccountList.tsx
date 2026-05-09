import { useState } from 'react'
import {
  Table, TableHead, TableBody, TableRow, TableCell,
  TextField, IconButton, Tooltip, Typography, Chip,
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import { useAccounts, useUpdateAccount } from './api'
import { formatAccountNumber } from '../../lib/formatters'
import type { AccountResponse } from '../../types/api'

interface EditablePrivateShareProps {
  account: AccountResponse
}

function EditablePrivateShare({ account }: EditablePrivateShareProps): JSX.Element {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(String(account.private_share_percent))
  const update = useUpdateAccount()

  async function save(): Promise<void> {
    const pct = parseInt(value, 10)
    if (isNaN(pct) || pct < 0 || pct > 100) return
    await update.mutateAsync({ id: account.id, body: { private_share_percent: pct } })
    setEditing(false)
  }

  if (!editing) {
    return (
      <span>
        {account.private_share_percent}%
        <Tooltip title="Bearbeiten">
          <IconButton size="small" onClick={() => setEditing(true)}>
            <EditIcon fontSize="inherit" />
          </IconButton>
        </Tooltip>
      </span>
    )
  }

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <TextField
        size="small"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        sx={{ width: 72 }}
        slotProps={{ htmlInput: { min: 0, max: 100 } }}
        type="number"
      />
      <IconButton size="small" onClick={save}><CheckIcon fontSize="inherit" /></IconButton>
      <IconButton size="small" onClick={() => setEditing(false)}><CloseIcon fontSize="inherit" /></IconButton>
    </span>
  )
}

export default function AccountList(): JSX.Element {
  const { data: accounts = [], isLoading } = useAccounts()

  if (isLoading) return <Typography>Lade…</Typography>

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Konto</TableCell>
          <TableCell>Bezeichnung</TableCell>
          <TableCell>Klasse</TableCell>
          <TableCell>Privatanteil</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {accounts.filter((a) => a.is_active).map((a) => (
          <TableRow key={a.id} hover>
            <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
              {formatAccountNumber(a.account_number)}
            </TableCell>
            <TableCell>{a.name}</TableCell>
            <TableCell>
              <Chip label={a.account_class} size="small" variant="outlined" />
            </TableCell>
            <TableCell>
              <EditablePrivateShare account={a} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
