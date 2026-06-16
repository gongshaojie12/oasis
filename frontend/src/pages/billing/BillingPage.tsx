// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Thin wrapper — body lives in views/BillingView.tsx so both the
// /w/:slug/billing route AND LandingPage's in-page view can reuse it.
import { useParams } from 'react-router-dom'
import { BillingView, formatCostUnits } from '@/views/BillingView'

export { formatCostUnits }

export function BillingPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  return <BillingView slug={slug} />
}
