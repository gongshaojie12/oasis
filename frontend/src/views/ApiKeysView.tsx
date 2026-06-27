// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Reusable API Keys view — used by /w/:slug/api-keys and LandingPage.
import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Copy, KeyRound, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { GlassCard } from '@/components/GlassCard'
import { DataTable, type Column } from '@/components/data/DataTable'
import { Modal } from '@/components/data/Modal'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { FormField } from '@/components/forms/FormField'
import { Select } from '@/components/forms/Select'
import type { ApiKeyCreated, ApiKeyEntry } from '@/types/api'

export function ApiKeysView({ slug }: { slug: string }) {
  const { t, i18n } = useTranslation()
  const [keys, setKeys] = useState<ApiKeyEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [role, setRole] = useState<'admin' | 'member'>('member')
  const [rpm, setRpm] = useState(60)
  const [submitting, setSubmitting] = useState(false)
  const [created, setCreated] = useState<ApiKeyCreated | null>(null)
  const [confirmRevoke, setConfirmRevoke] = useState<ApiKeyEntry | null>(null)
  const [revoking, setRevoking] = useState(false)

  async function load() {
    if (!slug) return
    setLoading(true)
    try {
      const r = await api.get<{ api_keys: ApiKeyEntry[] }>(
        `/workspaces/${slug}/api-keys`,
      )
      setKeys(r.data.api_keys ?? [])
    } catch {
      toast.error(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug])

  function fmtDate(iso: string): string {
    try {
      return new Date(iso).toLocaleDateString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN',
      )
    } catch {
      return iso
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    setSubmitting(true)
    try {
      const r = await api.post<ApiKeyCreated>(
        `/workspaces/${slug}/api-keys`,
        { name: trimmed, role, rpm_limit: rpm },
      )
      setCreated(r.data)
      setCreateOpen(false)
      setName('')
      setRole('member')
      setRpm(60)
      await load()
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e.response?.data?.detail ?? t('common.error'))
    } finally {
      setSubmitting(false)
    }
  }

  async function copyKey(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(t('api_keys.copied'))
    } catch {
      toast.error(t('common.error'))
    }
  }

  async function handleRevoke() {
    if (!confirmRevoke || !slug) return
    setRevoking(true)
    try {
      await api.delete(
        `/workspaces/${slug}/api-keys/${confirmRevoke.key_id}`,
      )
      toast.success(t('api_keys.revoked'))
      setConfirmRevoke(null)
      await load()
    } catch {
      toast.error(t('common.error'))
    } finally {
      setRevoking(false)
    }
  }

  const columns: Column<ApiKeyEntry>[] = [
    {
      key: 'name',
      header: t('api_keys.col_name'),
      render: (k) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <KeyRound size={14} color="var(--wx-accent-cyan)" />
          {k.name}
        </div>
      ),
    },
    {
      key: 'preview',
      header: t('api_keys.col_preview'),
      render: (k) => (
        <code
          style={{
            fontSize: 12,
            color: 'var(--wx-text-secondary)',
          }}
        >
          {k.api_key_preview}
        </code>
      ),
      width: '160px',
    },
    {
      key: 'role',
      header: t('api_keys.col_role'),
      render: (k) => (
        <span
          className={`wx-pill ${k.role === 'admin' ? 'wx-pill-info' : ''}`}
        >
          {t(`members.role_${k.role}`)}
        </span>
      ),
      width: '100px',
    },
    {
      key: 'rpm',
      header: t('api_keys.col_rpm'),
      accessor: (k) => k.rpm_limit,
      align: 'right',
      width: '90px',
    },
    {
      key: 'created',
      header: t('api_keys.col_created'),
      accessor: (k) => k.created_at,
      render: (k) => fmtDate(k.created_at),
      width: '130px',
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '60px',
      render: (k) => (
        <button
          type="button"
          className="wx-icon-btn wx-icon-btn-danger"
          title={t('api_keys.revoke')}
          onClick={(e) => {
            e.stopPropagation()
            setConfirmRevoke(k)
          }}
        >
          <Trash2 size={14} />
        </button>
      ),
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('api_keys.title')}</h1>
          <p className="wx-page-subtitle">{t('api_keys.subtitle')}</p>
        </div>
        <button
          type="button"
          className="wx-btn-primary text-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          onClick={() => setCreateOpen(true)}
        >
          <KeyRound size={14} />
          {t('api_keys.create')}
        </button>
      </div>

      <DataTable
        columns={columns}
        rows={keys}
        rowKey={(k) => k.key_id}
        loading={loading}
        emptyMessage={t('api_keys.empty')}
      />

      <GlassCard className="mt-6">
        <div className="wx-stat-label" style={{ marginBottom: 8 }}>
          {t('api_keys.usage_example')}
        </div>
        <div className="wx-code-block">
{`curl -H "X-API-Key: <YOUR_KEY>" \\
     -H "Content-Type: application/json" \\
     -d '{"scenario":{"material":"...","question":"...","kind":"rate"},"n":50,"rounds":0,"distribution_path":"cn_national_joint_2020"}' \\
     ${window.location.origin}/v1/simulations/async`}
        </div>
      </GlassCard>

      <Modal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t('api_keys.create')}
      >
        <form onSubmit={handleCreate}>
          <FormField label={t('api_keys.name')}>
            <input
              className="wx-input"
              value={name}
              maxLength={64}
              required
              autoFocus
              onChange={(e) => setName(e.target.value)}
              placeholder="staging-key"
            />
          </FormField>
          <FormField label={t('api_keys.role')}>
            <Select
              value={role}
              options={[
                { value: 'member', label: t('members.role_member') },
                { value: 'admin', label: t('members.role_admin') },
              ]}
              onChange={(v) => setRole(v as 'admin' | 'member')}
            />
          </FormField>
          <FormField label={t('api_keys.rpm')}>
            <input
              type="number"
              className="wx-input"
              value={rpm}
              min={1}
              max={10000}
              onChange={(e) => setRpm(Number(e.target.value) || 60)}
            />
          </FormField>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <button
              type="button"
              className="wx-btn-ghost"
              onClick={() => setCreateOpen(false)}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="wx-btn-primary"
              disabled={submitting || !name.trim()}
            >
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </Modal>

      {created && (
        <Modal
          isOpen
          closeOnBackdrop={false}
          onClose={() => setCreated(null)}
          title={t('api_keys.show_once')}
          size="lg"
        >
          <p
            className="text-sm"
            style={{
              color: 'var(--wx-warning)',
              marginBottom: 12,
              fontWeight: 500,
            }}
          >
            {t('api_keys.show_once_hint')}
          </p>
          <div className="wx-code-block" style={{ marginBottom: 12 }}>
            {created.api_key}
          </div>
          <div
            style={{
              display: 'flex',
              gap: 10,
              justifyContent: 'flex-end',
            }}
          >
            <button
              type="button"
              className="wx-btn-ghost text-sm"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
              onClick={() => void copyKey(created.api_key)}
            >
              <Copy size={14} />
              {t('api_keys.copy')}
            </button>
            <button
              type="button"
              className="wx-btn-primary"
              onClick={() => setCreated(null)}
            >
              {t('common.ok')}
            </button>
          </div>
        </Modal>
      )}

      <ConfirmDialog
        isOpen={confirmRevoke !== null}
        title={t('api_keys.revoke')}
        message={t('api_keys.revoke_confirm', {
          name: confirmRevoke?.name ?? '',
        })}
        destructive
        loading={revoking}
        onConfirm={handleRevoke}
        onCancel={() => setConfirmRevoke(null)}
      />
    </div>
  )
}
