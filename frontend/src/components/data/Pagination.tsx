// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface Props {
  page: number
  pageSize: number
  hasMore: boolean
  onPageChange: (page: number) => void
}

export function Pagination({ page, pageSize, hasMore, onPageChange }: Props) {
  const { t } = useTranslation()
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '12px 4px',
      }}
    >
      <button
        type="button"
        className="wx-btn-ghost text-sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="previous page"
      >
        <ChevronLeft size={14} />
      </button>
      <span
        className="text-xs"
        style={{ color: 'var(--wx-text-secondary)' }}
      >
        {t('common.page', { n: page, size: pageSize })}
      </span>
      <button
        type="button"
        className="wx-btn-ghost text-sm"
        disabled={!hasMore}
        onClick={() => onPageChange(page + 1)}
        aria-label="next page"
      >
        <ChevronRight size={14} />
      </button>
    </div>
  )
}
