// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage center column — chat header + pre-filled mock conversation +
// inline simulation status + report artifact card. Visual port of chat.html
// .chat-top / .msgs / .sim-status / .artifact.
import { useTranslation } from 'react-i18next'

interface Props {
  onRunRealSim: () => void
}

export function MockChat({ onRunRealSim }: Props) {
  const { t } = useTranslation()

  return (
    <>
      {/* Chat header (port of chat.html .chat-top) */}
      <div className="wx-chat-top">
        <div className="wx-ct-ava" aria-hidden="true">🧠</div>
        <div className="wx-ct-name">
          <b>
            {t('landing.officer_name')}
            <span className="wx-ct-badge">{t('landing.officer_online')}</span>
          </b>
          <small>{t('landing.officer_subtitle')}</small>
        </div>
        <div style={{ flex: 1 }} />
        <button
          type="button"
          id="wx-run-real-sim"
          onClick={onRunRealSim}
          style={{
            padding: '8px 14px',
            background: 'linear-gradient(135deg,#FF6B3D,#F5A623)',
            color: '#fff',
            border: 'none',
            borderRadius: 10,
            cursor: 'pointer',
            fontSize: 13,
            font: 'inherit',
            fontWeight: 600,
          }}
        >
          {t('landing.run_real_sim')}
        </button>
      </div>

      {/* Messages stream */}
      <div className="wx-msgs">
        <div className="wx-msg-wrap">
          {/* User message */}
          <div className="wx-msg">
            <div className="wx-m-av u" aria-hidden="true">
              {t('landing.user_initial')}
            </div>
            <div className="wx-m-body">
              <div className="wx-m-name">{t('landing.header_user')}</div>
              <div className="wx-m-text">{t('landing.user_msg_intro')}</div>
            </div>
          </div>

          {/* AI intro + streaming status card */}
          <div className="wx-msg">
            <div className="wx-m-av ai" aria-hidden="true">🧠</div>
            <div className="wx-m-body">
              <div className="wx-m-name">{t('landing.officer_name')}</div>
              <div className="wx-m-text">
                <p>{t('landing.ai_msg_intro')}</p>
              </div>
              <SimStatusCard />
            </div>
          </div>

          {/* AI summary + artifact card */}
          <div className="wx-msg">
            <div className="wx-m-av ai" aria-hidden="true">🧠</div>
            <div className="wx-m-body">
              <div className="wx-m-name">{t('landing.officer_name')}</div>
              <div className="wx-m-text">
                <p>{t('landing.ai_msg_summary')}</p>
              </div>
              <ReportArtifact onExpand={onRunRealSim} />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function SimStatusCard() {
  const { t } = useTranslation()
  return (
    <div
      style={{
        background: 'linear-gradient(135deg,#0E1726,#1A2B52)',
        borderRadius: 16,
        padding: 16,
        color: '#fff',
        margin: '8px 0 4px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{
        display: 'flex', alignItems: 'center', gap: 9,
        fontSize: 12.5, color: '#9DAAC4', marginBottom: 14,
      }}>
        <span
          aria-hidden="true"
          style={{
            width: 14, height: 14,
            border: '2px solid rgba(91,232,251,.3)',
            borderTopColor: '#5BE8FB',
            borderRadius: '50%',
            display: 'inline-block',
            animation: 'wxspin .8s linear infinite',
          }}
        />
        <span>{t('landing.ai_msg_progress_status')}</span>
      </div>
      <SimStep done label={t('landing.ai_msg_progress_step1')} />
      <SimStep done label={t('landing.ai_msg_progress_step2')} />
      <SimStep active label={t('landing.ai_msg_progress_step3')} />
      <SimStep label={t('landing.ai_msg_progress_step4')} />
    </div>
  )
}

function SimStep({ done, active, label }: { done?: boolean; active?: boolean; label: string }) {
  const color = done ? '#C4D2EC' : active ? '#5BE8FB' : '#7F8DA8'
  const fontWeight = active ? 500 : 400
  const icBg = done ? '#3DDC97' : 'transparent'
  const icColor = done ? '#0E1726' : color
  const sym = done ? '✓' : active ? '●' : '○'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      fontSize: 13, padding: '5px 0',
      color, fontWeight,
    }}>
      <span style={{
        width: 18, height: 18, borderRadius: '50%',
        border: `1.5px solid ${color}`,
        background: icBg, color: icColor,
        display: 'grid', placeItems: 'center', fontSize: 10,
        flexShrink: 0,
      }} aria-hidden="true">{sym}</span>
      <span>{label}</span>
    </div>
  )
}

