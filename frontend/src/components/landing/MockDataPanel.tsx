// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage right data panel — visual mock of chat.html .panel.
// Static metrics (no live animation), but the four-quadrant legend, progress
// bar, KPI rows, and CTA buttons all render faithfully.
import { useTranslation } from 'react-i18next'

interface Props {
  onGatedAction: () => void
}

export function MockDataPanel({ onGatedAction }: Props) {
  const { t } = useTranslation()

  return (
    <aside className="wx-panel" aria-label="WANXIANG live data panel">
      {/* Header */}
      <header style={{ textTransform: 'none', letterSpacing: 'normal' }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          fontFamily: 'inherit', fontSize: 13.5, fontWeight: 600,
          color: 'var(--wx-text-primary)',
          textTransform: 'none', letterSpacing: 'normal',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="#5BE8FB" strokeWidth="2"
               strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <path d="m19 9-5 5-4-4-3 3" />
          </svg>
          {t('landing.panel_live')}
        </span>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          fontSize: 11, fontWeight: 700, color: '#FF9E7D',
          background: 'rgba(255,107,61,.14)',
          padding: '4px 10px', borderRadius: 20,
        }}>
          <span aria-hidden="true" style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#FF6B3D',
            animation: 'wxblink 1.4s infinite',
          }} />
          LIVE
        </span>
      </header>

      {/* Particles / observation block */}
      <section>
        <SectionHeading label={t('landing.panel_observation')} />
        <div style={{
          height: 160, borderRadius: 14,
          background: 'radial-gradient(400px 300px at 50% 40%,rgba(27,77,255,.12),transparent 70%)',
          border: '1px solid rgba(91,232,251,.12)',
          position: 'relative', overflow: 'hidden',
          marginBottom: 12,
        }} aria-hidden="true">
          <ParticleField />
          <div style={{
            position: 'absolute', left: 12, bottom: 10,
            fontSize: 10, color: '#9DAAC4',
            fontFamily: 'ui-monospace,Menlo,Consolas,monospace',
          }}>{t('landing.panel_sampling')}</div>
        </div>
        <Legend t={t} />
      </section>

      {/* Progress + KPI rows */}
      <section>
        <SectionHeading label={t('landing.panel_progress')} />
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'baseline', marginBottom: 9,
        }}>
          <b style={{ fontSize: 26, fontWeight: 800, color: '#5BE8FB' }}>71%</b>
          <span style={{ fontSize: 11, color: '#7F8DA8' }}>
            {t('landing.panel_timestep')}
          </span>
        </div>
        <div style={{
          height: 8, borderRadius: 8,
          background: 'rgba(91,232,251,.12)', overflow: 'hidden',
          marginBottom: 14,
        }}>
          <span style={{
            display: 'block', height: '100%', width: '71%',
            background: 'linear-gradient(90deg,#1B4DFF,#5BE8FB)',
            boxShadow: '0 0 10px rgba(91,232,251,.6)',
          }} />
        </div>
        <KpiRow label={t('landing.panel_active')} value="50,000" tone="cyan" />
        <KpiRow label={t('landing.panel_decisions')} value="3,418,902" />
        <KpiRow label={t('landing.panel_current_scenario')}
                value={t('landing.panel_scenario_value')} tone="orange" />
        <KpiRow label={t('landing.panel_sentiment')}
                value={t('landing.panel_sentiment_value')} tone="green" />
        <KpiRow label={t('landing.panel_calibration')} value="91.3%" tone="cyan" />
      </section>

      {/* CTA buttons */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button
          type="button"
          onClick={onGatedAction}
          style={{
            width: '100%', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            gap: 9, padding: 13, borderRadius: 12, border: 'none',
            cursor: 'pointer', fontWeight: 600, fontSize: 13.5,
            background: 'linear-gradient(135deg,#1B4DFF,#3D6BFF)',
            color: '#fff',
            boxShadow: '0 8px 18px -8px rgba(27,77,255,.6)',
            font: 'inherit',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2.2"
               strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 3h6v6M21 3l-9 9M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
          </svg>
          {t('landing.panel_expand_cockpit')}
        </button>
        <button
          type="button"
          onClick={onGatedAction}
          style={{
            width: '100%', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            gap: 9, padding: 13, borderRadius: 12,
            border: '1px solid rgba(91,232,251,.16)',
            cursor: 'pointer', fontWeight: 600, fontSize: 13.5,
            background: 'rgba(255,255,255,.06)',
            color: '#E8EEFA',
            font: 'inherit',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2"
               strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <path d="m7 10 5 5 5-5" />
            <path d="M12 15V3" />
          </svg>
          {t('landing.panel_export_pdf')}
        </button>
      </section>
    </aside>
  )
}

function SectionHeading({ label }: { label: string }) {
  return (
    <div style={{
      fontSize: 11, color: '#7F8DA8',
      letterSpacing: 1.5, fontWeight: 700,
      marginBottom: 12,
      display: 'flex', alignItems: 'center', gap: 8,
      textTransform: 'uppercase',
    }}>
      <span aria-hidden="true" style={{
        width: 5, height: 5, borderRadius: '50%',
        background: '#5BE8FB', boxShadow: '0 0 6px #5BE8FB',
      }} />
      {label}
    </div>
  )
}

function Legend({ t }: { t: (k: string) => string }) {
  const items = [
    { color: '#3DDC97', label: t('landing.metric_buy') },
    { color: '#5BE8FB', label: t('landing.metric_hesitate') },
    { color: '#FF6B3D', label: t('landing.metric_priced_out') },
    { color: '#7C5CFC', label: t('landing.metric_swayed') },
  ]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {items.map((i) => (
        <div key={i.label} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 11.5, color: '#C4D2EC',
        }}>
          <span aria-hidden="true" style={{
            width: 9, height: 9, borderRadius: '50%',
            background: i.color, flexShrink: 0,
          }} />
          {i.label}
        </div>
      ))}
    </div>
  )
}

