import { describe, test, expect } from 'vitest'

describe('JWT Utilities', () => {
  test('signToken returns a valid JWT string', async () => {
    const { signToken } = await import('../../server/utils/jwt')
    const token = await signToken({ userId: 'u1', enterpriseId: 'e1', role: 'admin' })
    expect(token).toBeTruthy()
    expect(typeof token).toBe('string')
    expect(token.split('.')).toHaveLength(3)
  })

  test('verifyToken decodes a valid token', async () => {
    const { signToken, verifyToken } = await import('../../server/utils/jwt')
    const token = await signToken({ userId: 'u1', enterpriseId: 'e1', role: 'admin' })
    const payload = await verifyToken(token)
    expect(payload.userId).toBe('u1')
    expect(payload.enterpriseId).toBe('e1')
    expect(payload.role).toBe('admin')
  })

  test('verifyToken throws on invalid token', async () => {
    const { verifyToken } = await import('../../server/utils/jwt')
    await expect(verifyToken('invalid.token.here')).rejects.toThrow()
  })

  test('signRefreshToken creates a longer-lived token', async () => {
    const { signRefreshToken, verifyRefreshToken } = await import('../../server/utils/jwt')
    const token = await signRefreshToken({ userId: 'u1', enterpriseId: 'e1', role: 'user' })
    const payload = await verifyRefreshToken(token)
    expect(payload.userId).toBe('u1')
  })
})
