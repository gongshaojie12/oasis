// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import type { ReactNode } from 'react'
import { BrandLogo } from './BrandLogo'
import { I18nToggle } from './I18nToggle'
import { ThemeToggle } from './ThemeToggle'

interface Props {
  children: ReactNode
}

export function PageShell({ children }: Props) {
  return (
    <div className="min-h-screen grid place-items-center px-4 py-8">
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <ThemeToggle />
        <I18nToggle />
      </div>
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8"><BrandLogo size="lg" /></div>
        {children}
      </div>
    </div>
  )
}
