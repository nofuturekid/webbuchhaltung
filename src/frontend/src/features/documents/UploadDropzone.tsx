import { useRef, useState } from 'react'
import { Box, Button, Typography, CircularProgress } from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'

export type UploadDropzoneProps = {
  onUpload: (file: File) => void
  isLoading?: boolean
}

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png']
const ACCEPTED_EXTENSIONS = '.pdf,.jpg,.jpeg,.png'

function formatKb(bytes: number): string {
  return `${Math.round(bytes / 1024)} KB`
}

export function UploadDropzone({ onUpload, isLoading = false }: UploadDropzoneProps): JSX.Element {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFileSelect(file: File): void {
    if (!ACCEPTED_TYPES.includes(file.type)) return
    setSelectedFile(file)
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>): void {
    const file = e.target.files?.[0]
    if (file) handleFileSelect(file)
    // reset input so same file can be re-selected
    e.target.value = ''
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>): void {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave(): void {
    setIsDragging(false)
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>): void {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }

  function handleUpload(): void {
    if (selectedFile) {
      onUpload(selectedFile)
    }
  }

  return (
    <Box
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !isLoading && inputRef.current?.click()}
      sx={{
        border: '2px dashed',
        borderColor: isDragging ? 'primary.main' : 'grey.400',
        borderRadius: 2,
        p: 4,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 1,
        cursor: isLoading ? 'default' : 'pointer',
        backgroundColor: isDragging ? 'action.hover' : 'background.paper',
        transition: 'border-color 0.2s, background-color 0.2s',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        style={{ display: 'none' }}
        onChange={handleInputChange}
        disabled={isLoading}
      />

      <UploadFileIcon sx={{ fontSize: 48, color: 'text.secondary' }} />

      {selectedFile ? (
        <Box textAlign="center">
          <Typography variant="body1" fontWeight="medium">
            {selectedFile.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {formatKb(selectedFile.size)}
          </Typography>
        </Box>
      ) : (
        <Typography variant="body1" color="text.secondary">
          Datei hierher ziehen oder klicken
        </Typography>
      )}

      <Button
        variant="contained"
        onClick={(e) => {
          e.stopPropagation()
          handleUpload()
        }}
        disabled={!selectedFile || isLoading}
        startIcon={isLoading ? <CircularProgress size={16} color="inherit" /> : undefined}
      >
        Hochladen
      </Button>
    </Box>
  )
}
