// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Billing dashboard: balance, MTD usage, lifetime spend, mode breakdown,
// and a transactions table with kind filter.
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Plus } from 'lucide-react'
import { api } from '@/lib/api'
import { StatCard } from '@/components/data/StatCard'
import { DataTable, type Column } from '@/components/data/DataTable'
import { Modal } from '@/components/data/Modal'
import { Select } from '@/components/forms/Select'
import { GlassCard } from '@/components/GlassCard'
import { useAuthStore } from '@/stores/authStore'
import type {
  Transaction,
  TxKind,
  UsageMonthly,
  WorkspaceBalance,
} from '@/types/api'

export function formatCostUnits(units: number, locale: string): string {
  const sign = units < 0 ? '-' : ''
  const abs = Math.abs(units)
  const txt = abs.toLocaleString(locale === 'en' ? 'en-US' : 'zh-CN')
  return `${sign}${txt}`
}

const KIND_OPTIONS: { value: string; key: string }[] = [
  { value: '', key: 'billing.kind_all' },
  { value: 'topup', key: 'billing.kind_topup' },
  { value: 'usage', key: 'billing.kind_usage' },
  { value: 'refund', key: 'billing.kind_refund' },
  { value: 'adjust', key: 'billing.kind_adjust' },
]

function ModeBreakdown({ byMode }: { byMode: Record<string, number> }) {
  const { t } = useTranslation()
  const entries = Object.entries(byMode)
  const total = entries.reduce((sum, [, v]) => sum + v, 0)
  if (entries.length === 0) {
    return (
      <p
        className="text-sm"
        style={{ color: 'var(--wx-text-tertiary)' }}
      >
        {t('billing.no_usage_this_month')}
      </p>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {entries.map(([mode, units]) => {
        const pct = total > 0 ? Math.round((units / total) * 100) : 0
        return (
          <div key={mode}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 4,
                fontSize: 13,
              }}
            >
              <span style={{ color: 'var(--wx-text-primary)' }}>
                {mode}
              </span>
              <span
                style={{ color: 'var(--wx-text-secondary)', fontSize: 12 }}
              >
                {units.toLocaleString()} · {pct}%
              </span>
            </div>
            <div
              style={{
                height: 6,
                borderRadius: 4,
                background: 'rgba(120, 145, 220, 0.12)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: 'var(--wx-grad-blue)',
                  transition: 'width .3s',
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function BillingPage() {
  const { t, i18n } = useTranslation()
  const { slug } = useParams<{ slug: string }>()
  const setWorkspaces = useAuthStore((s) => s.setWorkspaces)
  const workspaces = useAuthStore((s) => s.workspaces)

  const [balance, setBalance] = useState<WorkspaceBalance | null>(null)
  const [usage, setUsage] = useState<UsageMonthly | null>(null)
  const [txs, setTxs] = useState<Transaction[]>([])
  const [kind, setKind] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [topupOpen, setTopupOpen] = useState(false)

  const lifetimeSpend = useMemo(
    () => txs.filter((t) => t.kind === 'usage').reduce((s, t) => s + Math.abs(t.delta_cost_units), 0),
    [txs],
  )

  useEffect(() => {
    if (!slug) return
    let cancelled = false
    setLoading(true)
    Promise.all([
      api.get<WorkspaceBalance>(`/workspaces/${slug}/balance`),
      api.get<UsageMonthly>(`/usage/current`),
      api.get<{ transactions: Transaction[] }>(
        `/workspaces/${slug}/transactions`,
        { params: kind ? { kind, limit: 200 } : { limit: 200 } },
      ),
    ])
      .then(([b, u, tx]) => {
        if (cancelled) return
        setBalance(b.data)
        setUsage(u.data)
        setTxs(tx.data.transactions ?? [])
        // Sync auth store so the sidebar shows the latest balance.
        const updated = workspaces.map((w) =>
          w.slug === slug
            ? { ...w, balance_cost_units: b.data.balance_cost_units }
            : w,
        )
        setWorkspaces(updated)
      })
      .catch(() => !cancelled && toast.error(t('common.error')))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, kind])

  function fmtDate(iso: string): string {
    try {
      return new Date(iso).toLocaleString(
        i18n.language === 'en' ? 'en-US' : 'zh-CN',
      )
    } catch {
      return iso
    }
  }

  function kindLabel(k: TxKind): string {
    return t(`billing.kind_${k}`)
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
      key: 'created_at',
      header: t('billing.col_when'),
      accessor: (r) => r.created_at,
      sortable: true,
      render: (r) => fmtDate(r.created_at),
      width: '170px',
    },
    {
      key: 'kind',
      header: t('billing.txn_kind'),
      render: (r) => (
        <span className={`wx-pill ${kindClass(r.kind)}`}>
          {kindLabel(r.kind)}
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
          {formatCostUnits(r.delta_cost_units, i18n.language)}
        </span>
      ),
      width: '120px',
    },
    {
      key: 'balance_after',
      header: t('billing.txn_balance_after'),
      accessor: (r) => r.balance_after,
      render: (r) => formatCostUnits(r.balance_after, i18n.language),
      align: 'right',
      width: '140px',
    },
    {
      key: 'note',
      header: t('billing.txn_note'),
      render: (r) => (
        <span
          style={{
            color: 'var(--wx-text-secondary)',
            fontSize: 12.5,
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
          <h1 className="wx-page-title">{t('billing.title')}</h1>
          <p className="wx-page-subtitle">{t('billing.subtitle')}</p>
        </div>
        <button
          type="button"
          className="wx-btn-primary text-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          onClick={() => setTopupOpen(true)}
        >
          <Plus size={14} />
          {t('billing.request_topup')}
        </button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 14,
          marginBottom: 18,
        }}
      >
        <StatCard
          label={t('billing.balance')}
          value={
            loading
              ? '—'
              : formatCostUnits(
                  balance?.balance_cost_units ?? 0,
                  i18n.language,
                )
          }
          sub={t('workspaces.units', {
            n: balance?.balance_cost_units ?? 0,
          })}
          accent="blue"
        />
        <StatCard
          label={t('billing.usage_mtd')}
          value={
            loading
              ? '—'
              : formatCostUnits(
                  usage?.total_cost_units ?? 0,
                  i18n.language,
                )
          }
          sub={t('billing.usage_mtd_sub')}
          accent="cyan"
        />
        <StatCard
          label={t('billing.lifetime_spend')}
          value={formatCostUnits(lifetimeSpend, i18n.language)}
          sub={t('billing.lifetime_spend_sub')}
          accent="orange"
        />
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1.2fr',
          gap: 14,
          marginBottom: 18,
        }}
      >
        <GlassCard>
          <div className="wx-stat-label" style={{ marginBottom: 12 }}>
            {t('billing.mode_breakdown')}
          </div>
          {usage ? (
            <ModeBreakdown byMode={usage.by_mode} />
          ) : (
            <p
              className="text-sm"
              style={{ color: 'var(--wx-text-tertiary)' }}
            >
              {t('common.loading')}
            </p>
          )}
        </GlassCard>
        <GlassCard>
          <div className="wx-stat-label" style={{ marginBottom: 12 }}>
            {t('billing.monthly_budget')}
          </div>
          <div
            className="wx-stat-value"
            style={{ marginBottom: 6 }}
          >
            {balance?.monthly_budget != null
              ? formatCostUnits(balance.monthly_budget, i18n.language)
              : '∞'}
          </div>
          <div
            className="text-xs"
            style={{ color: 'var(--wx-text-secondary)' }}
          >
            {t('billing.budget_hint')}
          </div>
        </GlassCard>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            fontWeight: 600,
            margin: 0,
          }}
        >
          {t('billing.txn_history')}
        </h2>
        <div style={{ width: 180 }}>
          <Select
            value={kind}
            ariaLabel={t('billing.filter_kind')}
            options={KIND_OPTIONS.map((o) => ({
              value: o.value,
              label: t(o.key),
            }))}
            onChange={setKind}
          />
        </div>
      </div>
      <DataTable
        columns={columns}
        rows={txs}
        rowKey={(r) => r.tx_id}
        loading={loading}
        emptyMessage={t('billing.no_transactions')}
      />

      <Modal
        isOpen={topupOpen}
        onClose={() => setTopupOpen(false)}
        title={t('billing.request_topup')}
      >
        <p
          className="text-sm"
          style={{ color: 'var(--wx-text-secondary)', marginBottom: 8 }}
        >
          {t('billing.topup_contact')}
        </p>
        <div className="wx-code-block">support@wanxiang.ai</div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
          <button
            type="button"
            className="wx-btn-primary"
            onClick={() => setTopupOpen(false)}
          >
            {t('common.ok')}
          </button>
        </div>
      </Modal>
    </div>
  )
}
