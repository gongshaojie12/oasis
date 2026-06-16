// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Wallet } from 'lucide-react'
import { api } from '@/lib/api'
import { DataTable, type Column } from '@/components/data/DataTable'
import { Modal } from '@/components/data/Modal'
import { FormField } from '@/components/forms/FormField'
import type { AdminWorkspace } from '@/types/api'

export function AdminWorkspacesPage() {
  const { t, i18n } = useTranslation()
  const [rows, setRows] = useState<AdminWorkspace[]>([])
  const [loading, setLoading] = useState(true)
  const [topupTarget, setTopupTarget] = useState<AdminWorkspace | null>(null)
  const [amount, setAmount] = useState(1000)
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const r = await api.get<{ workspaces: AdminWorkspace[] }>(
        '/admin/workspaces',
        { params: { limit: 500 } },
      )
      setRows(r.data.workspaces ?? [])
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

  async function handleTopup(e: FormEvent) {
    e.preventDefault()
    if (!topupTarget) return
    setSubmitting(true)
    try {
      await api.post('/admin/topup', {
        workspace_id: topupTarget.workspace_id,
        amount,
        note,
      })
      toast.success(t('admin.topup_success'))
      setTopupTarget(null)
      setAmount(1000)
      setNote('')
      await load()
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e.response?.data?.detail ?? t('common.error'))
    } finally {
      setSubmitting(false)
    }
  }

  const columns: Column<AdminWorkspace>[] = [
    {
      key: 'name',
      header: t('admin.col_workspace'),
      render: (w) => (
        <div style={{ lineHeight: 1.3 }}>
          <div style={{ fontWeight: 600 }}>{w.name}</div>
          <div
            className="text-xs"
            style={{ color: 'var(--wx-text-tertiary)' }}
          >
            {w.slug}
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: t('admin.col_type'),
      render: (w) => (
        <span
          className={`wx-pill ${w.type === 'team' ? 'wx-pill-info' : ''}`}
        >
          {t(`onboarding.${w.type}`)}
        </span>
      ),
      width: '110px',
    },
    {
      key: 'balance',
      header: t('admin.col_balance'),
      accessor: (w) => w.balance_cost_units,
      sortable: true,
      align: 'right',
      render: (w) => (
        <span
          style={{
            color:
              w.balance_cost_units <= 0
                ? 'var(--wx-warning)'
                : 'var(--wx-text-primary)',
            fontWeight: 600,
          }}
        >
          {w.balance_cost_units.toLocaleString()}
        </span>
      ),
      width: '130px',
    },
    {
      key: 'budget',
      header: t('admin.col_budget'),
      accessor: (w) => w.monthly_budget ?? -1,
      render: (w) =>
        w.monthly_budget != null
          ? w.monthly_budget.toLocaleString()
          : '∞',
      align: 'right',
      width: '110px',
    },
    {
      key: 'created',
      header: t('admin.col_created'),
      accessor: (w) => w.created_at ?? '',
      render: (w) => fmtDate(w.created_at),
      width: '130px',
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '110px',
      render: (w) => (
        <button
          type="button"
          className="wx-btn-ghost text-xs"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
          }}
          onClick={(e) => {
            e.stopPropagation()
            setTopupTarget(w)
          }}
        >
          <Wallet size={12} />
          {t('admin.topup')}
        </button>
      ),
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('admin.workspaces')}</h1>
          <p className="wx-page-subtitle">
            {t('admin.workspaces_subtitle')}
          </p>
        </div>
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(w) => w.workspace_id}
        loading={loading}
        emptyMessage={t('admin.no_workspaces')}
      />
      <Modal
        isOpen={topupTarget !== null}
        onClose={() => setTopupTarget(null)}
        title={t('admin.topup_modal_title')}
      >
        <form onSubmit={handleTopup}>
          <p
            className="text-sm"
            style={{
              color: 'var(--wx-text-secondary)',
              marginBottom: 14,
            }}
          >
            {topupTarget?.name} ({topupTarget?.slug})
          </p>
          <FormField label={t('admin.topup_amount')}>
            <input
              type="number"
              className="wx-input"
              value={amount}
              min={1}
              max={10000000}
              required
              onChange={(e) => setAmount(Number(e.target.value) || 0)}
            />
          </FormField>
          <FormField label={t('admin.topup_note')}>
            <input
              className="wx-input"
              value={note}
              maxLength={200}
              onChange={(e) => setNote(e.target.value)}
            />
          </FormField>
          <div
            style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}
          >
            <button
              type="button"
              className="wx-btn-ghost"
              onClick={() => setTopupTarget(null)}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="wx-btn-primary"
              disabled={submitting || amount <= 0}
            >
              {submitting ? t('common.loading') : t('common.submit')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
