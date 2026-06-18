// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'zh' },
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn((url: string) => {
      if (url.includes('/model-presets')) {
        return Promise.resolve({ data: { presets: [
          { id: 'stub', label: '测试桩', base_url: null,
            default_model: null, needs_key: false,
            allow_custom_base_url: false },
          { id: 'deepseek', label: 'DeepSeek',
            base_url: 'https://api.deepseek.com/v1',
            default_model: 'deepseek-chat', needs_key: true,
            allow_custom_base_url: false },
        ] } })
      }
      if (url.includes('/model-config')) {
        return Promise.resolve({ data: {
          provider: 'stub', api_key_masked: null, base_url: null,
          model_name: null, has_key: false, updated_at: null,
          updated_by: null } })
      }
      if (url.includes('/members')) {
        return Promise.resolve({ data: { members: [
          { user_id: 'u1', role: 'owner' },
        ] } })
      }
      if (/\/workspaces\/[^/]+$/.test(url)) {
        return Promise.resolve({ data: { owner_user_id: 'u1' } })
      }
      return Promise.resolve({ data: {} })
    }),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (sel: any) => sel({
    user: { user_id: 'u1' },
    workspaces: [{ slug: 'reptest', name: 'RT', locale: 'zh',
                   type: 'personal' }],
    setWorkspaces: vi.fn(),
  }),
}))

import { SettingsView } from './SettingsView'

describe('SettingsView model config card', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders provider select after load', async () => {
    render(<SettingsView slug="reptest" />)
    await waitFor(() =>
      expect(screen.getByTestId('model-provider-select')).toBeTruthy())
  })
})
