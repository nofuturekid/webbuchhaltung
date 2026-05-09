import { Box, Typography } from '@mui/material'
import DatevExport from '../features/datev/DatevExport'

export default function DatevPage() {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>DATEV Export</Typography>
      <DatevExport />
    </Box>
  )
}
