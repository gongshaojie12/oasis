// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// One message in the conversation. Visual mirrors chat.html .msg/.m-av/.m-body.
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useBrandStore } from '@/stores/brandStore'
import { useAuthStore } from '@/stores/authStore'
import { ReportCard } from './ReportCard'
import type { ChatMessage } from '@/types/api'

interface Props { msg: ChatMessage }

function authorLabel(role: ChatMessage['role'], t: (k: string) => string) {
  if (role === 'user') return t('chat.user')
  if (role === 'system') return t('chat.system')
  return t('chat.assistant')
}

export function ChatBubble({ msg }: Props) {
  const { t, i18n } = useTranslation()
  const { brand } = useBrandStore()
  const user = useAuthStore((s) => s.user)
  const lang: 'zh' | 'en' = i18n.language === 'en' ? 'en' : 'zh'
  const isUser = msg.role === 'user'

  const aiAvatar = brand?.avatar?.[lang] ?? (lang === 'en' ? 'W' : '象')
  const userAvatar = (user?.display_name ?? '?').trim().charAt(0).toUpperCase()
  const wrapClasses = ['wx-msg']
  if (msg.kind === 'error') wrapClasses.push('wx-msg-error')
  if (msg.kind === 'intent_parsed') wrapClasses.push('wx-msg-intent')

  return (
    <div className={wrapClasses.join(' ')}>
      <div className={`wx-m-av ${isUser ? 'u' : 'ai'}`} aria-hidden="true">
        {isUser ? userAvatar : aiAvatar}
      </div>
      <div className="wx-m-body">
        <div className="wx-m-name">{authorLabel(msg.role, t)}</div>
        {msg.kind === 'report_card' ? (
          <ReportCard msg={msg} />
        ) : (
          <div className="wx-m-text">
            {isUser ? (
              msg.content
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content || ''}
              </ReactMarkdown>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
