// ============================================================
// SalesOS AI — Conversations List Page
// ============================================================

'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { capitalize, timeAgo } from '@/lib/utils';

export default function ConversationsPage() {
  // Conversations are accessed via leads — show lead list with conversation counts
  const { data: leads, loading } = useApi(
    useCallback(() => api.getLeads({ per_page: 50, status: 'contacted' }), [])
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Conversations</h1>
          <p className="page-subtitle">Active communication threads</p>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 72 }} />
          ))}
        </div>
      ) : !leads || leads.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 'var(--space-3)' }}>◉</div>
          <p className="text-secondary">No active conversations yet.</p>
          <p className="text-tertiary" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>
            Conversations will appear here when leads are contacted.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {leads.map((lead) => (
            <Link
              key={lead.id}
              href={`/conversations/${lead.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div className="card" style={{ padding: 'var(--space-4)', cursor: 'pointer' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="sidebar-avatar"
                      style={{ width: 40, height: 40 }}
                    >
                      {(lead.first_name?.[0] || '') + (lead.last_name?.[0] || '')}
                    </div>
                    <div>
                      <div style={{ fontWeight: 500 }}>
                        {lead.first_name} {lead.last_name}
                      </div>
                      <div className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
                        {lead.email} {lead.company_name ? `· ${lead.company_name}` : ''}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`badge badge-${lead.status === 'conversation' ? 'success' : 'default'}`}>
                      {capitalize(lead.status)}
                    </span>
                    <span className="text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>
                      {timeAgo(lead.updated_at)}
                    </span>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
