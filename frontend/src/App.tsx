// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
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

import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout'
import { AdminLayout } from '@/components/layout/AdminLayout'
import { AdminGate } from '@/components/layout/AdminGate'

import { ReportsListPage } from '@/pages/reports/ReportsListPage'
import { ReportDetailPage } from '@/pages/reports/ReportDetailPage'
import { BillingPage } from '@/pages/billing/BillingPage'
import { MembersPage } from '@/pages/members/MembersPage'
import { ApiKeysPage } from '@/pages/api_keys/ApiKeysPage'
import { WorkspaceSettingsPage } from '@/pages/settings/WorkspaceSettingsPage'
import { UserSettingsPage } from '@/pages/settings/UserSettingsPage'
import { InviteAcceptPage } from '@/pages/invite/InviteAcceptPage'
import { AdminUsersPage } from '@/pages/admin/AdminUsersPage'
import { AdminWorkspacesPage } from '@/pages/admin/AdminWorkspacesPage'
import { AdminTransactionsPage } from '@/pages/admin/AdminTransactionsPage'

import { RequireAuth } from '@/components/RequireAuth'

const queryClient = new QueryClient()

function ProtectedShell() {
  return (
    <RequireAuth>
      <Outlet />
    </RequireAuth>
  )
}

export function App() {
  const setBrand = useBrandStore((s) => s.setBrand)
  useEffect(() => {
    void fetchBrand().then((b) => setBrand(b))
  }, [setBrand])
  return (
    <QueryClientProvider client={queryClient}>
      {/* P9: SPA mounted at /app/* — basename keeps all <Link> / useNavigate
          paths internal-relative, but URLs render as /app/login etc. */}
      <BrowserRouter basename="/app">
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
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/verify-sms" element={<VerifySmsPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/invite/:token" element={<InviteAcceptPage />} />

          {/* Authenticated, no workspace context */}
          <Route element={<ProtectedShell />}>
            <Route path="/" element={<Navigate to="/workspaces" replace />} />
            <Route path="/workspaces" element={<WorkspacesPage />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/settings/account" element={<UserSettingsPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />

            {/* Sandbox detail keeps its own full-screen 3-column shell —
                we don't wrap it in WorkspaceLayout so the chat composer
                still spans the full viewport. */}
            <Route
              path="/w/:slug/sandboxes/:sandboxId"
              element={<SandboxPage />}
            />

            {/* Workspace-scoped dashboard pages share a sidebar layout */}
            <Route path="/w/:slug" element={<WorkspaceLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="reports" element={<ReportsListPage />} />
              <Route path="reports/:taskId" element={<ReportDetailPage />} />
              <Route path="billing" element={<BillingPage />} />
              <Route path="members" element={<MembersPage />} />
              <Route path="api-keys" element={<ApiKeysPage />} />
              <Route path="settings" element={<WorkspaceSettingsPage />} />
            </Route>

            {/* Super-admin */}
            <Route
              path="/admin"
              element={
                <AdminGate>
                  <AdminLayout />
                </AdminGate>
              }
            >
              <Route index element={<Navigate to="/admin/users" replace />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route path="workspaces" element={<AdminWorkspacesPage />} />
              <Route path="transactions" element={<AdminTransactionsPage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
