// ============================================================
// SalesOS AI — Workspace Layout
// Wraps all authenticated pages with sidebar + topbar.
// ============================================================

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AuthProvider, useAuth } from '@/lib/auth';
import Sidebar from '@/components/layout/Sidebar';
import Topbar from '@/components/layout/Topbar';

function WorkspaceGuard({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="auth-page">
        <div style={{ textAlign: 'center' }}>
          <div className="sidebar-brand" style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>
            SalesOS AI
          </div>
          <p className="text-secondary">Loading workspace…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="workspace-layout">
      <Sidebar />
      <main className="main-content">
        <Topbar />
        <div className="page-content">
          {children}
        </div>
      </main>
    </div>
  );
}

export default function WorkspaceLayout({ children }) {
  return (
    <AuthProvider>
      <WorkspaceGuard>{children}</WorkspaceGuard>
    </AuthProvider>
  );
}
