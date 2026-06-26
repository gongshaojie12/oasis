// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// 全屏模拟驾驶舱 —— 大粒子群 + 大进度 + 大数字 + 决策动态流。
// 复刻 docs/prototype/chat.html 的 overlay 视觉,但数据全部真实(来自 SSE)。
// overlay 模式:fixed + backdrop 点击关闭 + Escape 关闭(仿 data/Modal.tsx)。
import { memo, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import { useSandboxStore } from '@/stores/sandboxStore'
import type { FeedItem, SimProgress } from '@/types/api'
import { phraseFeed, descFeed } from '@/lib/feedPhrase'
import { SwarmCanvas } from './SwarmCanvas'

interface Props {
  open: boolean
  onClose: () => void
  liveProgress: SimProgress | null
}

const FEED_COLORS = ['#8B5CF6', '#A78BFA', '#B79DF7', '#C9B6F5',
                     '#7C5CE0', '#9D7BF0']

const FeedRow = memo(function FeedRow({ item }: { item: FeedItem }) {
  const { t } = useTranslation()
  const color = FEED_COLORS[Math.abs(item.agent_id) % FEED_COLORS.length]
  const avatar = (item.name || String(item.agent_id)).trim().charAt(0)
    .toUpperCase()
  return (
    <div className="wx-cockpit-feed-row">
      <div className="wx-cockpit-fav"
           style={{ background: color + '22', color }}>{avatar}</div>
      <div className="wx-cockpit-ft">
        <b>{descFeed(item)}</b> {phraseFeed(item, t)}
      </div>
    </div>
  )
})

export function CockpitOverlay({ open, onClose, liveProgress }: Props) {
  const { t } = useTranslation()
  const feedItems = useSandboxStore((s) => s.feedItems)

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const total = liveProgress?.total ?? 0
  const done = liveProgress?.done ?? 0
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  const running = liveProgress?.status === 'running'

  return (
    <div
      className="wx-cockpit-backdrop"
      role="dialog"
      aria-modal="true"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="wx-cockpit">
        <div className="wx-cockpit-header">
          <span className="wx-cockpit-title">{t('overlay.title_cockpit')}</span>
          {running && (
            <span className="wx-panel-live">{t('overlay.live_label')}</span>
          )}
          <button type="button" className="wx-cockpit-close"
                  onClick={onClose} aria-label={t('overlay.back')}>
            <X size={16} /> {t('overlay.back')}
          </button>
        </div>

        <div className="wx-cockpit-body">
          <div className="wx-cockpit-main">
            <SwarmCanvas count={total} height={320} />
            <div className="wx-cockpit-prog">
              <div className="wx-cockpit-prog-head">
                <b>{pct}%</b>
                <span>{done} / {total}</span>
              </div>
              <div className="wx-cockpit-track">
                <i style={{ width: `${pct}%` }} />
              </div>
            </div>
            <div className="wx-cockpit-stats">
              <div className="wx-cockpit-stat">
                <span>{t('panel.active_agents')}</span>
                <b>{done.toLocaleString()} / {total.toLocaleString()}</b>
              </div>
              <div className="wx-cockpit-stat">
                <span>{t('stat.decisions')}</span>
                <b>{done.toLocaleString()}</b>
              </div>
              {typeof liveProgress?.mean === 'number' && (
                <div className="wx-cockpit-stat">
                  <span>{t('panel.running_mean')}</span>
                  <b>{liveProgress.mean.toFixed(2)}</b>
                </div>
              )}
            </div>
          </div>

          <div className="wx-cockpit-feed">
            <div className="wx-cockpit-feed-title">
              {t('overlay.activity_feed')}
            </div>
            <div className="wx-cockpit-feed-list">
              {feedItems.length === 0 ? (
                <div className="wx-cockpit-feed-empty">
                  {t('panel.sim_running')}…
                </div>
              ) : (
                feedItems.map((it) => <FeedRow key={it.id} item={it} />)
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
