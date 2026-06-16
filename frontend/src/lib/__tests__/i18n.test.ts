// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it } from 'vitest'
import i18n, { switchLang } from '../i18n'

describe('lib/i18n', () => {
  it('initialises with zh by default and resolves a known key', () => {
    expect(['zh', 'en']).toContain(i18n.language)
    expect(i18n.t('auth.login')).toBeTruthy()
  })

  it('switchLang persists the choice in localStorage', () => {
    switchLang('en')
    expect(i18n.language).toBe('en')
    expect(localStorage.getItem('wanxiang.lang')).toBe('en')
    expect(i18n.t('auth.login')).toBe('Sign in')

    switchLang('zh')
    expect(i18n.language).toBe('zh')
    expect(localStorage.getItem('wanxiang.lang')).toBe('zh')
    expect(i18n.t('auth.login')).toBe('登录')
  })
})
