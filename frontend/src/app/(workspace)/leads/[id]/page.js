// ============================================================
// SalesOS AI — Lead Detail Page
// ============================================================

'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import {
  capitalize, getStatusVariant, getPriorityVariant,
  formatDate, timeAgo, getInitials,
} from '@/lib/utils';

// ── Contact Card ───────────────────────────────────────────

function ContactCard({ lead }) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Contact Info</div>
      </div>
      <div className="flex items-center gap-4" style={{ marginBottom: 'var(--space-4)' }}>
        <div
          className="sidebar-avatar"
          style={{ width: 48, height: 48, fontSize: 'var(--text-lg)' }}
        >
          {getInitials(lead.first_name, lead.last_name)}
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 'var(--text-lg)' }}>
            {lead.first_name} {lead.last_name}
          </div>
          <div className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            {lead.job_title || 'No title'}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <InfoRow label="Email" value={lead.email} />
        <InfoRow label="Phone" value={lead.phone || '—'} />
        <InfoRow label="Company" value={lead.company_name || '—'} />
        <InfoRow label="Source" value={capitalize(lead.source) || '—'} />
        <InfoRow label="Created" value={formatDate(lead.created_at)} />
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>{label}</span>
      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>{value}</span>
    </div>
  );
}

// ── Qualification Card ─────────────────────────────────────

function QualificationCard({ lead }) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Qualification</div>
        <span className={`badge badge-${getStatusVariant(lead.status)}`}>
          {capitalize(lead.status)}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        <div>
          <div className="metric-label">Score</div>
          <div
            className="metric-value"
            style={{
              color: lead.qualification_score >= 70
                ? 'var(--success)'
                : lead.qualification_score >= 40
                ? 'var(--warning)'
                : 'var(--text-secondary)',
            }}
          >
            {lead.qualification_score ?? '—'}
            <span style={{ fontSize: 'var(--text-lg)', color: 'var(--text-tertiary)' }}>/100</span>
          </div>
          {/* Score bar */}
          <div
            style={{
              height: '6px',
              background: 'var(--bg-elevated)',
              borderRadius: '3px',
              marginTop: 'var(--space-2)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${lead.qualification_score || 0}%`,
                background: lead.qualification_score >= 70
                  ? 'var(--success)'
                  : lead.qualification_score >= 40
                  ? 'var(--warning)'
                  : 'var(--text-tertiary)',
                borderRadius: '3px',
                transition: 'width 0.6s ease',
              }}
            />
          </div>
        </div>
        <InfoRow label="Priority" value={
          lead.priority ? (
            <span className={`badge badge-${getPriorityVariant(lead.priority)}`}>
              {capitalize(lead.priority)}
            </span>
          ) : '—'
        } />
        <InfoRow label="Intent" value={capitalize(lead.intent) || '—'} />
        <InfoRow label="Urgency" value={capitalize(lead.urgency) || '—'} />
      </div>
    </div>
  );
}

// ── Company Card ───────────────────────────────────────────

function CompanyCard({ lead }) {
  const enrichment = lead.enrichment_data || {};
  if (!enrichment || Object.keys(enrichment).length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">Company</div>
        </div>
        <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
          Not yet enriched.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Company</div>
      </div>
      <div className="flex flex-col gap-3">
        <InfoRow label="Name" value={enrichment.company_name || lead.company_name || '—'} />
        <InfoRow label="Industry" value={enrichment.industry || '—'} />
        <InfoRow label="Size" value={enrichment.employee_count || '—'} />
        <InfoRow label="Location" value={enrichment.location || '—'} />
        <InfoRow label="Website" value={enrichment.website || '—'} />
      </div>
    </div>
  );
}

// ── Activity Timeline ──────────────────────────────────────

function Timeline({ leadId }) {
  const { data: activities, loading } = useApi(
    useCallback(() => api.getLeadTimeline(leadId, { per_page: 20 }), [leadId])
  );

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">Activity Timeline</div>
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 40, marginBottom: 8 }} />
        ))}
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Activity Timeline</div>
      </div>
      {!activities || activities.length === 0 ? (
        <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
          No activities yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {activities.map((activity, i) => (
            <div
              key={activity.id || i}
              className="flex gap-3"
              style={{
                paddingBottom: 'var(--space-3)',
                borderBottom: i < activities.length - 1 ? '1px solid var(--border)' : 'none',
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--accent)',
                  marginTop: 6,
                  flexShrink: 0,
                }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
                  {activity.title}
                </div>
                {activity.description && (
                  <div className="text-secondary" style={{ fontSize: 'var(--text-xs)', marginTop: 2 }}>
                    {activity.description}
                  </div>
                )}
                <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)', marginTop: 4 }}>
                  {timeAgo(activity.created_at)}
                </div>
              </div>
              <span className="badge badge-default" style={{ alignSelf: 'flex-start' }}>
                {capitalize(activity.activity_type)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Lead Detail Page ───────────────────────────────────────

export default function LeadDetailPage() {
  const { id } = useParams();

  const { data: lead, loading, error } = useApi(
    useCallback(() => api.getLead(id), [id])
  );

  if (loading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="skeleton" style={{ height: 32, width: 200 }} />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 300 }} />
          ))}
        </div>
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="card">
        <p className="text-danger">{error || 'Lead not found'}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{lead.first_name} {lead.last_name}</h1>
          <p className="page-subtitle">{lead.email}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`badge badge-${getStatusVariant(lead.status)}`}>
            {capitalize(lead.status)}
          </span>
        </div>
      </div>

      {/* Top cards */}
      <div className="grid grid-cols-3 gap-4">
        <ContactCard lead={lead} />
        <QualificationCard lead={lead} />
        <CompanyCard lead={lead} />
      </div>

      {/* Timeline */}
      <div style={{ marginTop: 'var(--space-4)' }}>
        <Timeline leadId={id} />
      </div>
    </div>
  );
}
