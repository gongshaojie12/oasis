// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { GlassCard } from '@/components/GlassCard'
import { FormField } from '@/components/forms/FormField'
import { Select } from '@/components/forms/Select'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { useAuthStore } from '@/stores/authStore'
import type { Workspace } from '@/types/api'

export function WorkspaceSettingsPage() {
  const { t } = useTranslation()
  const { slug } = useParams<{ slug: string }>()
  const nav = useNavigate()
  const user = useAuthStore((s) => s.user)
  const workspaces = useAuthStore((s) => s.workspaces)
  const setWorkspaces = useAuthStore((s) => s.setWorkspaces)
  const ws = workspaces.find((w) => w.slug === slug)
  const [name, setName] = useState(ws?.name ?? '')
  const [locale, setLocale] = useState(ws?.locale ?? 'zh')
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [ownerId, setOwnerId] = useState<string | null>(null)

  useEffect(() => {
    if (ws) {
      setName(ws.name)
      setLocale(ws.locale)
    }
  }, [ws])

  // Pull workspace detail so we know the owner_user_id (auth store has the
  // bare list shape; PATCH/delete needs owner check on the UI side too).
  useEffect(() => {
    if (!slug) return
    api
      .get<{ owner_user_id?: string }>(`/workspaces/${slug}`)
      .then((r) => setOwnerId(r.data.owner_user_id ?? null))
      .catch(() => {
        /* non-fatal */
      })
  }, [slug])

  const isOwner = !!user && !!ownerId && user.user_id === ownerId
  const canDelete = isOwner && ws?.type === 'team'

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    if (!slug) return
    setSaving(true)
    try {
      const r = await api.patch<Workspace>(`/workspaces/${slug}`, {
        name: name.trim() || undefined,
        locale,
      })
      setWorkspaces(
        workspaces.map((w) =>
          w.slug === slug ? { ...w, ...r.data } : w,
        ),
      )
      toast.success(t('settings.saved'))
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e.response?.data?.detail ?? t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!slug) return
    setDeleting(true)
    try {
      await api.delete(`/workspaces/${slug}`)
      toast.success(t('settings.deleted'))
      setWorkspaces(workspaces.filter((w) => w.slug !== slug))
      nav('/workspaces', { replace: true })
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e.response?.data?.detail ?? t('common.error'))
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  if (!ws) {
    return (
      <div style={{ padding: '28px 36px' }}>
        <GlassCard>{t('workspaces.empty')}</GlassCard>
      </div>
    )
  }

  return (
    <div style={{ padding: '28px 36px', maxWidth: 640 }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('settings.workspace_title')}</h1>
          <p className="wx-page-subtitle">{t('settings.workspace_subtitle')}</p>
        </div>
      </div>

      <GlassCard>
        <form onSubmit={handleSave}>
          <FormField label={t('onboarding.workspace_name')}>
            <input
              className="wx-input"
              value={name}
              maxLength={64}
              onChange={(e) => setName(e.target.value)}
            />
          </FormField>
          <FormField
            label={t('settings.locale')}
            hint={t('settings.locale_hint')}
          >
            <Select
              value={locale}
              options={[
                { value: 'zh', label: '中文' },
                { value: 'en', label: 'English' },
              ]}
              onChange={setLocale}
            />
          </FormField>
          <div
            style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}
          >
            <button
              type="submit"
              className="wx-btn-primary"
              disabled={saving || !name.trim()}
            >
              {saving ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </GlassCard>

      {canDelete && (
        <GlassCard className="mt-6">
          <div className="wx-stat-label" style={{ marginBottom: 8 }}>
            {t('settings.danger_zone')}
          </div>
          <p
            className="text-sm"
            style={{
              color: 'var(--wx-text-secondary)',
              marginBottom: 12,
            }}
          >
            {t('settings.delete_hint')}
          </p>
          <button
            type="button"
            className="wx-btn-ghost"
            style={{
              color: 'var(--wx-danger)',
              borderColor: 'rgba(255, 77, 110, .35)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
            onClick={() => setConfirmDelete(true)}
          >
            <Trash2 size={14} />
            {t('settings.delete_workspace')}
          </button>
        </GlassCard>
      )}

      <ConfirmDialog
        isOpen={confirmDelete}
        title={t('settings.delete_workspace')}
        message={t('settings.delete_confirm', { name: ws.name })}
        destructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  )
}
