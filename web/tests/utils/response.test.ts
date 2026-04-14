import { describe, test, expect } from 'vitest'

describe('Response Utilities', () => {
  test('success returns code 0 with data', async () => {
    const { success } = await import('../../server/utils/response')
    const res = success({ name: 'test' })
    expect(res.code).toBe(0)
    expect(res.data.name).toBe('test')
    expect(res.message).toBe('ok')
  })

  test('error returns error code and message', async () => {
    const { error } = await import('../../server/utils/response')
    const res = error(40001, '验证码已过期')
    expect(res.code).toBe(40001)
    expect(res.data).toBeNull()
    expect(res.message).toBe('验证码已过期')
  })
})
