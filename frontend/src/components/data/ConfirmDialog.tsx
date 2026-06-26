// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useTranslation } from 'react-i18next'
import { Modal } from './Modal'

interface Props {
  isOpen: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  loading?: boolean
  onConfirm: () => void | Promise<void>
  onCancel: () => void
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel,
  cancelLabel,
  destructive = false,
  loading = false,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useTranslation()
  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title}>
      <p
        className="text-sm"
        style={{ color: 'var(--wx-text-secondary)', marginBottom: 18 }}
      >
        {message}
      </p>
      <div
        style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}
      >
        <button
          type="button"
          className="wx-btn-ghost"
          onClick={onCancel}
          disabled={loading}
        >
          {cancelLabel ?? t('common.cancel')}
        </button>
        <button
          type="button"
          className="wx-btn-primary"
          style={
            destructive
              ? {
                  background:
                    'linear-gradient(135deg, #FF4D6E, #C026A8)',
                  boxShadow: '0 12px 32px -8px rgba(255, 77, 110, 0.4)',
                }
              : undefined
          }
          onClick={() => void onConfirm()}
          disabled={loading}
        >
          {loading
            ? t('common.loading')
            : confirmLabel ?? t('common.confirm')}
        </button>
      </div>
    </Modal>
  )
}
