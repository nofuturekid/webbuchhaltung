import { useState } from 'react'
import {
  Box,
  Typography,
  TextField,
  Button,
  Grid,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material'
import { useBilanz } from '../features/reports/api'
import { formatEuro, formatDate } from '../lib/formatters'
import type { BilanzSection } from '../types/reports'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type SectionTreeProps = {
  sections: BilanzSection[];
  depth?: number;
};

function SectionTree({ sections, depth = 0 }: SectionTreeProps) {
  return (
    <>
      {sections.map((section, idx) => (
        <Box key={idx}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              pl: depth * 2,
              py: 0.5,
              fontWeight: section.subsections.length > 0 || depth === 0 ? 'bold' : 'normal',
            }}
          >
            <Typography
              variant="body2"
              sx={{
                fontWeight:
                  section.subsections.length > 0 || depth === 0 ? 'bold' : 'normal',
              }}
            >
              {section.label}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontFamily: 'monospace',
                fontWeight:
                  section.subsections.length > 0 || depth === 0 ? 'bold' : 'normal',
              }}
            >
              {formatEuro(section.amount_cents)}
            </Typography>
          </Box>
          {section.subsections.length > 0 && (
            <SectionTree sections={section.subsections} depth={depth + 1} />
          )}
        </Box>
      ))}
    </>
  )
}

export default function BilanzPage() {
  const [asOfDate, setAsOfDate] = useState(todayIso())
  const [submitted, setSubmitted] = useState(false)

  const { data, isFetching } = useBilanz({ as_of_date: asOfDate }, submitted)

  function handleSubmit() {
    setSubmitted(true)
  }

  function handleDateChange(value: string) {
    setAsOfDate(value)
    setSubmitted(false)
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Bilanz
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'flex-start' }}>
        <TextField
          label="Stand"
          type="date"
          size="small"
          value={asOfDate}
          onChange={(e) => handleDateChange(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <Button variant="contained" onClick={handleSubmit}>
          Abrufen
        </Button>
      </Box>

      {isFetching && <CircularProgress />}

      {data && !isFetching && (
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 2 }}>
            Stand: {formatDate(data.as_of_date)}
          </Typography>

          {!data.balanced && (
            <Alert severity="warning" sx={{ mb: 2, bgcolor: 'warning.light' }}>
              Bilanz nicht ausgeglichen — Differenz: {formatEuro(data.imbalance_cents)}
            </Alert>
          )}

          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ mb: 1, fontWeight: 'bold' }}>
                Aktiva
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <SectionTree sections={data.aktiva} />
              <Divider sx={{ mt: 1, mb: 0.5 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', pt: 0.5 }}>
                <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                  Summe Aktiva
                </Typography>
                <Typography
                  variant="body1"
                  sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}
                >
                  {formatEuro(data.aktiva_total_cents)}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ mb: 1, fontWeight: 'bold' }}>
                Passiva
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <SectionTree sections={data.passiva} />
              <Divider sx={{ mt: 1, mb: 0.5 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', pt: 0.5 }}>
                <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                  Summe Passiva
                </Typography>
                <Typography
                  variant="body1"
                  sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}
                >
                  {formatEuro(data.passiva_total_cents)}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Box>
      )}
    </Box>
  )
}
