// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import type { ReactNode } from 'react'

interface Props {
  label: ReactNode
  value: ReactNode
  sub?: ReactNode
  accent?: 'blue' | 'orange' | 'cyan'
}

export function StatCard({ label, value, sub, accent }: Props) {
  const accentStyle: Record<string, string> = {
    blue: 'var(--wx-grad-blue)',
    orange: 'var(--wx-grad-orange)',
    cyan: 'linear-gradient(135deg, #00B8D4, #00D971)',
  }
  return (
    <div className="wx-stat-card">
      <div className="wx-stat-label">{label}</div>
      <div
        className="wx-stat-value"
        style={
          accent
            ? {
                background: accentStyle[accent],
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }
            : undefined
        }
      >
        {value}
      </div>
      {sub && <div className="wx-stat-sub">{sub}</div>}
    </div>
  )
}
