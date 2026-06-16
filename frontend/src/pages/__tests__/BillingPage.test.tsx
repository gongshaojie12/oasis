// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it } from 'vitest'
import { formatCostUnits } from '@/pages/billing/BillingPage'

describe('formatCostUnits', () => {
  it('formats positive integers with locale grouping (zh)', () => {
    expect(formatCostUnits(1234, 'zh')).toBe('1,234')
  })

  it('keeps sign for negative deltas', () => {
    expect(formatCostUnits(-2500, 'en')).toBe('-2,500')
  })

  it('handles zero', () => {
    expect(formatCostUnits(0, 'zh')).toBe('0')
  })

  it('handles large numbers', () => {
    expect(formatCostUnits(1_234_567, 'en')).toBe('1,234,567')
  })
})
