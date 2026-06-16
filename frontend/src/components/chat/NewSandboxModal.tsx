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

const DEFAULT_DIST =
  'wanxiang/datasources/distributions/cn_z_generation_v1.yaml'
const DEFAULT_EMOJIS = ['🥤', '👗', '🍔', '🎮', '📱', '🚗', '🏠', '✨']
const DISTRIBUTIONS = [
  { value: DEFAULT_DIST, labelZh: '中国 Z 世代 v1', labelEn: 'CN Gen-Z v1' },
]

export function NewSandboxModal({
  isOpen,
  defaultDistribution = DEFAULT_DIST,
  onClose,
  onSubmit,
  submitting = false,
}: Props) {
  const { t, i18n } = useTranslation()
  const [name, setName] = useState('')
  const [emoji, setEmoji] = useState('🥤')
  const [description, setDescription] = useState('')
  const [populationSize, setPopulationSize] = useState(1000)
  const [distributionPath, setDistributionPath] = useState(defaultDistribution)

  if (!isOpen) return null

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    await onSubmit({
      name: trimmed,
      emoji: emoji || '🥤',
      description: description.trim(),
      population_size: populationSize,
      distribution_path: distributionPath,
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
          <label className="wx-label">{t('sandbox.emoji_label')}</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {DEFAULT_EMOJIS.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => setEmoji(e)}
                aria-label={`emoji ${e}`}
                style={{
                  width: 36, height: 36, borderRadius: 9,
                  background: emoji === e
                    ? 'rgba(27, 77, 255, 0.25)'
                    : 'rgba(255,255,255,0.05)',
                  border: emoji === e
                    ? '1px solid var(--wx-accent-cyan)'
                    : '1px solid var(--wx-glass-border)',
                  cursor: 'pointer', fontSize: 18,
                }}
              >{e}</button>
            ))}
          </div>
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

        <div style={{ marginBottom: 12 }}>
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

        <div style={{ marginBottom: 18 }}>
          <label className="wx-label">{t('sandbox.distribution_label')}</label>
          <select
            className="wx-input"
            value={distributionPath}
            onChange={(e) => setDistributionPath(e.target.value)}
          >
            {DISTRIBUTIONS.map((d) => (
              <option key={d.value} value={d.value}>
                {i18n.language === 'en' ? d.labelEn : d.labelZh}
              </option>
            ))}
          </select>
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
