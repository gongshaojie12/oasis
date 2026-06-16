// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Download } from 'lucide-react'
import { api } from '@/lib/api'
import { DataTable, type Column } from '@/components/data/DataTable'
import { Select } from '@/components/forms/Select'
import type { AdminWorkspace, Transaction, TxKind } from '@/types/api'

const KIND_OPTIONS: { value: string; key: string }[] = [
  { value: '', key: 'billing.kind_all' },
  { value: 'topup', key: 'billing.kind_topup' },
  { value: 'usage', key: 'billing.kind_usage' },
  { value: 'refund', key: 'billing.kind_refund' },
  { value: 'adjust', key: 'billing.kind_adjust' },
]

function escapeCsv(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

export function AdminTransactionsPage() {
  const { t, i18n } = useTranslation()
  const [rows, setRows] = useState<Transaction[]>([])
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[]>([])
  const [loading, setLoading] = useState(true)
  const [wsFilter, setWsFilter] = useState('')
  const [kindFilter, setKindFilter] = useState('')

  useEffect(() => {
    api
      .get<{ workspaces: AdminWorkspace[] }>('/admin/workspaces', {
        params: { limit: 500 },
      })
      .then((r) => setWorkspaces(r.data.workspaces ?? []))
      .catch(() => {
        /* non-fatal */
      })
  }, [])

  useEffect(() => {
    setLoading(true)
    const params: Record<string, string | number> = { limit: 500 }
    if (wsFilter) params.workspace_id = wsFilter
    if (kindFilter) params.kind = kindFilter
    api
      .get<{ transactions: Transaction[] }>('/admin/transactions', { params })
      .then((r) => setRows(r.data.transactions ?? []))
      .catch(() => toast.error(t('common.error')))
      .finally(() => setLoading(false))
  }, [wsFilter, kindFilter, t])

  function fmtDate(iso: string): string {
    try {
      return new Date(iso).toLocaleString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN',
      )
    } catch {
      return iso
    }
  }

  function wsName(id: string): string {
    return workspaces.find((w) => w.workspace_id === id)?.name ?? id.slice(0, 8)
  }

  function exportCsv() {
    const headers = [
      'tx_id',
      'workspace',
      'kind',
      'delta',
      'balance_after',
      'note',
      'related_task_id',
      'created_at',
    ]
    const lines = [headers.join(',')]
    for (const r of rows) {
      lines.push(
        [
          r.tx_id,
          wsName(r.workspace_id),
          r.kind,
          String(r.delta_cost_units),
          String(r.balance_after),
          r.note,
          r.related_task_id ?? '',
          r.created_at,
        ]
          .map((v) => escapeCsv(String(v)))
          .join(','),
      )
    }
    const blob = new Blob([lines.join('\n')], {
      type: 'text/csv;charset=utf-8;',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `transactions-${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  function kindClass(k: TxKind): string {
    return k === 'topup'
      ? 'wx-pill-success'
      : k === 'usage'
        ? 'wx-pill-info'
        : k === 'refund'
          ? 'wx-pill-warning'
          : 'wx-pill'
  }

  const columns: Column<Transaction>[] = [
    {
      key: 'when',
      header: t('billing.col_when'),
      accessor: (r) => r.created_at,
      render: (r) => fmtDate(r.created_at),
      sortable: true,
      width: '180px',
    },
    {
      key: 'workspace',
      header: t('admin.col_workspace'),
      render: (r) => (
        <span style={{ fontSize: 12.5 }}>{wsName(r.workspace_id)}</span>
      ),
    },
    {
      key: 'kind',
      header: t('billing.txn_kind'),
      render: (r) => (
        <span className={`wx-pill ${kindClass(r.kind)}`}>
          {t(`billing.kind_${r.kind}`)}
        </span>
      ),
      width: '100px',
    },
    {
      key: 'delta',
      header: t('billing.txn_delta'),
      align: 'right',
      sortable: true,
      accessor: (r) => r.delta_cost_units,
      render: (r) => (
        <span
          style={{
            color:
              r.delta_cost_units >= 0
                ? 'var(--wx-success)'
                : 'var(--wx-text-primary)',
            fontWeight: 600,
          }}
        >
          {r.delta_cost_units >= 0 ? '+' : ''}
          {r.delta_cost_units.toLocaleString()}
        </span>
      ),
      width: '120px',
    },
    {
      key: 'balance_after',
      header: t('billing.txn_balance_after'),
      accessor: (r) => r.balance_after,
      render: (r) => r.balance_after.toLocaleString(),
      align: 'right',
      width: '130px',
    },
    {
      key: 'note',
      header: t('billing.txn_note'),
      render: (r) => (
        <span
          style={{
            fontSize: 12,
            color: 'var(--wx-text-secondary)',
          }}
        >
          {r.note || '—'}
        </span>
      ),
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('admin.transactions')}</h1>
          <p className="wx-page-subtitle">
            {t('admin.transactions_subtitle')}
          </p>
        </div>
        <button
          type="button"
          className="wx-btn-ghost text-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          onClick={exportCsv}
          disabled={rows.length === 0}
        >
          <Download size={14} />
          {t('admin.export_csv')}
        </button>
      </div>
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 14,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 240 }}>
          <Select
            value={wsFilter}
            ariaLabel={t('admin.filter_workspace')}
            options={[
              { value: '', label: t('admin.all_workspaces') },
              ...workspaces.map((w) => ({
                value: w.workspace_id,
                label: w.name,
              })),
            ]}
            onChange={setWsFilter}
          />
        </div>
        <div style={{ minWidth: 160 }}>
          <Select
            value={kindFilter}
            ariaLabel={t('billing.filter_kind')}
            options={KIND_OPTIONS.map((o) => ({
              value: o.value,
              label: t(o.key),
            }))}
            onChange={setKindFilter}
          />
        </div>
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.tx_id}
        loading={loading}
        emptyMessage={t('admin.no_transactions')}
      />
    </div>
  )
}
