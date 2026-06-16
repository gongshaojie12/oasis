// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Workspace members + pending invites with invite modal.
import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Trash2, UserPlus } from 'lucide-react'
import { api } from '@/lib/api'
import { DataTable, type Column } from '@/components/data/DataTable'
import { Modal } from '@/components/data/Modal'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { FormField } from '@/components/forms/FormField'
import { Select } from '@/components/forms/Select'
import type { Invite, Member, MemberRole } from '@/types/api'

function initials(name: string): string {
  return name?.slice(0, 1).toUpperCase() || '?'
}

export function MembersPage() {
  const { t, i18n } = useTranslation()
  const { slug } = useParams<{ slug: string }>()
  const [members, setMembers] = useState<Member[]>([])
  const [invites, setInvites] = useState<Invite[]>([])
  const [loading, setLoading] = useState(true)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<MemberRole>('member')
  const [submitting, setSubmitting] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState<Member | null>(null)
  const [removing, setRemoving] = useState(false)

  async function load() {
    if (!slug) return
    setLoading(true)
    try {
      const [ms, ins] = await Promise.all([
        api.get<{ members: Member[] }>(`/workspaces/${slug}/members`),
        api.get<{ invites: Invite[] }>(`/workspaces/${slug}/invites`).catch(() => ({ data: { invites: [] } })),
      ])
      setMembers(ms.data.members ?? [])
      setInvites(ins.data.invites ?? [])
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

  async function handleInvite(e: FormEvent) {
    e.preventDefault()
    const trimmed = email.trim()
    if (!trimmed) return
    setSubmitting(true)
    try {
      await api.post(`/workspaces/${slug}/invites`, {
        invited_email: trimmed,
        role,
        expires_in_days: 7,
      })
      toast.success(t('members.invite_sent'))
      setEmail('')
      setRole('member')
      setInviteOpen(false)
      await load()
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e.response?.data?.detail ?? t('common.error'))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemove() {
    if (!confirmRemove) return
    setRemoving(true)
    try {
      await api.delete(
        `/workspaces/${slug}/members/${confirmRemove.user_id}`,
      )
      toast.success(t('members.removed'))
      setConfirmRemove(null)
      await load()
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e.response?.data?.detail ?? t('common.error'))
    } finally {
      setRemoving(false)
    }
  }

  async function revokeInvite(inv: Invite) {
    if (!slug) return
    try {
      await api.delete(`/workspaces/${slug}/invites/${inv.invite_id}`)
      toast.success(t('members.invite_revoked'))
      await load()
    } catch {
      // backend may not yet implement DELETE invite — surface friendly note
      toast.error(t('common.error'))
    }
  }

  const memberCols: Column<Member>[] = [
    {
      key: 'name',
      header: t('members.col_name'),
      render: (m) => (
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 10 }}
        >
          <div
            className="wx-brand-avatar"
            style={{ width: 32, height: 32, fontSize: 13 }}
          >
            {initials(m.display_name)}
          </div>
          <div style={{ lineHeight: 1.3, minWidth: 0 }}>
            <div style={{ fontWeight: 600 }}>{m.display_name}</div>
            <div
              className="text-xs"
              style={{ color: 'var(--wx-text-tertiary)' }}
            >
              {m.email ?? m.phone ?? ''}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      header: t('members.col_role'),
      render: (m) => (
        <span
          className={`wx-pill ${m.role === 'owner' ? 'wx-pill-warning' : m.role === 'admin' ? 'wx-pill-info' : ''}`}
        >
          {t(`members.role_${m.role}`)}
        </span>
      ),
      width: '110px',
    },
    {
      key: 'joined_at',
      header: t('members.col_joined'),
      accessor: (m) => m.joined_at,
      render: (m) => fmtDate(m.joined_at),
      width: '140px',
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '60px',
      render: (m) => (
        <button
          type="button"
          className="wx-icon-btn wx-icon-btn-danger"
          disabled={m.role === 'owner'}
          title={
            m.role === 'owner'
              ? t('members.cannot_remove_owner')
              : t('members.remove')
          }
          onClick={(e) => {
            e.stopPropagation()
            setConfirmRemove(m)
          }}
        >
          <Trash2 size={14} />
        </button>
      ),
    },
  ]

  const inviteCols: Column<Invite>[] = [
    {
      key: 'email',
      header: t('members.col_invited_email'),
      render: (i) => i.invited_email,
    },
    {
      key: 'role',
      header: t('members.col_role'),
      render: (i) => (
        <span className="wx-pill">{t(`members.role_${i.role}`)}</span>
      ),
      width: '110px',
    },
    {
      key: 'expires',
      header: t('members.col_expires'),
      accessor: (i) => i.expires_at,
      render: (i) => fmtDate(i.expires_at),
      width: '140px',
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '120px',
      render: (i) => (
        <button
          type="button"
          className="wx-btn-ghost text-xs"
          onClick={() => void revokeInvite(i)}
        >
          {t('members.revoke_invite')}
        </button>
      ),
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('members.title')}</h1>
          <p className="wx-page-subtitle">{t('members.subtitle')}</p>
        </div>
        <button
          type="button"
          className="wx-btn-primary text-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          onClick={() => setInviteOpen(true)}
        >
          <UserPlus size={14} />
          {t('members.invite')}
        </button>
      </div>

      <DataTable
        columns={memberCols}
        rows={members}
        rowKey={(m) => m.user_id}
        loading={loading}
        emptyMessage={t('members.empty')}
      />

      {invites.length > 0 && (
        <>
          <h2
            style={{
              fontSize: 16,
              fontWeight: 600,
              margin: '24px 0 10px',
            }}
          >
            {t('members.pending_invites')}
          </h2>
          <DataTable
            columns={inviteCols}
            rows={invites}
            rowKey={(i) => i.invite_id}
          />
        </>
      )}

      <Modal
        isOpen={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title={t('members.invite')}
      >
        <form onSubmit={handleInvite}>
          <FormField label={t('members.invite_email')}>
            <input
              type="email"
              className="wx-input"
              value={email}
              required
              autoFocus
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alice@example.com"
            />
          </FormField>
          <FormField label={t('members.invite_role')}>
            <Select
              value={role}
              options={[
                { value: 'member', label: t('members.role_member') },
                { value: 'admin', label: t('members.role_admin') },
              ]}
              onChange={(v) => setRole(v as MemberRole)}
            />
          </FormField>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <button
              type="button"
              className="wx-btn-ghost"
              onClick={() => setInviteOpen(false)}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="wx-btn-primary"
              disabled={submitting || !email.trim()}
            >
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={confirmRemove !== null}
        title={t('members.remove')}
        message={t('members.remove_confirm', {
          name: confirmRemove?.display_name ?? '',
        })}
        destructive
        loading={removing}
        onConfirm={handleRemove}
        onCancel={() => setConfirmRemove(null)}
      />
    </div>
  )
}
