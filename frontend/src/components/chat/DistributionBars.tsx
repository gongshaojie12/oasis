// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// 决策分布柱状图(纯 CSS,无图表库) —— 渲染后端 histogram/breakdown。
// 数值 kind: [{label, count}] 评分分布;choose: [{option, share, count}]。
interface Bar {
  label: string
  count: number
  share?: number
}

interface Props {
  bars: Bar[]
  accent?: string
}

export function DistributionBars({ bars, accent = '#8B5CF6' }: Props) {
  if (!bars || bars.length === 0) return null
  const max = Math.max(1, ...bars.map((b) => b.count))
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {bars.map((b, i) => {
        const w = Math.round((b.count / max) * 100)
        const pctTxt = b.share != null
          ? `${(b.share * 100).toFixed(0)}%`
          : String(b.count)
        return (
          <div key={`${b.label}-${i}`}
               style={{ display: 'flex', alignItems: 'center', gap: 8,
                        fontSize: 11.5 }}>
            <span style={{ width: 56, flexShrink: 0, textAlign: 'right',
                           color: 'var(--wx-text-tertiary)',
                           whiteSpace: 'nowrap', overflow: 'hidden',
                           textOverflow: 'ellipsis' }}>{b.label}</span>
            <div style={{ flex: 1, height: 10, borderRadius: 3,
                          background: 'rgba(127,141,164,.14)',
                          overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${w}%`, borderRadius: 3,
                            background: accent, minWidth: b.count > 0 ? 2 : 0,
                            transition: 'width .3s ease' }} />
            </div>
            <span style={{ width: 34, flexShrink: 0,
                           color: 'var(--wx-text-secondary)',
                           fontVariantNumeric: 'tabular-nums' }}>
              {pctTxt}
            </span>
          </div>
        )
      })}
    </div>
  )
}
