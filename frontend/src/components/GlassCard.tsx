// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
}

export function GlassCard({ children, className = '' }: Props) {
  return <div className={`wx-glass p-6 ${className}`}>{children}</div>
}