function KpiRow({ label, value, tone }: {
  label: string; value: string; tone?: 'cyan' | 'orange' | 'green'
}) {
  const color = tone === 'cyan' ? '#5BE8FB'
              : tone === 'orange' ? '#FF9E7D'
              : tone === 'green' ? '#3DDC97'
              : 'var(--wx-text-primary)'
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      padding: '10px 0',
      borderBottom: '1px solid rgba(255,255,255,.05)',
      fontSize: 12.5,
    }}>
      <span style={{ color: '#9DAAC4' }}>{label}</span>
      <b style={{
        fontFamily: 'ui-monospace,Menlo,Consolas,monospace',
        fontWeight: 700, color,
      }}>{value}</b>
    </div>
  )
}

/** Static dot field — no animation, but the visual rhythm matches the
 *  swarm canvas in chat.html. Four clusters, ~120 dots total. */
function ParticleField() {
  // Deterministic pseudo-random for SSR stability + visual repeatability.
  const clusters = [
    { cx: 30, cy: 34, color: '#3DDC97' },
    { cx: 68, cy: 30, color: '#5BE8FB' },
    { cx: 38, cy: 72, color: '#FF6B3D' },
    { cx: 72, cy: 68, color: '#7C5CFC' },
  ]
  const dots: { x: number; y: number; c: string; r: number }[] = []
  let seed = 1
  function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 }
  for (let i = 0; i < 120; i++) {
    const cl = clusters[i % 4]
    const r = Math.sqrt(rnd()) * 14
    const a = rnd() * Math.PI * 2
    dots.push({
      x: cl.cx + Math.cos(a) * r,
      y: cl.cy + Math.sin(a) * r,
      c: cl.color,
      r: rnd() * 1.4 + 0.6,
    })
  }
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none"
         style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
      {clusters.map((c, i) => (
        <circle key={i} cx={c.cx} cy={c.cy} r={16}
                fill={c.color} opacity={0.08} />
      ))}
      {dots.map((d, i) => (
        <circle key={i} cx={d.x} cy={d.y} r={d.r}
                fill={d.c} opacity={0.85} />
      ))}
    </svg>
  )
}
