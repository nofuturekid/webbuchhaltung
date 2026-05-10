import {
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import PowerOffIcon from '@mui/icons-material/PowerOff'
import FileUploadIcon from '@mui/icons-material/FileUpload'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import { useState } from 'react'
import { useBankAccounts, useDeactivateBankAccount, useBankTransactions } from '../features/bank/api'
import { BankAccountFormDialog } from '../features/bank/BankAccountFormDialog'
import { ImportMT940Dialog } from '../features/bank/ImportMT940Dialog'
import { MatchingView } from '../features/bank/MatchingView'
import type { BankAccount, BankTransaction } from '../types/bank'

type TransactionStatus = 'unmatched' | 'matched' | 'ignored'

const STATUS_TABS: { label: string; value: TransactionStatus }[] = [
  { label: 'Nicht abgeglichen', value: 'unmatched' },
  { label: 'Abgeglichen', value: 'matched' },
  { label: 'Ignoriert', value: 'ignored' },
]

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('de-DE').format(new Date(iso))
}

function formatEur(cents: number): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(
    cents / 100
  )
}

type TransactionsPanelProps = {
  account: BankAccount
}

function TransactionsPanel({ account }: TransactionsPanelProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<TransactionStatus>('unmatched')
  const { data, isLoading } = useBankTransactions(account.id, activeTab)

  const transactions: BankTransaction[] = data?.items ?? []

  return (
    <Box sx={{ mt: 2, pl: 2, borderLeft: '3px solid', borderColor: 'primary.light' }}>
      <Tabs
        value={activeTab}
        onChange={(_e, val: TransactionStatus) => setActiveTab(val)}
        sx={{ mb: 2 }}
      >
        {STATUS_TABS.map((tab) => (
          <Tab key={tab.value} label={tab.label} value={tab.value} />
        ))}
      </Tabs>

      {activeTab === 'unmatched' ? (
        <MatchingView accountId={account.id} />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
              <TableCell>Datum</TableCell>
              <TableCell align="right">Betrag</TableCell>
              <TableCell>Verwendungszweck</TableCell>
              <TableCell>Gegenseite</TableCell>
              {activeTab === 'matched' && <TableCell>Buchungs-ID</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5}>Lädt…</TableCell>
              </TableRow>
            ) : transactions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>Keine Transaktionen vorhanden.</TableCell>
              </TableRow>
            ) : (
              transactions.map((tx) => (
                <TableRow key={tx.id} hover>
                  <TableCell>{formatDate(tx.transaction_date)}</TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      fontFamily: 'monospace',
                      color: tx.amount_cents < 0 ? 'error.main' : 'success.main',
                    }}
                  >
                    {formatEur(tx.amount_cents)}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 220 }}>
                    <Typography variant="body2" noWrap title={tx.purpose ?? ''}>
                      {tx.purpose ?? '—'}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ maxWidth: 180 }}>
                    <Typography variant="body2" noWrap title={tx.counterpart_name ?? ''}>
                      {tx.counterpart_name ?? '—'}
                    </Typography>
                  </TableCell>
                  {activeTab === 'matched' && (
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {tx.booking_id ?? '—'}
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}
    </Box>
  )
}

export default function BankAccountsPage(): JSX.Element {
  const { data: accounts = [], isLoading } = useBankAccounts()
  const deactivate = useDeactivateBankAccount()

  const [formOpen, setFormOpen] = useState(false)
  const [editAccount, setEditAccount] = useState<BankAccount | undefined>(undefined)
  const [importAccount, setImportAccount] = useState<BankAccount | null>(null)
  const [expandedAccountId, setExpandedAccountId] = useState<string | null>(null)

  function openCreate(): void {
    setEditAccount(undefined)
    setFormOpen(true)
  }

  function openEdit(account: BankAccount): void {
    setEditAccount(account)
    setFormOpen(true)
  }

  function toggleExpand(accountId: string): void {
    setExpandedAccountId((prev) => (prev === accountId ? null : accountId))
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Stack direction="row" alignItems="center" gap={1}>
          <AccountBalanceIcon />
          <Typography variant="h5">Bankkonten</Typography>
        </Stack>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          Neues Bankkonto
        </Button>
      </Stack>

      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Name</TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>IBAN</TableCell>
            <TableCell>BIC</TableCell>
            <TableCell>Währung</TableCell>
            <TableCell>Status</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={6}>Lädt…</TableCell>
            </TableRow>
          ) : accounts.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6}>Keine Bankkonten vorhanden.</TableCell>
            </TableRow>
          ) : (
            accounts.map((account) => (
              <>
                <TableRow key={account.id} hover>
                  <TableCell>{account.name}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{account.iban}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{account.bic ?? '—'}</TableCell>
                  <TableCell>{account.currency}</TableCell>
                  <TableCell>
                    {account.is_active ? (
                      <Chip label="Aktiv" color="primary" size="small" />
                    ) : (
                      <Chip label="Inaktiv" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" gap={0.5}>
                      <Tooltip title="MT940 importieren">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => setImportAccount(account)}
                        >
                          <FileUploadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Transaktionen">
                        <IconButton
                          size="small"
                          color={expandedAccountId === account.id ? 'primary' : 'default'}
                          onClick={() => toggleExpand(account.id)}
                        >
                          <AccountBalanceIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Bearbeiten">
                        <IconButton size="small" onClick={() => openEdit(account)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {account.is_active && (
                        <Tooltip title="Deaktivieren">
                          <IconButton
                            size="small"
                            color="warning"
                            disabled={deactivate.isPending}
                            onClick={() => deactivate.mutate(account.id)}
                          >
                            <PowerOffIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
                {expandedAccountId === account.id && (
                  <TableRow key={`${account.id}-expanded`}>
                    <TableCell colSpan={6} sx={{ pb: 3 }}>
                      <TransactionsPanel account={account} />
                    </TableCell>
                  </TableRow>
                )}
              </>
            ))
          )}
        </TableBody>
      </Table>

      <BankAccountFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        account={editAccount}
      />

      {importAccount && (
        <ImportMT940Dialog
          open={!!importAccount}
          onClose={() => setImportAccount(null)}
          accountId={importAccount.id}
          accountName={importAccount.name}
        />
      )}
    </Box>
  )
}
