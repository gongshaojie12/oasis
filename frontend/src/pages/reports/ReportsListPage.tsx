// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Thin wrapper — body lives in views/ReportsView.tsx.
import { useParams } from 'react-router-dom'
import { ReportsView } from '@/views/ReportsView'

export function ReportsListPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  return <ReportsView slug={slug} />
}
