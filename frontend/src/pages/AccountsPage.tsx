import { Box, Typography } from '@mui/material'
import AccountList from '../features/accounts/AccountList'

export default function AccountsPage(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>Kontenplan</Typography>
      <AccountList />
    </Box>
  )
}
