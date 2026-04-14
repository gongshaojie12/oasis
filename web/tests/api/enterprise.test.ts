import { describe, it, expect } from 'vitest'

const BASE = 'http://localhost:3000'

describe('Enterprise API', () => {
  it('current enterprise requires auth', async () => {
    const res = await fetch(`${BASE}/api/enterprises/current`)
    expect(res.status).toBe(401)
  })

  it('update enterprise requires auth', async () => {
    const res = await fetch(`${BASE}/api/enterprises/current`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'test' }),
    })
    expect(res.status).toBe(401)
  })

  it('usage stats requires auth', async () => {
    const res = await fetch(`${BASE}/api/enterprises/usage`)
    expect(res.status).toBe(401)
  })

  it('logs requires auth', async () => {
    const res = await fetch(`${BASE}/api/enterprises/logs`)
    expect(res.status).toBe(401)
  })

  it('platforms list requires auth', async () => {
    const res = await fetch(`${BASE}/api/platforms`)
    expect(res.status).toBe(401)
  })

  it('LLM providers list requires auth', async () => {
    const res = await fetch(`${BASE}/api/llm/providers`)
    expect(res.status).toBe(401)
  })

  it('LLM key save requires auth', async () => {
    const res = await fetch(`${BASE}/api/llm/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'deepseek', apiKey: 'sk-test' }),
    })
    expect(res.status).toBe(401)
  })

  it('reports list requires auth', async () => {
    const res = await fetch(`${BASE}/api/reports`)
    expect(res.status).toBe(401)
  })
})
