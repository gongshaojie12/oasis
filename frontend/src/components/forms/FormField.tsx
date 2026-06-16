// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import type { ReactNode } from 'react'

interface Props {
  label?: ReactNode
  hint?: ReactNode
  error?: ReactNode
  children: ReactNode
}

export function FormField({ label, hint, error, children }: Props) {
  return (
    <div style={{ marginBottom: 14 }}>
      {label && <label className="wx-label">{label}</label>}
      {children}
      {hint && (
        <div
          className="text-xs"
          style={{ color: 'var(--wx-text-tertiary)', marginTop: 4 }}
        >
          {hint}
        </div>
      )}
      {error && (
        <div
          className="text-xs"
          style={{ color: 'var(--wx-danger)', marginTop: 4 }}
        >
          {error}
        </div>
      )}
    </div>
  )
}
