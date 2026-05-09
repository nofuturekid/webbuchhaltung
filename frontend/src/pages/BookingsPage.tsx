import { Box, Typography, Button } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { useState } from 'react'
import BookingList from '../features/bookings/BookingList'
import BookingForm from '../features/bookings/BookingForm'

export default function BookingsPage() {
  const [showForm, setShowForm] = useState(false)

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <Typography variant="h4" sx={{ flexGrow: 1 }}>Buchungsjournal</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setShowForm(!showForm)}
        >
          Neue Buchung
        </Button>
      </Box>
      {showForm && <BookingForm onSuccess={() => setShowForm(false)} />}
      <BookingList />
    </Box>
  )
}
