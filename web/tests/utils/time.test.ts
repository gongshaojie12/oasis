import { describe, test, expect } from 'vitest'

describe('Time Utilities', () => {
  test('now returns ISO string', async () => {
    const { now } = await import('../../server/utils/time')
    const timestamp = now()
    expect(typeof timestamp).toBe('string')
    expect(new Date(timestamp).toISOString()).toBe(timestamp)
  })

  test('addMinutes returns future timestamp', async () => {
    const { addMinutes } = await import('../../server/utils/time')
    const future = addMinutes(5)
    const futureDate = new Date(future)
    const nowDate = new Date()
    expect(futureDate > nowDate).toBe(true)
  })

  test('isExpired returns true for past dates', async () => {
    const { isExpired } = await import('../../server/utils/time')
    const pastDate = new Date(Date.now() - 1000).toISOString()
    expect(isExpired(pastDate)).toBe(true)
  })

  test('isExpired returns false for future dates', async () => {
    const { isExpired } = await import('../../server/utils/time')
    const futureDate = new Date(Date.now() + 10000).toISOString()
    expect(isExpired(futureDate)).toBe(false)
  })
})
