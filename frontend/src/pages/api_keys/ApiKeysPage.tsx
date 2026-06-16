// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Thin wrapper — body lives in views/ApiKeysView.tsx.
import { useParams } from 'react-router-dom'
import { ApiKeysView } from '@/views/ApiKeysView'

export function ApiKeysPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  return <ApiKeysView slug={slug} />
}
