// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ShieldCheck, ShieldOff } from 'lucide-react'
import { api } from '@/lib/api'
import { DataTable, type Column } from '@/components/data/DataTable'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import type { User } from '@/types/api'

interface AdminUser extends User {
  user_id: string
  created_at?: string
}

export function AdminUsersPage() {
  const { t, i18n } = useTranslation()
  const [rows, setRows] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [pendingToggle, setPendingToggle] = useState<AdminUser | null>(null)
  const [toggling, setToggling] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const r = await api.get<{ users: AdminUser[] }>('/admin/users', {
        params: { limit: 200 },
      })
      setRows(r.data.users ?? [])
    } catch {
      toast.error(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function fmtDate(iso: string | undefined): string {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleDateString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN',
      )
    } catch {
      return iso
    }
  }

  async function handleConfirmToggle() {
    if (!pendingToggle) return
    setToggling(true)
    try {
      await api.patch(`/admin/users/${pendingToggle.user_id}/super-admin`, {
        user_id: pendingToggle.user_id,
        is_super_admin: !pendingToggle.is_super_admin,
      })
      toast.success(t('admin.updated'))
      setPendingToggle(null)
      await load()
    } catch {
      toast.error(t('common.error'))
    } finally {
      setToggling(false)
    }
  }

  const columns: Column<AdminUser>[] = [
    {
      key: 'identity',
      header: t('admin.col_identity'),
      render: (u) => (
        <div style={{ lineHeight: 1.3 }}>
          <div style={{ fontWeight: 600 }}>{u.display_name}</div>
          <div
            className="text-xs"
            style={{ color: 'var(--wx-text-tertiary)' }}
          >
            {u.email ?? u.phone ?? u.user_id.slice(0, 8)}
          </div>
        </div>
      ),
    },
    {
      key: 'verified',
      header: t('admin.col_verified'),
      render: (u) => (
        <div
          style={{
            display: 'flex',
            gap: 6,
            color: 'var(--wx-text-secondary)',
            fontSize: 11,
          }}
        >
          <span
            className={`wx-pill ${u.email_verified ? 'wx-pill-success' : ''}`}
          >
            email{u.email_verified ? '✓' : '✗'}
          </span>
          <span
            className={`wx-pill ${u.phone_verified ? 'wx-pill-success' : ''}`}
          >
            sms{u.phone_verified ? '✓' : '✗'}
          </span>
        </div>
      ),
      width: '180px',
    },
    {
      key: 'created',
      header: t('admin.col_created'),
      accessor: (u) => u.created_at ?? '',
      render: (u) => fmtDate(u.created_at),
      width: '130px',
    },
    {
      key: 'super_admin',
      header: t('admin.col_super_admin'),
      width: '140px',
      align: 'center',
      render: (u) => (
        <button
          type="button"
          className="wx-icon-btn"
          title={t('admin.toggle_super_admin')}
          style={{
            color: u.is_super_admin
              ? 'var(--wx-accent-amber)'
              : 'var(--wx-text-tertiary)',
          }}
          onClick={() => setPendingToggle(u)}
        >
          {u.is_super_admin ? (
            <ShieldCheck size={16} />
          ) : (
            <ShieldOff size={16} />
          )}
        </button>
      ),
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('admin.users')}</h1>
          <p className="wx-page-subtitle">{t('admin.users_subtitle')}</p>
        </div>
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(u) => u.user_id}
        loading={loading}
        emptyMessage={t('admin.no_users')}
      />
      <ConfirmDialog
        isOpen={pendingToggle !== null}
        title={t('admin.toggle_super_admin')}
        message={t('admin.toggle_super_admin_confirm', {
          name: pendingToggle?.display_name ?? '',
          target: pendingToggle?.is_super_admin
            ? t('admin.revoke')
            : t('admin.grant'),
        })}
        destructive={pendingToggle?.is_super_admin}
        loading={toggling}
        onConfirm={handleConfirmToggle}
        onCancel={() => setPendingToggle(null)}
      />
    </div>
  )
}
