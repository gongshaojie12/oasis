// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Right "live data panel" — population stats + recent runs + actions.
// Matches chat.html .panel.
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { ChatMessage, Sandbox, SimProgress } from '@/types/api'
import { SwarmCanvas } from './SwarmCanvas'
import { ReportSummary } from './ReportSummary'
import { useSandboxStore } from '@/stores/sandboxStore'
import { phraseFeed, descFeed } from '@/lib/feedPhrase'

interface Props {
  sandbox: Sandbox
  messages: ChatMessage[]
  liveProgress?: SimProgress | null
  onExportPdf?: () => void
  onExpandCockpit?: () => void
}

export function DataPanel({ sandbox, messages, liveProgress, onExportPdf,
                            onExpandCockpit }: Props) {
  const { t } = useTranslation()
  const feedItems = useSandboxStore((s) => s.feedItems)
  const recent = useMemo(
    () => messages.filter((m) => m.kind === 'report_card').slice(-3).reverse(),
    [messages],
  )

  const lastReport = recent[0]
  const lastMeta = (lastReport?.metadata ?? {}) as Record<string, unknown>

  const live = liveProgress && liveProgress.status === 'running'
    ? liveProgress : null
  const pct = live && live.total > 0
    ? Math.round((live.done / live.total) * 100) : 0

  return (
    <aside className="wx-panel">
      <header>
        <span>{t('panel.title')}</span>
        <span className="wx-panel-live">{t('panel.live')}</span>
      </header>

      {live && (
        <>
          <div className="wx-panel-stat">
            <div className="wx-panel-stat-label">
              {t('panel.particles_title')}
            </div>
            <SwarmCanvas count={live.total} />
          </div>
          <div className="wx-panel-stat">
            <div className="wx-panel-stat-label">{t('panel.sim_progress')}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between',
                          alignItems: 'baseline', marginBottom: 6 }}>
              <b style={{ fontSize: 22, fontWeight: 800,
                          color: 'var(--wx-accent-blue, #8B5CF6)' }}>{pct}%</b>
              <span style={{ fontSize: 12,
                             color: 'var(--wx-text-secondary)' }}>
                {live.done} / {live.total}
              </span>
            </div>
            <div style={{ height: 6, borderRadius: 4,
                          background: 'rgba(127,141,164,.18)',
                          overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`,
                            borderRadius: 4, transition: 'width .3s ease',
                            background:
                              'linear-gradient(90deg,#8B5CF6,#A78BFA)' }} />
            </div>
          </div>
          <div className="wx-panel-stat">
            <div className="wx-panel-stat-label">
              {t('panel.active_agents')}
            </div>
            <div className="wx-panel-stat-value">
              {live.done.toLocaleString()}
              <span style={{ fontSize: 12, color: 'var(--wx-text-tertiary)',
                             fontWeight: 400, marginLeft: 6 }}>
                / {live.total.toLocaleString()}
              </span>
            </div>
          </div>
          {typeof live.mean === 'number' && (
            <div className="wx-panel-stat">
              <div className="wx-panel-stat-label">
                {t('panel.running_mean')}
              </div>
              <div className="wx-panel-stat-value">
                {live.mean.toFixed(2)}
              </div>
            </div>
          )}
          {feedItems.length > 0 && (
            <div className="wx-panel-stat">
              <div className="wx-panel-stat-label">
                {t('overlay.activity_feed')}
              </div>
              {feedItems.slice(0, 4).map((it) => (
                <div key={it.id} style={{ fontSize: 12, lineHeight: 1.5,
                       color: 'var(--wx-text-secondary)', padding: '2px 0' }}>
                  <b>{descFeed(it)}</b> {phraseFeed(it, t)}
                </div>
              ))}
            </div>
          )}
          <div className="wx-panel-stat">
            <div style={{ fontSize: 12.5, color: 'var(--wx-text-secondary)' }}>
              {t('panel.sim_running')}…
            </div>
          </div>
        </>
      )}

      <div className="wx-panel-stat">
        <div className="wx-panel-stat-label">{t('sandbox.population')}</div>
        <div className="wx-panel-stat-value">
          {sandbox.population_size.toLocaleString()}
        </div>
      </div>
      <div className="wx-panel-stat">
        <div className="wx-panel-stat-label">{t('sandbox.distribution')}</div>
        <div style={{ fontSize: 13, color: 'var(--wx-text-secondary)',
                      wordBreak: 'break-all' }}>
          {sandbox.distribution_path.split('/').pop()}
        </div>
      </div>
      {lastReport && !live && (
        <ReportSummary meta={lastMeta} feedItems={feedItems} />
      )}
      <div className="wx-panel-stat">
        <div className="wx-panel-stat-label">{t('panel.recent_runs')}</div>
        {recent.length === 0 ? (
          <div style={{ fontSize: 12, color: 'var(--wx-text-tertiary)' }}>
            {t('panel.no_runs_yet')}
          </div>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0,
                       fontSize: 12.5, color: 'var(--wx-text-secondary)' }}>
            {recent.map((m) => (
              <li key={m.message_id} style={{ padding: '4px 0' }}>
                · {String((m.metadata as Record<string, unknown>)
                            .decision_kind ?? '—')}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8,
                    marginTop: 'auto' }}>
        <button
          type="button"
          className="wx-btn-ghost"
          disabled={!lastReport || !onExportPdf}
          onClick={onExportPdf}
        >
          {t('panel.export_pdf')}
        </button>
        <button
          type="button"
          className="wx-btn-primary"
          disabled={!onExpandCockpit}
          onClick={onExpandCockpit}
        >
          {t('panel.expand_cockpit')}
        </button>
      </div>
    </aside>
  )
}
