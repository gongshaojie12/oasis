// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage right data panel.
// - Anonymous: hidden behind a "登录后查看" placeholder.
// - Authed, no sandbox: prompt to create/select one.
// - Authed, sandbox selected: shows real sandbox info; once a report_card
//   message exists, renders real decision_kind / n_valid / mean from its metadata.
import { useTranslation } from 'react-i18next'
import type { ChatMessage, Sandbox } from '@/types/api'

interface Props {
  authed: boolean
  activeSandbox: Sandbox | null
  messages: ChatMessage[]
}

interface ReportMeta {
  decision_kind?: string
  n_valid?: number
  n_total?: number
  mean?: number | null
}

export function LandingDataPanel(p: Props) {
  const { t } = useTranslation()

  if (!p.authed) {
    return (
      <aside className="wx-panel" aria-label="WANXIANG live data panel">
        <header>
          <span>{t('landing.panel_title')}</span>
        </header>
        <div className="wx-panel-empty">
          <p
            style={{
              fontSize: 12.5,
              color: 'var(--wx-text-secondary)',
              textAlign: 'center',
              padding: '32px 16px',
              lineHeight: 1.6,
            }}
          >
            {t('landing.panel_anon_msg')}
          </p>
        </div>
      </aside>
    )
  }

  if (!p.activeSandbox) {
    return (
      <aside className="wx-panel" aria-label="WANXIANG live data panel">
        <header>
          <span>{t('landing.panel_title')}</span>
        </header>
        <div className="wx-panel-empty">
          <p
            style={{
              fontSize: 12.5,
              color: 'var(--wx-text-secondary)',
              textAlign: 'center',
              padding: '32px 16px',
              lineHeight: 1.6,
            }}
          >
            {t('landing.panel_no_sandbox')}
          </p>
        </div>
      </aside>
    )
  }

  // Look for most recent report_card message
  const lastReport = [...p.messages].reverse().find((m) => m.kind === 'report_card')
  const meta: ReportMeta = (lastReport?.metadata as ReportMeta) || {}

  return (
    <aside className="wx-panel" aria-label="WANXIANG live data panel">
      <header>
        <span>{t('landing.panel_title')}</span>
        {lastReport && <span className="wx-panel-live">LIVE</span>}
      </header>

      <div className="wx-panel-stat">
        <div className="wx-panel-stat-label">{t('landing.panel_sandbox')}</div>
        <div
          className="wx-panel-stat-value"
          style={{ fontSize: 15, fontWeight: 500 }}
        >
          {p.activeSandbox.emoji} {p.activeSandbox.name}
        </div>
      </div>

      <div className="wx-panel-stat">
        <div className="wx-panel-stat-label">{t('landing.panel_population')}</div>
        <div className="wx-panel-stat-value">
          {p.activeSandbox.population_size.toLocaleString()}
        </div>
      </div>

      {!lastReport ? (
        <div className="wx-panel-empty" style={{ minHeight: 120 }}>
          <p
            style={{
              fontSize: 12,
              color: 'var(--wx-text-secondary)',
              textAlign: 'center',
              padding: '20px 16px',
              lineHeight: 1.6,
            }}
          >
            {t('landing.panel_no_runs')}
          </p>
        </div>
      ) : (
        <>
          <div className="wx-panel-stat">
            <div className="wx-panel-stat-label">{t('landing.panel_decision_kind')}</div>
            <div
              className="wx-panel-stat-value"
              style={{ fontSize: 15, fontWeight: 500 }}
            >
              {meta.decision_kind || '-'}
            </div>
          </div>
          <div className="wx-panel-stat">
            <div className="wx-panel-stat-label">{t('landing.panel_valid_samples')}</div>
            <div className="wx-panel-stat-value">
              {meta.n_valid ?? '-'}
              {meta.n_total != null && (
                <span
                  style={{
                    fontSize: 12,
                    color: 'var(--wx-text-tertiary)',
                    fontWeight: 400,
                    marginLeft: 6,
                  }}
                >
                  / {meta.n_total}
                </span>
              )}
            </div>
          </div>
          {meta.mean !== undefined && meta.mean !== null && (
            <div className="wx-panel-stat">
              <div className="wx-panel-stat-label">{t('landing.panel_mean')}</div>
              <div className="wx-panel-stat-value">{Number(meta.mean).toFixed(2)}</div>
            </div>
          )}
        </>
      )}
    </aside>
  )
}
