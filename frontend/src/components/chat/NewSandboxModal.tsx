// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Modal to create a new sandbox.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

interface Props {
  isOpen: boolean
  defaultDistribution?: string
  onClose: () => void
  onSubmit: (payload: {
    name: string
    emoji: string
    description: string
    population_size: number
    distribution_path: string
  }) => Promise<void> | void
  submitting?: boolean
}

// 人群画像不再让用户在建沙盒时选择——内置联合分布画像即唯一真相源,
// 静默使用其 slug(后端 resolve_distribution 认 slug)。图标也固定默认值。
const DEFAULT_DIST = 'cn_national_joint_2020'
const DEFAULT_EMOJI = '🥤'

export function NewSandboxModal({
  isOpen,
  defaultDistribution = DEFAULT_DIST,
  onClose,
  onSubmit,
  submitting = false,
}: Props) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [populationSize, setPopulationSize] = useState(1000)

  if (!isOpen) return null

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    await onSubmit({
      name: trimmed,
      emoji: DEFAULT_EMOJI,
      description: description.trim(),
      population_size: populationSize,
      distribution_path: defaultDistribution,
    })
    setName('')
    setDescription('')
  }

  return (
    <div className="wx-modal-backdrop" role="dialog" aria-modal="true"
         onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <form className="wx-modal" onSubmit={handleSubmit}>
        <h2>{t('sandbox.create')}</h2>

        <div style={{ marginBottom: 12 }}>
          <label className="wx-label">{t('sandbox.name_label')}</label>
          <input
            className="wx-input"
            value={name}
            maxLength={64}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            placeholder={t('sandbox.name_placeholder')}
          />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label className="wx-label">{t('sandbox.description_label')}</label>
          <input
            className="wx-input"
            value={description}
            maxLength={200}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div style={{ marginBottom: 18 }}>
          <label className="wx-label">
            {t('sandbox.population_label')}
          </label>
          <input
            type="number"
            className="wx-input"
            value={populationSize}
            min={10}
            max={1000000}
            onChange={(e) => setPopulationSize(Number(e.target.value) || 1000)}
          />
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button type="button" className="wx-btn-ghost" onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            className="wx-btn-primary"
            disabled={submitting || !name.trim()}
          >
            {submitting ? t('common.loading') : t('sandbox.create')}
          </button>
        </div>
      </form>
    </div>
  )
}
