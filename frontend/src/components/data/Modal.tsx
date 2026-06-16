// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Generic glass modal used across P7 dashboards.
import { useEffect, type ReactNode } from 'react'
import { X } from 'lucide-react'

interface Props {
  isOpen: boolean
  onClose: () => void
  title?: ReactNode
  children: ReactNode
  size?: 'sm' | 'lg'
  closeOnBackdrop?: boolean
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'sm',
  closeOnBackdrop = true,
}: Props) {
  useEffect(() => {
    if (!isOpen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, onClose])

  if (!isOpen) return null
  return (
    <div
      className="wx-modal-backdrop"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) onClose()
      }}
    >
      <div className={`wx-modal ${size === 'lg' ? 'wx-modal-lg' : ''}`}>
        {title && (
          <div
            className="flex items-center justify-between mb-4"
            style={{ gap: 12 }}
          >
            <h2 style={{ margin: 0 }}>{title}</h2>
            <button
              type="button"
              className="wx-icon-btn"
              onClick={onClose}
              aria-label="close"
            >
              <X size={16} />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}
