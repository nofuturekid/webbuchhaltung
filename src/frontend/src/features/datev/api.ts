import api from '../../lib/api'

export async function downloadDatevExport(dateFrom: string, dateTo: string): Promise<void> {
  const response = await api.post(
    '/datev/export',
    { date_from: dateFrom, date_to: dateTo },
    { responseType: 'blob' }
  )
  const url = URL.createObjectURL(new Blob([response.data as BlobPart]))
  const link = document.createElement('a')
  link.href = url
  link.download = `EXTF_${dateFrom}_${dateTo}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
