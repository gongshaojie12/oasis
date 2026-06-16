// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// Tiny wrapper around GET /v1/brand. Returns null on error so callers
// can fall back to baked-in defaults.
import { api } from './api'
import type { BrandConfig } from '@/types/api'

export async function fetchBrand(): Promise<BrandConfig | null> {
  try {
    const r = await api.get<BrandConfig>('/brand')
    return r.data
  } catch {
    return null
  }
}
