// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Reusable Reports list view — used by both /w/:slug/reports route AND
// LandingPage's in-page view when activeView === 'reports'.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { DataTable, type Column } from '@/components/data/DataTable'
import type { SimulationTaskSummary, TaskStatus } from '@/types/api'

function StatusPill({ status }: { status: TaskStatus }) {
  const { t } = useTranslation()
  const cls =
    status === 'done'
      ? 'wx-pill-success'
      : status === 'failed'
        ? 'wx-pill-danger'
        : status === 'running'
          ? 'wx-pill-info'
          : 'wx-pill-warning'
  return (
    <span className={`wx-pill ${cls}`}>{t(`reports.status_${status}`)}</span>
  )
}

export function ReportsView({ slug }: { slug: string }) {
  const { t, i18n } = useTranslation()
  const nav = useNavigate()
  const [rows, setRows] = useState<SimulationTaskSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .get<SimulationTaskSummary[]>('/simulations', { params: { limit: 100 } })
      .then((r) => {
        if (cancelled) return
        setRows(Array.isArray(r.data) ? r.data : [])
      })
      .catch(() => !cancelled && toast.error(t('common.error')))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [t])

  function fmtDate(iso: string): string {
    try {
      return new Date(iso).toLocaleString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN',
      )
    } catch {
      return iso
    }
  }

  const columns: Column<SimulationTaskSummary>[] = [
    {
      key: 'created_at',
      header: t('reports.col_created'),
      accessor: (r) => r.created_at,
      sortable: true,
      render: (r) => fmtDate(r.created_at),
      width: '180px',
    },
    {
      key: 'kind',
      header: t('reports.col_kind'),
      accessor: (r) => r.result?.decision_kind ?? '—',
      render: (r) => r.result?.decision_kind ?? '—',
      width: '120px',
    },
    {
      key: 'status',
      header: t('reports.col_status'),
      render: (r) => <StatusPill status={r.status} />,
      width: '110px',
    },
    {
      key: 'n_valid',
      header: t('reports.col_n_valid'),
      render: (r) =>
        r.result
          ? `${r.result.n_valid}/${r.result.n_total}`
          : '—',
      align: 'right',
      width: '110px',
    },
    {
      key: 'mean',
      header: t('reports.col_mean'),
      accessor: (r) => r.result?.mean ?? null,
      render: (r) =>
        typeof r.result?.mean === 'number'
          ? r.result.mean.toFixed(2)
          : '—',
      align: 'right',
      sortable: true,
      width: '90px',
    },
    {
      key: 'task_id',
      header: t('reports.col_task_id'),
      render: (r) => (
        <code style={{ fontSize: 11, color: 'var(--wx-text-tertiary)' }}>
          {r.task_id.slice(0, 8)}…
        </code>
      ),
      width: '120px',
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header">
        <div>
          <h1 className="wx-page-title">{t('reports.title')}</h1>
          <p className="wx-page-subtitle">{t('reports.subtitle')}</p>
        </div>
        <button
          type="button"
          className="wx-btn-primary text-sm"
          onClick={() => nav(`/w/${slug}`)}
        >
          {t('reports.go_run_one')}
        </button>
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.task_id}
        loading={loading}
        emptyMessage={
          <div>
            <p>{t('reports.empty')}</p>
            <button
              type="button"
              className="wx-btn-primary text-sm"
              style={{ marginTop: 10 }}
              onClick={() => nav(`/w/${slug}`)}
            >
              {t('reports.go_run_one')}
            </button>
          </div>
        }
        onRowClick={(r) => nav(`/w/${slug}/reports/${r.task_id}`)}
      />
    </div>
  )
}
