// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Detail view: shows task metadata, markdown report (when done),
// and lets the user download a PDF or copy the markdown source.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, Copy, Download } from 'lucide-react'
import { api } from '@/lib/api'
import { GlassCard } from '@/components/GlassCard'
import type { SimulationTaskSummary, TaskStatus } from '@/types/api'

function statusClass(status: TaskStatus): string {
  return status === 'done'
    ? 'wx-pill-success'
    : status === 'failed'
      ? 'wx-pill-danger'
      : status === 'running'
        ? 'wx-pill-info'
        : 'wx-pill-warning'
}

export function ReportDetailPage() {
  const { t, i18n } = useTranslation()
  const { slug, taskId } = useParams<{ slug: string; taskId: string }>()
  const nav = useNavigate()
  const [task, setTask] = useState<SimulationTaskSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!taskId) return
    let cancelled = false
    setLoading(true)
    api
      .get<SimulationTaskSummary>(`/simulations/${taskId}`)
      .then((r) => !cancelled && setTask(r.data))
      .catch(() => !cancelled && toast.error(t('common.error')))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [taskId, t])

  function fmtDate(iso: string | null): string {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN',
      )
    } catch {
      return iso
    }
  }

  async function downloadPdf() {
    if (!task) return
    setDownloading(true)
    try {
      const res = await api.post(
        '/reports/pdf',
        { task_id: task.task_id },
        { responseType: 'blob' },
      )
      const blob = new Blob([res.data as BlobPart], {
        type: 'application/pdf',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${task.task_id.slice(0, 8)}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(t('reports.pdf_failed'))
    } finally {
      setDownloading(false)
    }
  }

  async function copyMarkdown() {
    const md = task?.result?.markdown
    if (!md) return
    try {
      await navigator.clipboard.writeText(md)
      toast.success(t('api_keys.copied'))
    } catch {
      toast.error(t('common.error'))
    }
  }

  return (
    <div style={{ padding: '28px 36px', maxWidth: 980, margin: '0 auto' }}>
      <button
        type="button"
        className="wx-btn-ghost text-sm"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 16,
        }}
        onClick={() => nav(`/w/${slug}/reports`)}
      >
        <ArrowLeft size={14} />
        {t('reports.detail_back')}
      </button>
      {loading ? (
        <GlassCard>{t('common.loading')}</GlassCard>
      ) : !task ? (
        <GlassCard>{t('reports.not_found')}</GlassCard>
      ) : (
        <>
          <div className="wx-page-header">
            <div>
              <h1 className="wx-page-title">
                {t('reports.detail_title')}
              </h1>
              <p className="wx-page-subtitle">
                <code style={{ marginRight: 8 }}>{task.task_id}</code>
                <span className={`wx-pill ${statusClass(task.status)}`}>
                  {t(`reports.status_${task.status}`)}
                </span>
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                className="wx-btn-ghost text-sm"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                }}
                onClick={copyMarkdown}
                disabled={!task.result?.markdown}
              >
                <Copy size={14} />
                {t('reports.copy_markdown')}
              </button>
              <button
                type="button"
                className="wx-btn-primary text-sm"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                }}
                onClick={downloadPdf}
                disabled={downloading || task.status !== 'done'}
              >
                <Download size={14} />
                {downloading
                  ? t('common.loading')
                  : t('reports.download_pdf')}
              </button>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 12,
              marginBottom: 18,
            }}
          >
            <div className="wx-stat-card">
              <div className="wx-stat-label">
                {t('reports.col_created')}
              </div>
              <div className="wx-stat-sub">
                {fmtDate(task.created_at)}
              </div>
            </div>
            <div className="wx-stat-card">
              <div className="wx-stat-label">
                {t('reports.col_finished')}
              </div>
              <div className="wx-stat-sub">
                {fmtDate(task.finished_at)}
              </div>
            </div>
            {task.result && (
              <>
                <div className="wx-stat-card">
                  <div className="wx-stat-label">
                    {t('reports.col_n_valid')}
                  </div>
                  <div className="wx-stat-value">
                    {task.result.n_valid}
                    <span
                      className="text-sm"
                      style={{
                        color: 'var(--wx-text-tertiary)',
                        fontWeight: 400,
                      }}
                    >
                      {' '}
                      / {task.result.n_total}
                    </span>
                  </div>
                </div>
                <div className="wx-stat-card">
                  <div className="wx-stat-label">
                    {t('reports.col_kind')}
                  </div>
                  <div className="wx-stat-sub">
                    {task.result.decision_kind}
                  </div>
                </div>
              </>
            )}
          </div>

          {task.status === 'failed' && task.error && (
            <GlassCard className="mb-4">
              <div
                className="text-sm"
                style={{ color: 'var(--wx-danger)' }}
              >
                {task.error}
              </div>
            </GlassCard>
          )}

          {task.result?.markdown ? (
            <GlassCard>
              <div className="wx-m-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {task.result.markdown}
                </ReactMarkdown>
              </div>
            </GlassCard>
          ) : (
            task.status === 'done' && (
              <GlassCard>
                <p
                  className="text-sm"
                  style={{ color: 'var(--wx-text-secondary)' }}
                >
                  {t('reports.no_markdown')}
                </p>
              </GlassCard>
            )
          )}
        </>
      )}
    </div>
  )
}
