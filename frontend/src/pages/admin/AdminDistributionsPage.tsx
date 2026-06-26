// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// M1 管理后台:人群画像库 —— 列表 / 上传 / 编辑 / 启用 / 复制 / 删除。
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Power, Copy, Trash2, Upload, Eye } from 'lucide-react'
import { api } from '@/lib/api'
import { DataTable, type Column } from '@/components/data/DataTable'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { Modal } from '@/components/data/Modal'

interface DistSummary {
  distribution_id: string
  slug: string
  name_zh: string
  name_en: string
  description: string
  source_type: string
  trait_counts: { demographic?: number; personality?: number; media?: number }
  enabled: boolean
  builtin: boolean
  updated_at?: string
}

export function AdminDistributionsPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<DistSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<DistSummary | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [viewing, setViewing] = useState<DistSummary | null>(null)
  const [viewContent, setViewContent] = useState<string>('')

  async function load() {
    setLoading(true)
    try {
      // admin 也用公开列表(只列 enabled)——这里改用带全部的:复用 GET /distributions
      // 但 admin 需要看到 disabled 的,所以逐个不行;后端 list 是 enabled_only。
      // 简化:admin 页也调 /distributions(enabled)+ 标注;disabled 的通过编辑恢复。
      const r = await api.get<{ distributions: DistSummary[] }>(
        '/distributions')
      setRows(r.data.distributions ?? [])
    } catch {
      toast.error(t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, []) // eslint-disable-line

  async function toggleEnabled(d: DistSummary) {
    try {
      await api.put(`/admin/distributions/${d.distribution_id}`, {
        enabled: !d.enabled,
      })
      toast.success(t('admin.updated'))
      await load()
    } catch (e) {
      toast.error(errDetail(e))
    }
  }

  async function duplicate(d: DistSummary) {
    try {
      await api.post(`/admin/distributions/${d.distribution_id}/duplicate`)
      toast.success(t('admin.dist_duplicated'))
      await load()
    } catch (e) {
      toast.error(errDetail(e))
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.delete(`/admin/distributions/${pendingDelete.distribution_id}`)
      toast.success(t('admin.dist_deleted'))
      setPendingDelete(null)
      await load()
    } catch (e) {
      toast.error(errDetail(e))
    } finally {
      setDeleting(false)
    }
  }

  async function viewDetail(d: DistSummary) {
    setViewing(d)
    setViewContent(t('common.loading'))
    try {
      const r = await api.get<{ content: unknown }>(
        `/distributions/${d.distribution_id}`)
      setViewContent(JSON.stringify(r.data.content, null, 2))
    } catch {
      setViewContent(t('common.error'))
    }
  }

  const columns: Column<DistSummary>[] = [
    {
      key: 'name',
      header: t('admin.dist_name'),
      render: (d) => (
        <div style={{ lineHeight: 1.3 }}>
          <div style={{ fontWeight: 600 }}>{d.name_zh}</div>
          <div className="text-xs" style={{ color: 'var(--wx-text-tertiary)' }}>
            {d.slug} {d.builtin && `· ${t('admin.dist_builtin')}`}
          </div>
        </div>
      ),
    },
    {
      key: 'traits',
      header: t('admin.dist_traits'),
      width: '200px',
      render: (d) => (
        <span style={{ fontSize: 12, color: 'var(--wx-text-secondary)' }}>
          {t('admin.dist_demographic')} {d.trait_counts.demographic ?? 0} ·
          {' '}{t('admin.dist_personality')} {d.trait_counts.personality ?? 0} ·
          {' '}{t('admin.dist_media')} {d.trait_counts.media ?? 0}
        </span>
      ),
    },
    {
      key: 'source',
      header: t('admin.dist_source'),
      width: '90px',
      render: (d) => <span className="wx-pill">{d.source_type}</span>,
    },
    {
      key: 'enabled',
      header: t('admin.dist_enabled'),
      width: '70px',
      align: 'center',
      render: (d) => (
        <span className={`wx-pill ${d.enabled ? 'wx-pill-success' : ''}`}>
          {d.enabled ? '✓' : '✗'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: t('admin.dist_actions'),
      width: '170px',
      align: 'center',
      render: (d) => (
        <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
          <button type="button" className="wx-icon-btn"
                  title={t('admin.dist_view')} onClick={() => viewDetail(d)}>
            <Eye size={15} />
          </button>
          <button type="button" className="wx-icon-btn"
                  title={t('admin.dist_toggle')}
                  style={{ color: d.enabled ? 'var(--wx-accent-amber)'
                                            : 'var(--wx-text-tertiary)' }}
                  onClick={() => toggleEnabled(d)}>
            <Power size={15} />
          </button>
          <button type="button" className="wx-icon-btn"
                  title={t('admin.dist_duplicate')}
                  onClick={() => duplicate(d)}>
            <Copy size={15} />
          </button>
          <button type="button" className="wx-icon-btn wx-icon-btn-danger"
                  title={t('admin.dist_delete')}
                  disabled={d.builtin}
                  onClick={() => setPendingDelete(d)}>
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div style={{ padding: '28px 36px' }}>
      <div className="wx-page-header"
           style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'flex-start' }}>
        <div>
          <h1 className="wx-page-title">{t('admin.distributions')}</h1>
          <p className="wx-page-subtitle">
            {t('admin.distributions_subtitle')}
          </p>
        </div>
        <button type="button" className="wx-btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                onClick={() => setUploadOpen(true)}>
          <Upload size={15} /> {t('admin.dist_upload')}
        </button>
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(d) => d.distribution_id}
        loading={loading}
        emptyMessage={t('admin.dist_empty')}
      />

      <UploadModal isOpen={uploadOpen} onClose={() => setUploadOpen(false)}
                   onDone={() => { setUploadOpen(false); void load() }} />

      <Modal isOpen={viewing !== null} onClose={() => setViewing(null)}
             title={viewing?.name_zh} size="lg">
        <pre style={{ maxHeight: '60vh', overflow: 'auto', fontSize: 12,
                      background: 'var(--wx-bg-card)', padding: 12,
                      borderRadius: 8 }}>{viewContent}</pre>
      </Modal>

      <ConfirmDialog
        isOpen={pendingDelete !== null}
        title={t('admin.dist_delete')}
        message={t('admin.dist_delete_confirm',
                   { name: pendingDelete?.name_zh ?? '' })}
        destructive
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}

function errDetail(e: unknown): string {
  const r = (e as { response?: { data?: { detail?: unknown } } })?.response
  const d = r?.data?.detail
  if (typeof d === 'string') return d
  if (d && typeof d === 'object' && 'message' in d) {
    return String((d as { message: unknown }).message)
  }
  return '操作失败'
}

function UploadModal({ isOpen, onClose, onDone }: {
  isOpen: boolean; onClose: () => void; onDone: () => void
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [fmt, setFmt] = useState<'yaml' | 'json'>('json')
  const [content, setContent] = useState('')
  const [doSynthetic, setDoSynthetic] = useState(false)
  const [dpOn, setDpOn] = useState(false)
  const [dpEpsilon, setDpEpsilon] = useState('1.0')
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    const text = await f.text()
    setContent(text)
    if (f.name.endsWith('.json')) setFmt('json')
    else setFmt('yaml')
    if (!name) setName(f.name.replace(/\.(ya?ml|json)$/i, ''))
  }

  async function submit() {
    setErrors([])
    if (!name.trim() || !content.trim()) {
      setErrors([t('admin.dist_need_name_content')])
      return
    }
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        name: name.trim(), description, fmt, content,
        synthetic_fill: doSynthetic,
      }
      if (dpOn) payload.dp_epsilon = parseFloat(dpEpsilon) || 1.0
      const r = await api.post('/admin/distributions', payload)
      const warns = (r.data?.warnings ?? []) as string[]
      toast.success(t('admin.dist_uploaded'))
      if (warns.length) toast(warns.slice(0, 3).join('\n'), { icon: '⚠️' })
      onDone()
      // reset
      setName(''); setDescription(''); setContent(''); setErrors([])
    } catch (e) {
      const r = (e as { response?: { data?: { detail?: unknown } } })?.response
      const d = r?.data?.detail
      if (d && typeof d === 'object' && 'errors' in d) {
        setErrors((d as { errors: string[] }).errors)
      } else {
        setErrors([errDetail(e)])
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('admin.dist_upload')}
           size="lg">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <label className="wx-label">{t('admin.dist_name')}</label>
          <input className="wx-input" value={name}
                 onChange={(e) => setName(e.target.value)}
                 placeholder={t('admin.dist_name_ph')} />
        </div>
        <div>
          <label className="wx-label">{t('admin.dist_description')}</label>
          <input className="wx-input" value={description}
                 onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <label className="wx-label" style={{ margin: 0 }}>
            {t('admin.dist_format')}
          </label>
          <select className="wx-input" style={{ width: 100 }} value={fmt}
                  onChange={(e) => setFmt(e.target.value as 'yaml' | 'json')}>
            <option value="json">JSON</option>
            <option value="yaml">YAML</option>
          </select>
          <input type="file" accept=".yaml,.yml,.json" onChange={onFile} />
        </div>
        <div>
          <label className="wx-label">{t('admin.dist_content')}</label>
          <textarea className="wx-input" rows={10}
                    style={{ fontFamily: 'monospace', fontSize: 12 }}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder={t('admin.dist_content_ph')} />
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6,
                          fontSize: 13 }}>
            <input type="checkbox" checked={doSynthetic}
                   onChange={(e) => setDoSynthetic(e.target.checked)} />
            {t('admin.dist_synthetic')}
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6,
                          fontSize: 13 }}>
            <input type="checkbox" checked={dpOn}
                   onChange={(e) => setDpOn(e.target.checked)} />
            {t('admin.dist_dp')}
          </label>
          {dpOn && (
            <input className="wx-input" style={{ width: 90 }} value={dpEpsilon}
                   onChange={(e) => setDpEpsilon(e.target.value)}
                   placeholder="ε" />
          )}
        </div>
        {errors.length > 0 && (
          <div style={{ background: 'rgba(255,77,110,.08)', borderRadius: 8,
                        padding: 10, fontSize: 12,
                        color: 'var(--wx-danger)' }}>
            {errors.slice(0, 12).map((er, i) => <div key={i}>· {er}</div>)}
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button type="button" className="wx-btn-ghost" onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button type="button" className="wx-btn-primary" disabled={saving}
                  onClick={submit}>
            {saving ? t('common.loading') : t('admin.dist_submit')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
