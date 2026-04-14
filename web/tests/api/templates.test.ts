import { describe, it, expect } from 'vitest'

const BASE = 'http://localhost:3000'

describe('Templates API', () => {
  it('agent templates list requires auth', async () => {
    const res = await fetch(`${BASE}/api/templates/agents`)
    expect(res.status).toBe(401)
  })

  it('agent template create requires auth', async () => {
    const res = await fetch(`${BASE}/api/templates/agents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'test', platform: 'twitter', profileConfig: {} }),
    })
    expect(res.status).toBe(401)
  })

  it('simulation templates list requires auth', async () => {
    const res = await fetch(`${BASE}/api/templates/simulations`)
    expect(res.status).toBe(401)
  })

  it('simulation template create requires auth', async () => {
    const res = await fetch(`${BASE}/api/templates/simulations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'test', type: 'marketing_sim', platform: 'twitter', config: {} }),
    })
    expect(res.status).toBe(401)
  })
})
