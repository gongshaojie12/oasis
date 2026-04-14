import { describe, test, expect } from 'vitest'

// Test the auth flow by calling the API endpoints directly
// These tests require the dev server to be running
// Run: npm run dev (in another terminal)
// Then: npx vitest run tests/e2e/auth-flow.test.ts

const BASE_URL = 'http://localhost:3000'

// Generate a random valid Chinese mobile number to avoid SMS rate limiting
function randomPhone(): string {
  const prefixes = ['138', '139', '150', '151', '152', '158', '159', '186', '187']
  const prefix = prefixes[Math.floor(Math.random() * prefixes.length)]
  const suffix = String(Math.floor(Math.random() * 100000000)).padStart(8, '0')
  return prefix + suffix
}

describe('Auth Flow E2E', () => {
  test('health check returns ok', async () => {
    const res = await fetch(`${BASE_URL}/api/health`)
    const data = await res.json()
    expect(data.code).toBe(0)
    expect(data.data.status).toBe('healthy')
  })

  test('SMS send returns success for valid phone', async () => {
    const phone = randomPhone()
    const res = await fetch(`${BASE_URL}/api/auth/sms.send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    })
    const data = await res.json()
    expect(data.code).toBe(0)
  })

  test('SMS send rejects invalid phone', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/sms.send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '123' }),
    })
    const data = await res.json()
    expect(data.code).not.toBe(0)
  })

  test('login rejects non-existent user', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '13800138001', code: '000000' }),
    })
    const data = await res.json()
    expect(data.code).not.toBe(0)
  })

  test('me endpoint rejects unauthenticated request', async () => {
    const res = await fetch(`${BASE_URL}/api/auth/me`)
    expect(res.status).toBe(401)
  })
})
