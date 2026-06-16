// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Right "live data panel" — population stats + recent runs + actions.
// Matches chat.html .panel.
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { ChatMessage, Sandbox } from '@/types/api'

interface Props {
  sandbox: Sandbox
  messages: ChatMessage[]
  onExportPdf?: () => void
  onExpandCockpit?: () => void
}

export function DataPanel({ sandbox, messages, onExportPdf,
                            onExpandCockpit }: Props) {
  const { t } = useTranslation()
  const recent = useMemo(
    () => messages.filter((m) => m.kind === 'report_card').slice(-3).reverse(),
    [messages],
  )

  const lastReport = recent[0]
  const lastMeta = (lastReport?.metadata ?? {}) as Record<string, unknown>

  return (
    <aside className="wx-panel">
      <header>
        <span>{t('panel.title')}</span>
        <span className="wx-panel-live">{t('panel.live')}</span>
      </header>
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
      {lastReport && (
        <div className="wx-panel-stat">
          <div className="wx-panel-stat-label">{t('panel.last_run')}</div>
          <div style={{ fontSize: 13, color: 'var(--wx-text-secondary)' }}>
            {String(lastMeta.decision_kind ?? '—')}
            {typeof lastMeta.mean === 'number' && (
              <> · {t('chat.report_mean')}: <b>{(lastMeta.mean as number).toFixed(2)}</b></>
            )}
            {typeof lastMeta.n_valid === 'number' && (
              <> · n = {lastMeta.n_valid as number}</>
            )}
          </div>
        </div>
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
