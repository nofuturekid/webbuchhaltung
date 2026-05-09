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
  // Intl outputs a non-breaking space (U+00A0) before the currency symbol;
  // normalize to a regular space for consistent string comparison.
  return euroFormatter.format(cents / 100).replace('\u00a0', ' ')
}

export function formatDate(dateStr: string): string {
  return dateFormatter.format(new Date(dateStr + 'T00:00:00'))
}

export function formatAccountNumber(num: string): string {
  return num.padStart(4, '0')
}

export function euroToCents(euro: string): number {
  return Math.round(parseFloat(euro.replace(',', '.')) * 100)
}

export function centsToEuro(cents: number): string {
  return (cents / 100).toFixed(2)
}
