// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Reusable Workspace Settings view — used by /w/:slug/settings and LandingPage.
import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { GlassCard } from '@/components/GlassCard'
import { FormField } from '@/components/forms/FormField'
import { Select } from '@/components/forms/Select'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { useAuthStore } from '@/stores/authStore'
import type { Workspace } from '@/types/api'

export function SettingsView({ slug }: { slug: string }) {
  const { t } = useTranslation()
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

  // ── model config state ──
  const [presets, setPresets] = useState<Array<{
    id: string; label: string; base_url: string | null;
    default_model: string | null; needs_key: boolean;
    allow_custom_base_url: boolean }>>([])
  const [mcProvider, setMcProvider] = useState('stub')
  const [mcKey, setMcKey] = useState('')
  const [mcKeyMasked, setMcKeyMasked] = useState<string | null>(null)
  const [mcBaseUrl, setMcBaseUrl] = useState('')
  const [mcModelName, setMcModelName] = useState('')
  const [mcSaving, setMcSaving] = useState(false)
  const [myRole, setMyRole] = useState<string>('member')

  useEffect(() => {
    api.get('/model-presets')
      .then((r) => setPresets(r.data.presets ?? []))
      .catch(() => { /* non-fatal */ })
  }, [])

  useEffect(() => {
    if (!slug) return
    api.get(`/workspaces/${slug}/model-config`).then((r) => {
      setMcProvider(r.data.provider ?? 'stub')
      setMcKeyMasked(r.data.api_key_masked ?? null)
      setMcBaseUrl(r.data.base_url ?? '')
      setMcModelName(r.data.model_name ?? '')
    }).catch(() => { /* non-fatal */ })
    api.get(`/workspaces/${slug}/members`).then((r) => {
      const me = (r.data.members ?? []).find(
        (m: { user_id: string }) => m.user_id === user?.user_id)
      if (me) setMyRole(me.role)
    }).catch(() => { /* non-fatal */ })
  }, [slug, user?.user_id])

  const canEditModel = myRole === 'owner' || myRole === 'admin'
  const curPreset = presets.find((p) => p.id === mcProvider)

  async function handleSaveModel(e: FormEvent) {
    e.preventDefault()
    if (!slug) return
    setMcSaving(true)
    try {
      const payload: Record<string, unknown> = { provider: mcProvider }
      if (mcKey) payload.api_key = mcKey
      if (curPreset?.allow_custom_base_url) payload.base_url = mcBaseUrl
      if (mcModelName) payload.model_name = mcModelName
      const r = await api.put(
        `/workspaces/${slug}/model-config`, payload)
      setMcKey('')
      setMcKeyMasked(r.data.api_key_masked ?? null)
      toast.success(t('settings.model_saved'))
    } catch (err) {
      const ex = err as { response?: { data?: { detail?: string } } }
      toast.error(ex.response?.data?.detail ?? t('common.error'))
    } finally {
      setMcSaving(false)
    }
  }

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

      <GlassCard className="mt-6">
        <div className="wx-page-header" style={{ marginBottom: 12 }}>
          <div>
            <h2 className="wx-page-title" style={{ fontSize: 18 }}>
              {t('settings.model_title')}
            </h2>
            <p className="wx-page-subtitle">{t('settings.model_subtitle')}</p>
          </div>
        </div>
        {!canEditModel && (
          <p className="text-sm" style={{ color: 'var(--wx-text-secondary)',
               marginBottom: 12 }}>
            {t('settings.model_readonly_hint')}
          </p>
        )}
        <form onSubmit={handleSaveModel}>
          <FormField label={t('settings.model_provider')}>
            <select
              data-testid="model-provider-select"
              className="wx-input"
              value={mcProvider}
              disabled={!canEditModel}
              onChange={(e) => setMcProvider(e.target.value)}
            >
              {presets.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </FormField>
          {curPreset?.needs_key && (
            <FormField label={t('settings.model_api_key')}
                       hint={t('settings.model_api_key_hint')}>
              <input
                className="wx-input"
                type="password"
                value={mcKey}
                disabled={!canEditModel}
                placeholder={mcKeyMasked ?? ''}
                onChange={(e) => setMcKey(e.target.value)}
              />
            </FormField>
          )}
          {curPreset?.allow_custom_base_url && (
            <FormField label={t('settings.model_base_url')}>
              <input
                className="wx-input"
                value={mcBaseUrl}
                disabled={!canEditModel}
                placeholder="https://your-gateway/v1"
                onChange={(e) => setMcBaseUrl(e.target.value)}
              />
            </FormField>
          )}
          <FormField label={t('settings.model_model_name')}>
            <input
              className="wx-input"
              value={mcModelName}
              disabled={!canEditModel}
              placeholder={curPreset?.default_model ?? ''}
              onChange={(e) => setMcModelName(e.target.value)}
            />
          </FormField>
          {canEditModel && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="wx-btn-primary"
                      disabled={mcSaving}>
                {mcSaving ? t('common.loading') : t('common.submit')}
              </button>
            </div>
          )}
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
