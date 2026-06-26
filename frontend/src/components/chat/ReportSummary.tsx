// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// 模拟结束后的丰富报告摘要(数据面板用)。
// 渲染:均值/中位数、置信区间 p25-p75、范围 min-max、错误率、评分分布柱状图、
// choose 份额分布,以及保留的决策动态 feed(末 N 条真实决策)。
import { useTranslation } from 'react-i18next'
import type { FeedItem } from '@/types/api'
import { DistributionBars } from './DistributionBars'
import { phraseFeed, descFeed } from '@/lib/feedPhrase'

type Meta = Record<string, unknown>

interface Bar { label: string; count: number; share?: number }

interface Props {
  meta: Meta
  feedItems?: FeedItem[]
}

function num(v: unknown): number | null {
  return typeof v === 'number' && !Number.isNaN(v) ? v : null
}

export function ReportSummary({ meta, feedItems = [] }: Props) {
  const { t } = useTranslation()
  const kind = String(meta.decision_kind ?? '—')
  const isChoose = kind === 'choose'
  const mean = num(meta.mean)
  const median = num(meta.median)
  const p25 = num(meta.p25)
  const p75 = num(meta.p75)
  const lo = num(meta.min)
  const hi = num(meta.max)
  const errRate = num(meta.error_rate)
  const nValid = num(meta.n_valid)
  const nTotal = num(meta.n_total)

  const histogram = (meta.histogram as Bar[] | undefined) || undefined
  const breakdown = (meta.breakdown as Array<{
    option: string; share: number; count: number }> | undefined) || undefined
  // 注意:数值 kind 时后端 breakdown 是空数组 [](非 undefined),不能用 ??
  // 兜底,否则空数组会盖住 histogram。仅当 breakdown 非空才用它。
  const chooseBars: Bar[] | undefined = breakdown && breakdown.length > 0
    ? breakdown.map((b) => ({ label: b.option, count: b.count,
                              share: b.share }))
    : undefined
  const distBars: Bar[] | undefined = chooseBars
    ?? (histogram && histogram.length > 0 ? histogram : undefined)

  return (
    <>
      <div className="wx-panel-stat">
        <div className="wx-panel-stat-label">{t('panel.last_run')}</div>
        <div style={{ fontSize: 13, color: 'var(--wx-text-secondary)' }}>
          {kind}
          {nValid != null && (
            <> · n = {nValid}{nTotal != null && nTotal !== nValid
              ? ` / ${nTotal}` : ''}</>
          )}
        </div>
      </div>

      {/* 数值 kind:关键统计 */}
      {!isChoose && mean != null && (
        <div className="wx-panel-stat">
          <div className="wx-panel-stat-label">{t('chat.report_mean')}</div>
          <div className="wx-panel-stat-value">{mean.toFixed(2)}</div>
          <div style={{ fontSize: 12, color: 'var(--wx-text-secondary)',
                        marginTop: 6, display: 'flex',
                        flexDirection: 'column', gap: 2 }}>
            {median != null && (
              <span>{t('panel.median')}: <b>{median.toFixed(2)}</b></span>
            )}
            {p25 != null && p75 != null && (
              <span>{t('panel.ci_band')}: <b>{p25.toFixed(2)} – {p75.toFixed(2)}</b></span>
            )}
            {lo != null && hi != null && (
              <span>{t('panel.range')}: <b>{lo.toFixed(2)} – {hi.toFixed(2)}</b></span>
            )}
          </div>
        </div>
      )}

      {/* choose:首选 + 份额 */}
      {isChoose && meta.top_choice != null && (
        <div className="wx-panel-stat">
          <div className="wx-panel-stat-label">{t('panel.top_choice')}</div>
          <div className="wx-panel-stat-value" style={{ fontSize: 16 }}>
            {String(meta.top_choice)}
            {num(meta.top_share) != null && (
              <span style={{ fontSize: 12, fontWeight: 400,
                             color: 'var(--wx-text-tertiary)', marginLeft: 6 }}>
                {((meta.top_share as number) * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      )}

      {/* 分布柱状图 */}
      {distBars && (
        <div className="wx-panel-stat">
          <div className="wx-panel-stat-label">{t('panel.distribution')}</div>
          <DistributionBars bars={distBars} />
        </div>
      )}

      {/* 错误率 */}
      {errRate != null && (
        <div className="wx-panel-stat">
          <div className="wx-panel-stat-label">{t('panel.error_rate')}</div>
          <div className="wx-panel-stat-value" style={{ fontSize: 16 }}>
            {(errRate * 100).toFixed(1)}%
          </div>
        </div>
      )}

      {/* 保留的决策动态 feed(末 N 条真实决策) */}
      {feedItems.length > 0 && (
        <div className="wx-panel-stat">
          <div className="wx-panel-stat-label">{t('overlay.activity_feed')}</div>
          {feedItems.slice(0, 6).map((it) => (
            <div key={it.id} style={{ fontSize: 12, lineHeight: 1.5,
                   color: 'var(--wx-text-secondary)', padding: '2px 0' }}>
              <b>{descFeed(it)}</b> {phraseFeed(it, t)}
            </div>
          ))}
        </div>
      )}
    </>
  )
}
