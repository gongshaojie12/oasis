// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Public route /invite/:token — if the user is logged in, accept the
// invite immediately and route to the workspace. Otherwise, send them
// to /login and preserve the token so we can come back.
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { GlassCard } from '@/components/GlassCard'
import { PageShell } from '@/components/PageShell'
import { useAuthStore } from '@/stores/authStore'
import type { MeResponse, Workspace } from '@/types/api'

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const { t } = useTranslation()
  const nav = useNavigate()
  const setWorkspaces = useAuthStore((s) => s.setWorkspaces)
  const setCurrentWorkspace = useAuthStore((s) => s.setCurrentWorkspace)
  const [status, setStatus] = useState<'idle' | 'accepting' | 'done' | 'error'>(
    'idle',
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    if (!isAuthenticated()) {
      // Park the token in router state so the login page can resume.
      nav('/login', { state: { inviteToken: token }, replace: true })
      return
    }
    setStatus('accepting')
    api
      .post<{ ok: boolean; workspace?: Workspace }>(
        '/invites/accept',
        { token },
      )
      .then(async (r) => {
        toast.success(t('members.invite_accepted'))
        // Refresh workspace list so the new one shows up in the sidebar.
        try {
          const me = await api.get<MeResponse>('/me')
          setWorkspaces(me.data.workspaces)
        } catch {
          /* ignore */
        }
        const ws = r.data.workspace
        if (ws) {
          setCurrentWorkspace(ws.slug)
          setStatus('done')
          nav(`/w/${ws.slug}`, { replace: true })
        } else {
          nav('/workspaces', { replace: true })
        }
      })
      .catch((err) => {
        const e = err as { response?: { data?: { detail?: string } } }
        setError(e.response?.data?.detail ?? t('common.error'))
        setStatus('error')
      })
  }, [token, nav, setWorkspaces, setCurrentWorkspace, t])

  return (
    <PageShell>
      <GlassCard>
        {status === 'accepting' && <p>{t('members.invite_accepting')}</p>}
        {status === 'error' && (
          <>
            <p
              className="text-sm"
              style={{ color: 'var(--wx-danger)', marginBottom: 12 }}
            >
              {error ?? t('common.error')}
            </p>
            <button
              type="button"
              className="wx-btn-primary text-sm"
              onClick={() => nav('/workspaces')}
            >
              {t('common.continue')}
            </button>
          </>
        )}
        {status === 'idle' && <p>{t('common.loading')}</p>}
      </GlassCard>
    </PageShell>
  )
}
