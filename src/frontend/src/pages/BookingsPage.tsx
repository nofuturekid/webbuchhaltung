import { Box, Typography, Button, Pagination, Stack, TextField } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import SearchIcon from '@mui/icons-material/Search'
import InputAdornment from '@mui/material/InputAdornment'
import { useState, useEffect } from 'react'
import BookingList from '../features/bookings/BookingList'
import BookingForm from '../features/bookings/BookingForm'
import { useBookings } from '../features/bookings/api'

const PAGE_SIZE = 50

export default function BookingsPage(): JSX.Element {
  const [showForm, setShowForm] = useState(false)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [q, setQ] = useState('')

  // Debounce search input 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(searchInput)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Fetch data at page level so we can read total for pagination
  const { data } = useBookings(page, PAGE_SIZE, { q })
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

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

      <Stack direction="row" gap={2} mb={2} flexWrap="wrap" alignItems="center">
        <TextField
          label="Suche (Beschreibung, Belegnr.)"
          size="small"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          sx={{ minWidth: 280 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Stack>

      {showForm && <BookingForm onSuccess={() => setShowForm(false)} />}

      <BookingList page={page} pageSize={PAGE_SIZE} q={q} />

      {totalPages > 1 && (
        <Box mt={2} display="flex" flexDirection="column" alignItems="center" gap={1}>
          <Typography variant="body2" color="text.secondary">
            Seite {page} von {totalPages} — {total} Einträge
          </Typography>
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
