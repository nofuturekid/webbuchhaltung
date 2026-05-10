import type { ReactNode } from 'react'
import {
  Box, AppBar, Toolbar, Typography, Drawer, List,
  ListItemButton, ListItemIcon, ListItemText, Divider, IconButton,
} from '@mui/material'
import BookIcon from '@mui/icons-material/MenuBook'
import BusinessCenterIcon from '@mui/icons-material/BusinessCenter'
import DescriptionIcon from '@mui/icons-material/Description'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import BarChartIcon from '@mui/icons-material/BarChart'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import ReceiptIcon from '@mui/icons-material/Receipt'
import PeopleIcon from '@mui/icons-material/People'
import BusinessIcon from '@mui/icons-material/Business'
import SettingsIcon from '@mui/icons-material/Settings'
import LogoutIcon from '@mui/icons-material/Logout'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const DRAWER_WIDTH = 220

const NAV_ITEMS = [
  { label: 'Buchungsjournal', path: '/bookings', icon: <BookIcon /> },
  { label: 'Kontenplan', path: '/accounts', icon: <AccountBalanceIcon /> },
  { label: 'Kontoauszug', path: '/kontoauszug', icon: <ReceiptLongIcon /> },
  { label: 'EÜR', path: '/eur', icon: <BarChartIcon /> },
  { label: 'DATEV Export', path: '/datev', icon: <FileDownloadIcon /> },
]

const NAV_ITEMS_RECHNUNGEN = [
  { label: 'Rechnungen', path: '/invoices', icon: <ReceiptIcon /> },
  { label: 'Kunden', path: '/customers', icon: <PeopleIcon /> },
]

const NAV_ITEMS_ANLAGEN = [
  { label: 'Anlagenverzeichnis', path: '/assets', icon: <BusinessCenterIcon /> },
  { label: 'Belege', path: '/documents', icon: <DescriptionIcon /> },
]

const NAV_ITEMS_BANKING = [
  { label: 'Bankkonten', path: '/bank', icon: <AccountBalanceWalletIcon /> },
]

const NAV_ITEMS_AP = [
  { label: 'Lieferanten', path: '/vendors', icon: <BusinessIcon /> },
  { label: 'Eingangsrechnungen', path: '/vendor-invoices', icon: <ReceiptLongIcon /> },
]

const NAV_ITEMS_SETTINGS = [
  { label: 'Einstellungen', path: '/settings/mandant', icon: <SettingsIcon /> },
]

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  function isSelected(path: string): boolean {
    return location.pathname.startsWith(path)
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>WebBuchhaltung</Typography>
          <IconButton color="inherit" onClick={handleLogout} title="Abmelden">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <List>
          {NAV_ITEMS.map((item) => (
            <ListItemButton
              key={item.path}
              selected={isSelected(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
        <Divider />
        <List>
          {NAV_ITEMS_RECHNUNGEN.map((item) => (
            <ListItemButton
              key={item.path}
              selected={isSelected(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
        <Divider />
        <List>
          {NAV_ITEMS_ANLAGEN.map((item) => (
            <ListItemButton
              key={item.path}
              selected={isSelected(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
        <Divider />
        <List>
          {NAV_ITEMS_BANKING.map((item) => (
            <ListItemButton
              key={item.path}
              selected={isSelected(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
        <Divider />
        <List>
          {NAV_ITEMS_AP.map((item) => (
            <ListItemButton
              key={item.path}
              selected={isSelected(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
        <Divider />
        <List>
          {NAV_ITEMS_SETTINGS.map((item) => (
            <ListItemButton
              key={item.path}
              selected={isSelected(item.path)}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8, ml: `${DRAWER_WIDTH}px` }}>
        {children}
      </Box>
    </Box>
  )
}
