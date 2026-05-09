import type { ReactNode } from 'react'
import { Box, AppBar, Toolbar, Typography, Button } from '@mui/material'
import { useNavigate } from 'react-router-dom'

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  function handleLogout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>WebBuchhaltung</Typography>
          <Button color="inherit" onClick={handleLogout}>Abmelden</Button>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ p: 3, flexGrow: 1 }}>{children}</Box>
    </Box>
  )
}
