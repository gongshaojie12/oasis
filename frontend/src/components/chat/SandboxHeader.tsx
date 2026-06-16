// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Top bar: sandbox identity + workspace + balance + I18nToggle.
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { I18nToggle } from '@/components/I18nToggle'
import { ThemeToggle } from '@/components/ThemeToggle'
import type { Sandbox, Workspace } from '@/types/api'

interface Props {
  sandbox: Sandbox
  workspace: Workspace
}

export function SandboxHeader({ sandbox, workspace }: Props) {
  const { t } = useTranslation()
  const nav = useNavigate()

  return (
    <div className="wx-chat-top">
      <button
        type="button"
        className="wx-btn-ghost"
        style={{ padding: '6px 10px', fontSize: 12 }}
        onClick={() => nav(`/w/${workspace.slug}`)}
        aria-label={t('common.back')}
      >
        ←
      </button>
      <div className="wx-ct-ava" aria-hidden="true">{sandbox.emoji}</div>
      <div className="wx-ct-name">
        <b>
          {sandbox.name}
          <span className="wx-ct-badge">{t('panel.live')}</span>
        </b>
        <small>
          {workspace.name} · {t('workspaces.balance')}:{' '}
          {t('workspaces.units', { n: workspace.balance_cost_units })}
        </small>
      </div>
      <div style={{ flex: 1 }} />
      <ThemeToggle />
      <I18nToggle />
    </div>
  )
}
