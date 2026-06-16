// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// P9b: Anonymous-accessible demo home — visual port of docs/prototype/chat.html.
// 3-column layout (sidebar | chat | data panel) with hardcoded sample data.
// Any interactive action (compose, run-real-sim, expand cockpit, new sandbox,
// click a sandbox in the list, click the user pill) triggers AuthGateModal
// for unauthenticated visitors. Already-authenticated users get a "Go to
// dashboard" affordance and are NOT auto-redirected — the demo stays one
// bookmark click away.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { I18nToggle } from '@/components/I18nToggle'
import { isAuthenticated } from '@/lib/auth'
import { MockSidebar } from '@/components/landing/MockSidebar'
import { MockChat } from '@/components/landing/MockChat'
import { MockDataPanel } from '@/components/landing/MockDataPanel'
import { MockComposer } from '@/components/landing/MockComposer'
import { AuthGateModal } from '@/components/landing/AuthGateModal'

export function LandingPage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const [gateOpen, setGateOpen] = useState(false)
  const [pendingText, setPendingText] = useState<string | undefined>(undefined)
  const [authed, setAuthed] = useState(false)

  // Compute auth state once after mount (avoids SSR/localStorage hydration mismatch).
  useEffect(() => {
    setAuthed(isAuthenticated())
  }, [])

  // Re-hydrate pending text if user came back from login with ?pending=...
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const p = params.get('pending')
    if (p) setPendingText(p)
  }, [])

  function handleGatedAction(text?: string) {
    if (authed) {
      if (text) {
        try {
          localStorage.setItem('wanxiang.pending_chat', text)
        } catch { /* quota / private mode */ }
      }
      nav('/dashboard')
      return
    }
    if (text) setPendingText(text)
    setGateOpen(true)
  }

  return (
    <>
      <div className="wx-app">
        <MockSidebar onGatedAction={() => handleGatedAction()} />
        <section className="wx-chat-col">
          <MockChat onRunRealSim={() => handleGatedAction()} />
          <MockComposer onTrySend={(text) => handleGatedAction(text)} />
        </section>
        <MockDataPanel onGatedAction={() => handleGatedAction()} />
      </div>

      {/* Floating controls: language toggle + (if authed) go-to-dashboard CTA. */}
      <div
        style={{
          position: 'fixed', top: 14, right: 18, zIndex: 200,
          display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        {authed && (
          <button
            type="button"
            className="wx-btn-primary"
            style={{ fontSize: 12.5, padding: '7px 14px' }}
            onClick={() => nav('/dashboard')}
          >
            {t('landing.go_dashboard')}
          </button>
        )}
        <I18nToggle />
      </div>

      <AuthGateModal
        open={gateOpen}
        onClose={() => setGateOpen(false)}
        pendingText={pendingText}
      />

      {/* Keyframes used by the streaming status card spinner. */}
      <style>{`@keyframes wxspin{to{transform:rotate(360deg)}}`}</style>
    </>
  )
}