interface ReportArtifactProps { onExpand: () => void }
function ReportArtifact({ onExpand }: ReportArtifactProps) {
  const { t } = useTranslation()
  const bars = [
    { key: 'landing.report_bar_grape_6', value: '34.2%', pct: 68,
      grad: 'linear-gradient(90deg,#1B4DFF,#00B8D4)', highlight: true },
    { key: 'landing.report_bar_grape_5', value: '31.0%', pct: 62,
      grad: 'linear-gradient(90deg,#7C5CFC,#9B82FF)' },
    { key: 'landing.report_bar_peach_6', value: '29.7%', pct: 59,
      grad: 'linear-gradient(90deg,#1B4DFF,#5B82FF)' },
    { key: 'landing.report_bar_grape_8', value: '18.6%', pct: 37,
      grad: 'linear-gradient(90deg,#FF6B3D,#FFA07D)', warn: true },
  ]
  return (
    <div className="wx-art-card" style={{
      margin: '8px 0 4px',
      overflow: 'hidden',
      padding: 0,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 11,
        padding: '14px 16px',
        background: 'linear-gradient(135deg,#0E1726,#1A2B52)',
        color: '#fff',
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: 'rgba(91,232,251,.16)',
          display: 'grid', placeItems: 'center',
          fontSize: 16,
        }} aria-hidden="true">📊</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <b style={{ display: 'block', fontSize: 13.5, fontWeight: 700 }}>
            {t('landing.report_title')}
          </b>
          <small style={{ fontSize: 11, color: '#9DAAC4', display: 'block' }}>
            {t('landing.report_calibration')}
          </small>
        </div>
        <button
          type="button"
          onClick={onExpand}
          style={{
            fontSize: 12, fontWeight: 600,
            color: '#0E1726', background: '#5BE8FB',
            border: 'none', padding: '7px 12px',
            borderRadius: 9, cursor: 'pointer',
          }}
        >
          {t('landing.panel_expand_cockpit')}
        </button>
      </div>
      <div style={{ padding: 18 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 11, fontWeight: 700, color: '#10B981',
          background: 'rgba(0,217,113,.12)',
          padding: '5px 11px', borderRadius: 20,
          width: 'fit-content', marginBottom: 13,
        }}>{t('landing.report_recommend')}</div>
        {bars.map((b) => (
          <div key={b.key} style={{ marginBottom: 11 }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontSize: 12.5, marginBottom: 6,
            }}>
              <b style={{ fontWeight: 500, color: 'var(--wx-text-primary)' }}>
                {t(b.key)}
              </b>
              <span style={{
                fontFamily: 'ui-monospace,Menlo,Consolas,monospace',
                fontWeight: 700,
                color: b.highlight ? 'var(--wx-accent-cyan)'
                     : b.warn ? 'var(--wx-accent-orange)'
                     : 'var(--wx-text-primary)',
              }}>{b.value}</span>
            </div>
            <div style={{
              height: 9, borderRadius: 9,
              background: 'rgba(255,255,255,.06)',
              overflow: 'hidden',
            }}>
              <span style={{
                display: 'block', height: '100%',
                width: `${b.pct}%`, background: b.grad,
                borderRadius: 9,
              }} />
            </div>
          </div>
        ))}
        <div style={{
          display: 'flex', gap: 0, marginTop: 16,
          borderTop: '1px solid rgba(255,255,255,.08)', paddingTop: 14,
        }}>
          <ReportStat value="34.2%" color="var(--wx-accent-cyan)"
                      label={t('landing.report_stat_conversion')} />
          <ReportStat value="¥6" color="var(--wx-accent-orange)"
                      label={t('landing.report_stat_best_price')} />
          <ReportStat value="±2.8%" color="#10B981"
                      label={t('landing.report_stat_ci')} last />
        </div>
      </div>
    </div>
  )
}

function ReportStat({ value, color, label, last }: { value: string; color: string; label: string; last?: boolean }) {
  return (
    <div style={{
      flex: 1, textAlign: 'center',
      borderRight: last ? 'none' : '1px solid rgba(255,255,255,.08)',
    }}>
      <b style={{
        display: 'block', fontSize: 20, fontWeight: 800,
        color, lineHeight: 1.1,
      }}>{value}</b>
      <small style={{ fontSize: 11, color: 'var(--wx-text-tertiary)' }}>{label}</small>
    </div>
  )
}
