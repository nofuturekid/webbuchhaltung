import { describe, expect, it } from 'vitest'

function computeLineItem(qty: number, priceCents: number, vatRate: number) {
  const net = Math.round(qty * priceCents)
  const vat = Math.round(net * vatRate)
  return { net, vat, gross: net + vat }
}

describe('line item calculations', () => {
  it('single item 19%', () => {
    const { net, vat, gross } = computeLineItem(2, 5000, 0.19)
    expect(net).toBe(10000)
    expect(vat).toBe(1900)
    expect(gross).toBe(11900)
  })

  it('zero vat rate', () => {
    const { vat, gross } = computeLineItem(1, 10000, 0.0)
    expect(vat).toBe(0)
    expect(gross).toBe(10000)
  })

  it('7% reduced rate', () => {
    const { net, vat } = computeLineItem(1, 10000, 0.07)
    expect(net).toBe(10000)
    expect(vat).toBe(700)
  })

  it('decimal quantity', () => {
    const { net } = computeLineItem(1.5, 4000, 0.19)
    expect(net).toBe(6000)
  })
})
