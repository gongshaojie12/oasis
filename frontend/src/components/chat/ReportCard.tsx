// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Decision summary + collapsible markdown report. Matches chat.html .art-card.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage } from '@/types/api'

interface Props { msg: ChatMessage }

function formatMean(v: unknown): string | null {
  if (typeof v === 'number') return v.toFixed(2)
  return null
}

export function ReportCard({ msg }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const meta = msg.metadata ?? {}
  const decisionKind = String(meta.decision_kind ?? '')
  const nValid = typeof meta.n_valid === 'number' ? meta.n_valid : null
  const nTotal = typeof meta.n_total === 'number' ? meta.n_total : null
  const mean = formatMean(meta.mean)
  const topChoice =
    typeof meta.top_choice === 'string' ? meta.top_choice : null

  return (
    <div className="wx-art-card">
      <header>
        <span className="wx-art-title">{t('chat.report_title')}</span>
        <button
          type="button"
          className="wx-art-toggle"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? t('chat.report_collapse') : t('chat.report_expand')}
        </button>
      </header>
      <div className="wx-art-stats">
        {decisionKind && (
          <span>
            {t('chat.report_kind')}: <b>{decisionKind}</b>
          </span>
        )}
        {nValid !== null && (
          <span>
            {t('chat.report_n')}: <b>{nValid}{nTotal ? ` / ${nTotal}` : ''}</b>
          </span>
        )}
        {mean !== null && (
          <span>{t('chat.report_mean')}: <b>{mean}</b></span>
        )}
        {topChoice && (
          <span>{t('chat.report_top')}: <b>{topChoice}</b></span>
        )}
      </div>
      {expanded && (
        <div className="wx-m-text" style={{ marginTop: 8 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {msg.content || ''}
          </ReactMarkdown>
        </div>
      )}
    </div>
  )
}
