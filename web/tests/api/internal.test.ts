import { describe, it, expect } from 'vitest'

// These tests require the dev server to be running
// Run: npm run dev (in another terminal)
// Then: npx vitest run tests/api/internal.test.ts

const BASE = 'http://localhost:3000'
const INTERNAL_KEY = 'dev-internal-key'

describe('Internal Callback Endpoints', () => {
  it('rejects progress without internal key', async () => {
    const res = await fetch(`${BASE}/api/internal/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'test', current_step: 1, total_steps: 5, progress: 0.2 }),
    })
    expect(res.status).toBe(401)
  })

  it('rejects complete without internal key', async () => {
    const res = await fetch(`${BASE}/api/internal/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'test', result: {} }),
    })
    expect(res.status).toBe(401)
  })

  it('rejects error without internal key', async () => {
    const res = await fetch(`${BASE}/api/internal/error`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'test', error: 'boom' }),
    })
    expect(res.status).toBe(401)
  })

  it('accepts progress with valid internal key', async () => {
    const res = await fetch(`${BASE}/api/internal/progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Key': INTERNAL_KEY,
      },
      body: JSON.stringify({ task_id: 'nonexistent', current_step: 1, total_steps: 5, progress: 0.2 }),
    })
    expect(res.status).toBe(200)
  })
})
