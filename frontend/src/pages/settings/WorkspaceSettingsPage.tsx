// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Thin wrapper — body lives in views/SettingsView.tsx.
import { useParams } from 'react-router-dom'
import { SettingsView } from '@/views/SettingsView'

export function WorkspaceSettingsPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  return <SettingsView slug={slug} />
}
