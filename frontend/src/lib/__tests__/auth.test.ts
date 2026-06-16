// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it } from 'vitest'
import { clearTokens, getTokens, isAuthenticated, setTokens } from '../auth'

describe('lib/auth', () => {
  it('round-trips tokens through localStorage', () => {
    expect(getTokens()).toEqual({ access: null, refresh: null })
    setTokens({ access: 'a-tok', refresh: 'r-tok' })
    expect(getTokens()).toEqual({ access: 'a-tok', refresh: 'r-tok' })
    expect(isAuthenticated()).toBe(true)
  })

  it('clears tokens', () => {
    setTokens({ access: 'a', refresh: 'r' })
    clearTokens()
    expect(getTokens()).toEqual({ access: null, refresh: null })
    expect(isAuthenticated()).toBe(false)
  })
})
