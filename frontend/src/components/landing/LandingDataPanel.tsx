// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage right data panel.
// - Anonymous: hidden behind a "登录后查看" placeholder.
// - Authed, no sandbox: prompt to create/select one.
// - Authed, sandbox selected: shows real sandbox info; once a report_card
//   message exists, renders real decision_kind / n_valid / mean from its metadata.
import { useTranslation } from 'react-i18next'
import { Activity, ChevronLeft, ChevronRight, Maximize2 } from 'lucide-react'
import type { ChatMessage, Sandbox, SimProgress } from '@/types/api'
import { SwarmCanvas } from '@/components/chat/SwarmCanvas'
import { ReportSummary } from '@/components/chat/ReportSummary'
import { useSandboxStore } from '@/stores/sandboxStore'
import { phraseFeed, descFeed } from '@/lib/feedPhrase'

interface Props {
  authed: boolean
  activeSandbox: Sandbox | null
  messages: ChatMessage[]
  liveProgress?: SimProgress | null
  collapsed: boolean
  onToggleCollapse: () => void
  onExpandCockpit?: () => void
}

function PanelCollapseToggle({ collapsed, onClick }: {
  collapsed: boolean; onClick: () => void
}) {
  // Right panel: arrow points RIGHT when expanded (collapse), LEFT when collapsed (expand)
  const Arrow = collapsed ? ChevronLeft : ChevronRight
  return (
    <button
      type="button"
      className="wx-collapse-btn"
      onClick={onClick}
      title={collapsed ? '展开 / Expand' : '收起 / Collapse'}
      aria-label={collapsed ? 'Expand panel' : 'Collapse panel'}
    >
      <Arrow size={14} />
    </button>
  )
}


export function LandingDataPanel(p: Props) {
  const { t } = useTranslation()
  const feedItems = useSandboxStore((s) => s.feedItems)

  // Collapsed mode: narrow strip with activity icon + expand button
  if (p.collapsed) {
    return (
      <aside className="wx-panel collapsed" aria-label="Data panel (collapsed)">
        <div className="wx-panel-collapsed-inner">
          <PanelCollapseToggle collapsed={true} onClick={p.onToggleCollapse} />
          <div className="wx-collapsed-icon" title={t('landing.panel_title')}>
            <Activity size={18} />
          </div>
        </div>
      </aside>
    )
  }

  if (!p.authed) {
    return (
      <aside className="wx-panel" aria-label="WANXIANG live data panel">
        <header>
          <PanelCollapseToggle collapsed={false} onClick={p.onToggleCollapse} />
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
          <PanelCollapseToggle collapsed={false} onClick={p.onToggleCollapse} />
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

  const live = p.liveProgress && p.liveProgress.status === 'running'
    ? p.liveProgress : null
  const pct = live && live.total > 0
    ? Math.round((live.done / live.total) * 100) : 0

  return (
    <aside className="wx-panel" aria-label="WANXIANG live data panel">
      <header>
        <PanelCollapseToggle collapsed={false} onClick={p.onToggleCollapse} />
        <span>{t('landing.panel_title')}</span>
        {(lastReport || live) && <span className="wx-panel-live">LIVE</span>}
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
              <span style={{ fontSize: 12, color: 'var(--wx-text-secondary)' }}>
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
          {typeof live.mean === 'number' && (
            <div className="wx-panel-stat">
              <div className="wx-panel-stat-label">
                {t('panel.running_mean')}
              </div>
              <div className="wx-panel-stat-value">{live.mean.toFixed(2)}</div>
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
            <div style={{ display: 'flex', justifyContent: 'space-between',
                          alignItems: 'center' }}>
              <span style={{ fontSize: 12.5,
                             color: 'var(--wx-text-secondary)' }}>
                {t('panel.sim_running')}…
              </span>
              {p.onExpandCockpit && (
                <button type="button" className="wx-link"
                        style={{ display: 'flex', alignItems: 'center',
                                 gap: 4, fontSize: 12 }}
                        onClick={p.onExpandCockpit}>
                  <Maximize2 size={13} /> {t('panel.expand_cockpit')}
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {live ? null : !lastReport ? (
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
        <ReportSummary
          meta={(lastReport?.metadata as Record<string, unknown>) || {}}
          feedItems={feedItems}
        />
      )}
    </aside>
  )
}
