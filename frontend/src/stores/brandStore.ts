// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { create } from 'zustand'
import type { BrandConfig } from '@/types/api'

interface BrandState {
  brand: BrandConfig | null
  setBrand: (b: BrandConfig | null) => void
}

export const useBrandStore = create<BrandState>((set) => ({
  brand: null,
  setBrand: (brand) => set({ brand }),
}))
