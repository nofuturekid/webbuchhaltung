import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material'
import { useLoginMutation } from '../features/auth/api'
import { useAuthStore } from '../store/auth'

const schema = z.object({
  email: z.string().email('Ungültige E-Mail-Adresse'),
  password: z.string().min(1, 'Passwort erforderlich'),
})

type FormValues = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })
  const login = useLoginMutation()

  async function onSubmit(values: FormValues) {
    const result = await login.mutateAsync(values)
    setTokens(result.accessToken, result.refreshToken)
    navigate('/')
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Paper sx={{ p: 4, width: 360 }}>
        <Typography variant="h5" gutterBottom>WebBuchhaltung</Typography>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="E-Mail"
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
          {login.isError && (
            <Alert severity="error">
              {login.error instanceof Error ? login.error.message : 'Anmeldung fehlgeschlagen.'}
            </Alert>
          )}
          <Button type="submit" variant="contained" loading={login.isPending}>
            Anmelden
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
