// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// LandingPage left sidebar — visual mock of chat.html .sb / .sandbox / .usr.
// Hardcoded sample sandboxes; clicking any item triggers the auth gate.
import { useTranslation } from 'react-i18next'
import { BrandLogo } from '@/components/BrandLogo'

interface MockSandbox {
  id: string
  emoji: string
  nameKey: string
  statusKey: string
  live?: boolean
  active?: boolean
}

const SANDBOXES: MockSandbox[] = [
  { id: 'genz', emoji: '🥤', nameKey: 'landing.sandbox_genz',
    statusKey: 'landing.sandbox_genz_status', live: true, active: true },
  { id: 'lower', emoji: '📱', nameKey: 'landing.sandbox_lower',
    statusKey: 'landing.sandbox_lower_status' },
  { id: 'newtier', emoji: '💄', nameKey: 'landing.sandbox_newtier',
    statusKey: 'landing.sandbox_newtier_status' },
  { id: 'driver', emoji: '🚗', nameKey: 'landing.sandbox_driver',
    statusKey: 'landing.sandbox_driver_status' },
  { id: 'hnw', emoji: '🏦', nameKey: 'landing.sandbox_hnw',
    statusKey: 'landing.sandbox_hnw_status' },
]

interface Props {
  onGatedAction: () => void
}

export function MockSidebar({ onGatedAction }: Props) {
  const { t } = useTranslation()

  return (
    <aside className="wx-sb">
      <div className="wx-sb-brand">
        <BrandLogo size="sm" />
      </div>
      <button
        type="button"
        className="wx-new-btn"
        onClick={onGatedAction}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2.4"
             strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12h14" />
          <path d="M12 5v14" />
        </svg>
        {t('landing.new_sandbox')}
      </button>
      <div className="wx-sb-label">{t('landing.sandbox_label')}</div>
      <div className="wx-sb-scroll">
        {SANDBOXES.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`wx-sandbox ${s.active ? 'on' : ''}`}
            onClick={onGatedAction}
          >
            <span className="wx-sb-emoji" aria-hidden="true">{s.emoji}</span>
            <span className="wx-sb-txt">
              <b>{t(s.nameKey)}</b>
              <small>
                {s.live && (
                  <span
                    aria-hidden="true"
                    style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: '#FF6B3D',
                      boxShadow: '0 0 6px #FF6B3D',
                      display: 'inline-block',
                      animation: 'wxblink 1.4s infinite',
                    }}
                  />
                )}
                {t(s.statusKey)}
              </small>
            </span>
          </button>
        ))}
      </div>
      <div className="wx-sb-foot">
        <button
          type="button"
          className="wx-usr"
          onClick={onGatedAction}
        >
          <span className="wx-usr-av" aria-hidden="true">
            {t('landing.user_initial')}
          </span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <b style={{ display: 'block', fontSize: 12.5, lineHeight: 1.3 }}>
              {t('landing.header_user')}
            </b>
            <small style={{ fontSize: 10.5, color: 'var(--wx-text-tertiary)' }}>
              {t('landing.header_team')}
            </small>
          </span>
        </button>
      </div>
    </aside>
  )
}
