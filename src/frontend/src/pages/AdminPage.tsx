import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Pagination,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import { useAuditLog } from '../features/admin/api'
import type { AuditLogParams } from '../types/admin'

const DATE_FMT = new Intl.DateTimeFormat('de-DE', {
  dateStyle: 'short',
  timeStyle: 'medium',
})

function formatDate(iso: string): string {
  return DATE_FMT.format(new Date(iso))
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text
}

// ─── Tab 1: Audit Log ────────────────────────────────────────────────────────

function AuditLogTab(): JSX.Element {
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 50

  const [filters, setFilters] = useState<Omit<AuditLogParams, 'page'>>({
    table: '',
    action: 'all',
    date_from: '',
    date_to: '',
  })

  const { data, isLoading, isError } = useAuditLog({ page, ...filters })

  function handleFilterChange(
    field: keyof typeof filters,
    value: string,
  ): void {
    setFilters((prev) => ({ ...prev, [field]: value }))
    setPage(1)
  }

  function handleActionChange(e: SelectChangeEvent): void {
    handleFilterChange('action', e.target.value)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  return (
    <Box>
      <Stack direction="row" gap={2} mb={2} flexWrap="wrap">
        <TextField
          label="Tabelle"
          size="small"
          value={filters.table}
          onChange={(e) => handleFilterChange('table', e.target.value)}
          sx={{ width: 180 }}
        />
        <FormControl size="small" sx={{ width: 160 }}>
          <InputLabel>Aktion</InputLabel>
          <Select label="Aktion" value={filters.action ?? 'all'} onChange={handleActionChange}>
            <MenuItem value="all">Alle</MenuItem>
            <MenuItem value="insert">Insert</MenuItem>
            <MenuItem value="update">Update</MenuItem>
            <MenuItem value="delete">Delete</MenuItem>
          </Select>
        </FormControl>
        <TextField
          label="Datum von"
          type="date"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={filters.date_from}
          onChange={(e) => handleFilterChange('date_from', e.target.value)}
          sx={{ width: 160 }}
        />
        <TextField
          label="Datum bis"
          type="date"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={filters.date_to}
          onChange={(e) => handleFilterChange('date_to', e.target.value)}
          sx={{ width: 160 }}
        />
      </Stack>

      <Table size="small">
        <TableHead>
          <TableRow sx={{ '& th': { fontWeight: 'bold' } }}>
            <TableCell>Zeitpunkt</TableCell>
            <TableCell>Benutzer-ID</TableCell>
            <TableCell>Tabelle</TableCell>
            <TableCell>Datensatz-ID</TableCell>
            <TableCell>Aktion</TableCell>
            <TableCell>Änderungen</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={6}>Lädt…</TableCell>
            </TableRow>
          ) : isError ? (
            <TableRow>
              <TableCell colSpan={6}>Fehler beim Laden des Protokolls.</TableCell>
            </TableRow>
          ) : !data || data.items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6}>Keine Einträge vorhanden.</TableCell>
            </TableRow>
          ) : (
            data.items.map((entry) => {
              const summaryText = truncate(JSON.stringify(entry.change_summary), 80)
              return (
                <TableRow key={entry.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12 }}>
                    {formatDate(entry.changed_at)}
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                    {entry.user_id ?? '—'}
                  </TableCell>
                  <TableCell>{entry.table_name}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                    {entry.record_id}
                  </TableCell>
                  <TableCell>{entry.action}</TableCell>
                  <TableCell>
                    <Tooltip title={JSON.stringify(entry.change_summary, null, 2)}>
                      <span style={{ fontFamily: 'monospace', fontSize: 12, cursor: 'help' }}>
                        {summaryText}
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              )
            })
          )}
        </TableBody>
      </Table>

      {totalPages > 1 && (
        <Box mt={2} display="flex" justifyContent="center">
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, p) => setPage(p)}
            color="primary"
          />
        </Box>
      )}
    </Box>
  )
}

// ─── Tab 2: System Info ───────────────────────────────────────────────────────

function SystemTab(): JSX.Element {
  return (
    <Card variant="outlined" sx={{ maxWidth: 520 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Systeminformationen
        </Typography>
        <Stack gap={1.5}>
          <Stack direction="row" justifyContent="space-between">
            <Typography color="text.secondary">Backend-Status</Typography>
            <Typography fontWeight="bold">OK</Typography>
          </Stack>
          <Stack direction="row" justifyContent="space-between">
            <Typography color="text.secondary">Umgebung</Typography>
            <Typography fontFamily="monospace">{window.location.hostname}</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" mt={1}>
            Datenbankversion und Migrationsstand: siehe Backend-Logs.
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}

// ─── Tab 3: Mandant Stub ──────────────────────────────────────────────────────

function MandantTab(): JSX.Element {
  return (
    <Card variant="outlined" sx={{ maxWidth: 520 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Mandantenstammdaten
        </Typography>
        <Typography color="text.secondary">
          Mandantenstammdaten werden in einer zukünftigen Version verwaltet.
        </Typography>
      </CardContent>
    </Card>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AdminPage(): JSX.Element {
  const [tab, setTab] = useState(0)

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" gap={1} mb={3}>
        <AdminPanelSettingsIcon />
        <Typography variant="h5">Administration</Typography>
      </Stack>

      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Buchungsprotokoll" />
        <Tab label="System" />
        <Tab label="Mandant" />
      </Tabs>

      {tab === 0 && <AuditLogTab />}
      {tab === 1 && <SystemTab />}
      {tab === 2 && <MandantTab />}
    </Box>
  )
}
