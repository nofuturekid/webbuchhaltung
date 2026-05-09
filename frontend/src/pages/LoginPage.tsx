import type { FormEvent } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Button, TextField, Typography, Paper } from '@mui/material'
import axios from 'axios'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleLogin(e: FormEvent) {
    e.preventDefault()
    try {
      const { data } = await axios.post('/api/v1/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      navigate('/')
    } catch {
      setError('Invalid email or password.')
    }
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Paper sx={{ p: 4, width: 360 }}>
        <Typography variant="h5" gutterBottom>WebBuchhaltung</Typography>
        <Box component="form" onSubmit={handleLogin} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="E-Mail" value={email} onChange={e => setEmail(e.target.value)} type="email" required />
          <TextField label="Passwort" value={password} onChange={e => setPassword(e.target.value)} type="password" required />
          {error && <Typography color="error">{error}</Typography>}
          <Button type="submit" variant="contained">Anmelden</Button>
        </Box>
      </Paper>
    </Box>
  )
}
