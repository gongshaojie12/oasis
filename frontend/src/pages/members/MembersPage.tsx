// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Thin wrapper — body lives in views/MembersView.tsx.
import { useParams } from 'react-router-dom'
import { MembersView } from '@/views/MembersView'

export function MembersPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  return <MembersView slug={slug} />
}
