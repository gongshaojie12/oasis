import { describe, test, expect } from 'vitest'

describe('ID Utilities', () => {
  test('generateId returns a string of default length 21', async () => {
    const { generateId } = await import('../../server/utils/id')
    const id = generateId()
    expect(typeof id).toBe('string')
    expect(id.length).toBe(21)
  })

  test('generateId accepts custom length', async () => {
    const { generateId } = await import('../../server/utils/id')
    const id = generateId(10)
    expect(id.length).toBe(10)
  })

  test('generateSmsCode returns 6-digit string', async () => {
    const { generateSmsCode } = await import('../../server/utils/id')
    const code = generateSmsCode()
    expect(typeof code).toBe('string')
    expect(code.length).toBe(6)
    expect(parseInt(code)).toBeGreaterThanOrEqual(100000)
    expect(parseInt(code)).toBeLessThanOrEqual(999999)
  })
})
