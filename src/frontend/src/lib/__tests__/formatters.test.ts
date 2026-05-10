import { formatEuro, formatDate, formatAccountNumber, euroToCents, centsToEuro } from '../formatters'

describe('formatEuro', () => {
  it('formats 119000 cents as 1.190,00 €', () => {
    expect(formatEuro(119000)).toBe('1.190,00 €')
  })
  it('formats 100 cents as 1,00 €', () => {
    expect(formatEuro(100)).toBe('1,00 €')
  })
  it('formats negative cents', () => {
    expect(formatEuro(-5000)).toBe('-50,00 €')
  })
})

describe('formatDate', () => {
  it('formats ISO date as DD.MM.YYYY', () => {
    expect(formatDate('2026-01-15')).toBe('15.01.2026')
  })
  it('formats year-end date', () => {
    expect(formatDate('2026-12-31')).toBe('31.12.2026')
  })
})

describe('formatAccountNumber', () => {
  it('pads 4-digit number unchanged', () => {
    expect(formatAccountNumber('1200')).toBe('1200')
  })
  it('pads 3-digit number with leading zero', () => {
    expect(formatAccountNumber('800')).toBe('0800')
  })
})

describe('euroToCents', () => {
  it('converts 1190.00 to 119000', () => {
    expect(euroToCents('1190.00')).toBe(119000)
  })
  it('converts comma decimal 1190,00 to 119000', () => {
    expect(euroToCents('1190,00')).toBe(119000)
  })
  it('rounds correctly', () => {
    expect(euroToCents('0.005')).toBe(1)
  })
  it('throws on non-numeric input', () => {
    expect(() => euroToCents('abc')).toThrow()
  })
  it('handles integer input', () => {
    expect(euroToCents('100')).toBe(10000)
  })
})

describe('centsToEuro', () => {
  it('converts 119000 to "1190.00"', () => {
    expect(centsToEuro(119000)).toBe('1190.00')
  })
  it('handles zero', () => {
    expect(centsToEuro(0)).toBe('0.00')
  })
  it('handles negative cents', () => {
    expect(centsToEuro(-5000)).toBe('-50.00')
  })
})
