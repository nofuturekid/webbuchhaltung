import { useRef, useState } from 'react'
import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
  Alert,
} from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { useImportMT940 } from './api'
import type { ImportStatsResponse } from '../../types/bank'

const ACCEPTED_EXTENSIONS = '.mt940,.txt,.sta'

export type ImportMT940DialogProps = {
  open: boolean
  onClose: () => void
  accountId: string
  accountName: string
}

export function ImportMT940Dialog({
  open,
  onClose,
  accountId,
  accountName,
}: ImportMT940DialogProps): JSX.Element {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<ImportStatsResponse | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const importMT940 = useImportMT940()

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>): void {
    const file = e.target.files?.[0] ?? null
    setSelectedFile(file)
    setResult(null)
    e.target.value = ''
  }

  async function handleUpload(): Promise<void> {
    if (!selectedFile) return
    const stats = await importMT940.mutateAsync({ accountId, file: selectedFile })
    setResult(stats)
  }

  function handleClose(): void {
    setSelectedFile(null)
    setResult(null)
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>MT940 importieren — {accountName}</DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ mt: 1 }}>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            style={{ display: 'none' }}
            onChange={handleInputChange}
          />

          <Button
            variant="outlined"
            startIcon={<UploadFileIcon />}
            onClick={() => inputRef.current?.click()}
            disabled={importMT940.isPending}
          >
            Datei auswählen
          </Button>

          {selectedFile && (
            <Typography variant="body2" color="text.secondary">
              Ausgewählt: {selectedFile.name}
            </Typography>
          )}

          {importMT940.isError && (
            <Alert severity="error">
              Import fehlgeschlagen. Bitte prüfen Sie das Dateiformat.
            </Alert>
          )}

          {result && (
            <Alert severity="success">
              {result.imported} Buchungen importiert, {result.skipped} übersprungen
            </Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={importMT940.isPending}>
          Schließen
        </Button>
        <Button
          variant="contained"
          onClick={handleUpload}
          disabled={!selectedFile || importMT940.isPending || !!result}
          startIcon={importMT940.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          Hochladen
        </Button>
      </DialogActions>
    </Dialog>
  )
}
