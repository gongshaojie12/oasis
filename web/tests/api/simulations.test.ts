import { describe, it, expect } from 'vitest'

const BASE = 'http://localhost:3000'

describe('Simulations API', () => {
  it('lists simulations requires auth', async () => {
    const res = await fetch(`${BASE}/api/simulations`)
    expect(res.status).toBe(401)
  })

  it('create simulation requires auth', async () => {
    const res = await fetch(`${BASE}/api/simulations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'test', type: 'marketing_sim', platform: 'twitter' }),
    })
    expect(res.status).toBe(401)
  })

  it('get simulation detail requires auth', async () => {
    const res = await fetch(`${BASE}/api/simulations/nonexistent`)
    expect(res.status).toBe(401)
  })

  it('cancel simulation requires auth', async () => {
    const res = await fetch(`${BASE}/api/simulations/nonexistent/cancel`, { method: 'POST' })
    expect(res.status).toBe(401)
  })

  it('retry simulation requires auth', async () => {
    const res = await fetch(`${BASE}/api/simulations/nonexistent/retry`, { method: 'POST' })
    expect(res.status).toBe(401)
  })
})
