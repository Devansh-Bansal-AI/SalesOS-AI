// ============================================================
// SalesOS AI — CRM Page (Activity Timeline)
// ============================================================

'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { capitalize, timeAgo } from '@/lib/utils';

const ACTIVITY_ICON = {
  lead_created: '✦',
  lead_qualified: '◎',
  lead_enriched: '◈',
  lead_assigned: '→',
  lead_status_changed: '↻',
  email_sent: '✉',
  email_received: '↓',
  meeting_scheduled: '◆',
  meeting_completed: '◇',
  note_added: '✎',
  call_logged: '☎',
  followup_scheduled: '⏱',
  followup_sent: '↗',
  sla_violation: '⚠',
  qualification_completed: '⬡',
  enrichment_completed: '◈',
  escalation_created: '▲',
  score_changed: '★',
};

export default function CRMPage() {
  const [selectedLead, setSelectedLead] = useState('');

  // Get recent leads for the selector
  const { data: leads } = useApi(
    useCallback(() => api.getLeads({ per_page: 100 }), [])
  );

  // Get timeline for selected lead
  const { data: activities, loading } = useApi(
    useCallback(() => {
      if (!selectedLead) return Promise.resolve({ data: [] });
      return api.getLeadTimeline(selectedLead, { per_page: 50 });
    }, [selectedLead]),
    [selectedLead],
    !!selectedLead
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">CRM</h1>
          <p className="page-subtitle">Unified activity timeline</p>
        </div>
      </div>

      {/* Lead selector */}
      <div className="input-group" style={{ maxWidth: 400, marginBottom: 'var(--space-6)' }}>
        <label>Select Lead</label>
        <select
          className="input"
          value={selectedLead}
          onChange={(e) => setSelectedLead(e.target.value)}
        >
          <option value="">Choose a lead…</option>
          {leads && leads.map((lead) => (
            <option key={lead.id} value={lead.id}>
              {lead.first_name} {lead.last_name} — {lead.email}
            </option>
          ))}
        </select>
      </div>

      {!selectedLead ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 'var(--space-3)' }}>◇</div>
          <p className="text-secondary">Select a lead to view their CRM timeline.</p>
        </div>
      ) : loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 56 }} />
          ))}
        </div>
      ) : !activities || activities.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
          <p className="text-secondary">No activities recorded yet.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          {activities.map((activity, i) => (
            <div
              key={activity.id || i}
              className="flex items-center gap-4"
              style={{
                padding: 'var(--space-4) var(--space-5)',
                borderBottom: i < activities.length - 1 ? '1px solid var(--border)' : 'none',
                transition: 'background var(--transition-fast)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-hover)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 'var(--text-sm)',
                  flexShrink: 0,
                }}
              >
                {ACTIVITY_ICON[activity.activity_type] || '•'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
                  {activity.title}
                </div>
                {activity.description && (
                  <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)', marginTop: 2 }}>
                    {activity.description}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="badge badge-default">
                  {capitalize(activity.activity_type)}
                </span>
                <span className="text-tertiary" style={{ fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>
                  {timeAgo(activity.created_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
