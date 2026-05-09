const euroFormatter = new Intl.NumberFormat('de-DE', {
  style: 'currency',
  currency: 'EUR',
})

const dateFormatter = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

export function formatEuro(cents: number): string {
  return euroFormatter.format(cents / 100).replace('\u00a0', ' ')
}

export function formatDate(dateStr: string): string {
  return dateFormatter.format(new Date(dateStr + 'T00:00:00'))
}

export function formatAccountNumber(num: string): string {
  return num.padStart(4, '0')
}

export function euroToCents(euro: string): number {
  const normalized = euro.replace(',', '.')
  const result = Math.round(parseFloat(normalized) * 100)
  if (isNaN(result)) throw new Error(`Invalid amount: "${euro}"`)
  return result
}

export function centsToEuro(cents: number): string {
  return (cents / 100).toFixed(2)
}
