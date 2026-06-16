// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

import { fetchBrand } from '@/lib/brand'
import { useBrandStore } from '@/stores/brandStore'

import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { VerifyEmailPage } from '@/pages/auth/VerifyEmailPage'
import { VerifySmsPage } from '@/pages/auth/VerifySmsPage'
import { ForgotPasswordPage } from '@/pages/auth/ForgotPasswordPage'
import { OnboardingPage } from '@/pages/onboarding/OnboardingPage'
import { WorkspacesPage } from '@/pages/WorkspacesPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { SandboxPage } from '@/pages/sandbox/SandboxPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { RequireAuth } from '@/components/RequireAuth'

const queryClient = new QueryClient()

export function App() {
  const setBrand = useBrandStore((s) => s.setBrand)
  useEffect(() => {
    void fetchBrand().then((b) => setBrand(b))
  }, [setBrand])
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="top-center"
          toastOptions={{
            style: {
              background: '#131e3b',
              color: '#fff',
              border: '1px solid rgba(120,145,220,0.18)',
            },
          }}
        />
        <Routes>
          <Route path="/" element={<Navigate to="/workspaces" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/verify-sms" element={<VerifySmsPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
          <Route path="/workspaces" element={<RequireAuth><WorkspacesPage /></RequireAuth>} />
          <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
          <Route path="/w/:slug" element={<RequireAuth><DashboardPage /></RequireAuth>} />
          <Route path="/w/:slug/sandboxes/:sandboxId" element={<RequireAuth><SandboxPage /></RequireAuth>} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
