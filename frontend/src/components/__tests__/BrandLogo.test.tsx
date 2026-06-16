// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrandLogo } from '../BrandLogo'
import { switchLang } from '@/lib/i18n'
import { useBrandStore } from '@/stores/brandStore'

describe('BrandLogo', () => {
  it('renders zh defaults when no brand is loaded', () => {
    useBrandStore.setState({ brand: null })
    switchLang('zh')
    render(<BrandLogo />)
    expect(screen.getByText('万象')).toBeInTheDocument()
    expect(screen.getByText('象')).toBeInTheDocument()
  })

  it('renders en defaults when switched to English', () => {
    useBrandStore.setState({ brand: null })
    switchLang('en')
    render(<BrandLogo />)
    expect(screen.getByText('WANXIANG')).toBeInTheDocument()
    expect(screen.getByText('W')).toBeInTheDocument()
  })

  it('uses brand store values when present', () => {
    useBrandStore.setState({
      brand: {
        name: { zh: '万象X', en: 'WANXIANG X' },
        short: 'WX',
        avatar: { zh: '象', en: 'W' },
        tagline: { zh: '首席模拟官', en: 'CSO' },
      },
    })
    switchLang('en')
    render(<BrandLogo />)
    expect(screen.getByText('WANXIANG X')).toBeInTheDocument()
    expect(screen.getByText('CSO')).toBeInTheDocument()
  })
})
