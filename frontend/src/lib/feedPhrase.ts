// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// 决策动态 feed 的本地化措辞 —— 把 FeedItem 转成一句人话。
// kind 字符串对应后端 DecisionKind.value(rate/choose/click_probability/
// sentiment/wtp);error 优先。
import type { TFunction } from 'i18next'
import type { FeedItem } from '@/types/api'

export function phraseFeed(f: FeedItem, t: TFunction): string {
  if (f.error) return t('feed.error')
  switch (f.kind) {
    case 'rate':
      return t('feed.rate', { value: f.value })
    case 'choose':
      return t('feed.choose', { value: f.value })
    case 'sentiment':
      return Number(f.value) >= 0
        ? t('feed.sentiment_pos') : t('feed.sentiment_neg')
    case 'click_probability':
      return t('feed.click', { pct: Math.round(Number(f.value) * 100) })
    case 'wtp':
      return t('feed.wtp', { value: f.value })
    default:
      return String(f.value ?? '')
  }
}

/** 人群描述符:城市 · 性别 · 年龄段(过滤空值)。无信息时退回 name。 */
export function descFeed(f: FeedItem): string {
  const parts = [f.city, f.gender, f.age].filter(
    (x): x is string => !!x && x !== 'null')
  if (parts.length) return parts.join(' · ')
  return f.name || `#${f.agent_id}`
}
