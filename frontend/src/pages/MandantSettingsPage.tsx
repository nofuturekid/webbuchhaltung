import {
  Box,
  Button,
  CircularProgress,
  Divider,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import api from '../lib/api'

interface BankForm {
  iban: string
  bic: string
}

interface SmtpForm {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password: string
  smtp_from: string
  smtp_from_name: string
}

export default function MandantSettingsPage(): JSX.Element {
  const [tab, setTab] = useState(0)

  const bankForm = useForm<BankForm>()
  const smtpForm = useForm<SmtpForm>({ defaultValues: { smtp_port: 587 } })
  const [smtpTestLoading, setSmtpTestLoading] = useState(false)
  const [smtpTestResult, setSmtpTestResult] = useState<string | null>(null)

  async function saveBankSettings(values: BankForm): Promise<void> {
    await api.patch('/mandants/settings', values)
  }

  async function saveSmtpSettings(values: SmtpForm): Promise<void> {
    await api.patch('/mandants/settings', values)
  }

  async function testSmtp(): Promise<void> {
    setSmtpTestLoading(true)
    setSmtpTestResult(null)
    try {
      await api.post('/mandants/smtp-test')
      setSmtpTestResult('✓ Testmail erfolgreich gesendet')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message
      setSmtpTestResult(`Fehler: ${msg ?? 'Unbekannter Fehler'}`)
    } finally {
      setSmtpTestLoading(false)
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 600 }}>
      <Typography variant="h5" mb={2}>Einstellungen</Typography>

      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Bankverbindung" />
        <Tab label="E-Mail (SMTP)" />
      </Tabs>

      {tab === 0 && (
        <Stack gap={2} component="form" onSubmit={bankForm.handleSubmit(saveBankSettings)}>
          <TextField {...bankForm.register('iban')} label="IBAN" fullWidth inputProps={{ maxLength: 34 }} />
          <TextField {...bankForm.register('bic')} label="BIC" fullWidth inputProps={{ maxLength: 11 }} />
          <Button type="submit" variant="contained" sx={{ alignSelf: 'flex-start' }}>
            Speichern
          </Button>
        </Stack>
      )}

      {tab === 1 && (
        <Stack gap={2} component="form" onSubmit={smtpForm.handleSubmit(saveSmtpSettings)}>
          <TextField {...smtpForm.register('smtp_host')} label="SMTP-Host" fullWidth />
          <TextField {...smtpForm.register('smtp_port', { valueAsNumber: true })} label="Port" type="number" sx={{ width: 120 }} />
          <TextField {...smtpForm.register('smtp_user')} label="Benutzername" fullWidth />
          <TextField {...smtpForm.register('smtp_password')} label="Passwort" type="password" fullWidth />
          <Divider />
          <TextField {...smtpForm.register('smtp_from')} label="Absender-E-Mail" fullWidth />
          <TextField {...smtpForm.register('smtp_from_name')} label="Absendername" fullWidth />
          <Stack direction="row" gap={2} alignItems="center">
            <Button type="submit" variant="contained">Speichern</Button>
            <Button variant="outlined" onClick={testSmtp} disabled={smtpTestLoading}>
              {smtpTestLoading ? <CircularProgress size={18} /> : 'Testmail senden'}
            </Button>
          </Stack>
          {smtpTestResult && (
            <Typography color={smtpTestResult.startsWith('✓') ? 'success.main' : 'error.main'}>
              {smtpTestResult}
            </Typography>
          )}
        </Stack>
      )}
    </Box>
  )
}
