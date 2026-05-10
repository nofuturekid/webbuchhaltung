import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, Link as RouterLink } from 'react-router-dom'
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  FormHelperText,
} from '@mui/material'
import { useSystemStatus, useSetupMutation } from '../features/setup/api'
import { useAuthStore } from '../store/auth'

const schema = z
  .object({
    email: z.string().email('Ungültige E-Mail-Adresse'),
    password: z.string().min(8, 'Passwort muss mindestens 8 Zeichen haben'),
    confirm_password: z.string().min(1, 'Bitte Passwort bestätigen'),
    mandant_name: z.string().min(1, 'Firmenname erforderlich'),
    skr_variant: z.enum(['skr03', 'skr04', 'skr07']),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'Passwörter stimmen nicht überein',
    path: ['confirm_password'],
  })

type FormValues = z.infer<typeof schema>

export default function SetupPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  const { data: statusData, isLoading: statusLoading } = useSystemStatus()
  const setup = useSetupMutation()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      mandant_name: 'Meine Firma',
      skr_variant: 'skr03',
    },
  })

  useEffect(() => {
    if (!statusLoading && statusData?.needs_setup === false) {
      navigate('/login', { replace: true })
    }
  }, [statusLoading, statusData, navigate])

  async function onSubmit(values: FormValues) {
    const { confirm_password: _, ...requestBody } = values
    const result = await setup.mutateAsync(requestBody)
    setTokens(result.access_token, result.refresh_token)
    navigate('/')
  }

  if (statusLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  const isAlreadySetup =
    setup.isError &&
    setup.error instanceof Error &&
    (setup.error as { status?: number } & Error).status === 404

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Paper sx={{ p: 4, width: 420 }}>
        <Typography variant="h5" gutterBottom>
          WebBuchhaltung — Ersteinrichtung
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Erstellen Sie Ihren Administrator-Account und die erste Buchhaltungseinheit.
        </Typography>
        <Box
          component="form"
          onSubmit={handleSubmit(onSubmit)}
          sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
        >
          <TextField
            label="E-Mail Adresse"
            type="email"
            {...register('email')}
            error={!!errors.email}
            helperText={errors.email?.message}
          />
          <TextField
            label="Passwort"
            type="password"
            {...register('password')}
            error={!!errors.password}
            helperText={errors.password?.message}
          />
          <TextField
            label="Passwort bestätigen"
            type="password"
            {...register('confirm_password')}
            error={!!errors.confirm_password}
            helperText={errors.confirm_password?.message}
          />
          <TextField
            label="Firmenname"
            {...register('mandant_name')}
            error={!!errors.mandant_name}
            helperText={errors.mandant_name?.message}
          />
          <FormControl error={!!errors.skr_variant}>
            <InputLabel id="skr-variant-label">SKR-Variante</InputLabel>
            <Select
              labelId="skr-variant-label"
              label="SKR-Variante"
              defaultValue="skr03"
              {...register('skr_variant')}
            >
              <MenuItem value="skr03">SKR 03 (Standardkontenrahmen)</MenuItem>
              <MenuItem value="skr04">SKR 04 (Industriekontenrahmen)</MenuItem>
              <MenuItem value="skr07">SKR 07 (Wohnungswirtschaft)</MenuItem>
            </Select>
            {errors.skr_variant && (
              <FormHelperText>{errors.skr_variant.message}</FormHelperText>
            )}
          </FormControl>
          {isAlreadySetup ? (
            <Alert severity="error">
              Die Ersteinrichtung wurde bereits abgeschlossen.{' '}
              <RouterLink to="/login">Zur Anmeldung</RouterLink>
            </Alert>
          ) : setup.isError ? (
            <Alert severity="error">
              {setup.error instanceof Error ? setup.error.message : 'Einrichtung fehlgeschlagen.'}
            </Alert>
          ) : null}
          <Button type="submit" variant="contained" loading={setup.isPending}>
            Einrichtung abschließen
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
