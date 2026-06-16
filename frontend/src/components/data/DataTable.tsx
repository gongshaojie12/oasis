// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Minimal sortable/clickable table for P7 dashboards.
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronUp } from 'lucide-react'

export interface Column<T> {
  key: string
  header: ReactNode
  /** value getter used for sorting & default render */
  accessor?: (row: T) => string | number | null | undefined
  /** custom cell renderer (overrides accessor for display) */
  render?: (row: T) => ReactNode
  sortable?: boolean
  width?: string
  align?: 'left' | 'right' | 'center'
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  onRowClick?: (row: T) => void
  loading?: boolean
  emptyMessage?: ReactNode
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  loading,
  emptyMessage,
}: Props<T>) {
  const { t } = useTranslation()
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const sortable = columns.find((c) => c.key === sortKey)
  const sorted =
    sortable && sortable.accessor
      ? [...rows].sort((a, b) => {
          const av = sortable.accessor!(a)
          const bv = sortable.accessor!(b)
          if (av == null && bv == null) return 0
          if (av == null) return 1
          if (bv == null) return -1
          if (av < bv) return sortDir === 'asc' ? -1 : 1
          if (av > bv) return sortDir === 'asc' ? 1 : -1
          return 0
        })
      : rows

  function toggleSort(col: Column<T>) {
    if (!col.sortable || !col.accessor) return
    if (sortKey !== col.key) {
      setSortKey(col.key)
      setSortDir('desc')
    } else {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc')
    }
  }

  return (
    <div className="wx-glass" style={{ padding: 0, overflow: 'hidden' }}>
      <table className="wx-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{
                  width: c.width,
                  textAlign: c.align ?? 'left',
                  cursor: c.sortable ? 'pointer' : 'default',
                  userSelect: 'none',
                }}
                onClick={() => toggleSort(c)}
              >
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  {c.header}
                  {c.sortable && sortKey === c.key && (
                    sortDir === 'asc' ? (
                      <ChevronUp size={12} />
                    ) : (
                      <ChevronDown size={12} />
                    )
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td className="wx-td-empty" colSpan={columns.length}>
                {t('common.loading')}
              </td>
            </tr>
          ) : sorted.length === 0 ? (
            <tr>
              <td className="wx-td-empty" colSpan={columns.length}>
                {emptyMessage ?? t('common.empty')}
              </td>
            </tr>
          ) : (
            sorted.map((row) => (
              <tr
                key={rowKey(row)}
                style={onRowClick ? { cursor: 'pointer' } : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((c) => {
                  const cell = c.render
                    ? c.render(row)
                    : c.accessor
                      ? (c.accessor(row) as ReactNode)
                      : null
                  return (
                    <td
                      key={c.key}
                      style={{ textAlign: c.align ?? 'left' }}
                    >
                      {cell}
                    </td>
                  )
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
