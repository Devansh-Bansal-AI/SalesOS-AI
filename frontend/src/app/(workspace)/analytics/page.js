// ============================================================
// SalesOS AI — Analytics Page
// ============================================================

'use client';

import { useCallback } from 'react';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { formatNumber, formatPercent } from '@/lib/utils';

export default function AnalyticsPage() {
  const { data: pipeline } = useApi(
    useCallback(() => api.getPipelineMetrics({ days: 30 }), [])
  );
  const { data: conversion } = useApi(
    useCallback(() => api.getConversionMetrics({ days: 30 }), [])
  );
  const { data: reps } = useApi(
    useCallback(() => api.getRepPerformance({ days: 30 }), [])
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Sales performance insights — last 30 days</p>
        </div>
      </div>

      {/* Pipeline Breakdown */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-header">
          <div className="card-title">Pipeline Breakdown</div>
        </div>
        {pipeline ? (
          <div className="grid grid-cols-4 gap-4">
            <StatBlock label="Total" value={pipeline.total_leads} />
            <StatBlock label="New" value={pipeline.new_leads} color="var(--info)" />
            <StatBlock label="Qualified" value={pipeline.qualified_leads} color="var(--success)" />
            <StatBlock label="In Conversation" value={pipeline.in_conversation} color="var(--warning)" />
            <StatBlock label="Meetings" value={pipeline.meetings_booked} color="var(--accent)" />
            <StatBlock label="Converted" value={pipeline.converted} color="var(--success)" />
            <StatBlock label="Lost" value={pipeline.disqualified} color="var(--danger)" />
            <StatBlock label="Avg Score" value={pipeline.avg_qualification_score} suffix="/100" />
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 80 }} />
            ))}
          </div>
        )}
      </div>

      {/* Conversion Funnel */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-header">
          <div className="card-title">Conversion Funnel</div>
        </div>
        {conversion ? (
          <div className="flex flex-col gap-4">
            <FunnelBar label="Lead → Qualified" rate={conversion.lead_to_qualified_rate} />
            <FunnelBar label="Qualified → Meeting" rate={conversion.qualified_to_meeting_rate} />
            <FunnelBar label="Meeting → Won" rate={conversion.meeting_to_conversion_rate} />
            <FunnelBar label="Overall" rate={conversion.overall_conversion_rate} highlight />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 48 }} />
            ))}
          </div>
        )}
      </div>

      {/* Rep Performance */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Rep Performance</div>
        </div>
        {reps && reps.length > 0 ? (
          <div className="table-container" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Active Leads</th>
                  <th>Meetings</th>
                  <th>Conversions</th>
                  <th>Conv. Rate</th>
                </tr>
              </thead>
              <tbody>
                {reps.map((rep, i) => {
                  const convRate = rep.active_leads > 0
                    ? (rep.conversions / rep.active_leads * 100)
                    : 0;
                  return (
                    <tr key={rep.user_id}>
                      <td>
                        <span
                          style={{
                            display: 'inline-flex',
                            width: 24, height: 24,
                            alignItems: 'center', justifyContent: 'center',
                            borderRadius: 'var(--radius-full)',
                            background: i < 3 ? 'var(--accent-muted)' : 'var(--bg-elevated)',
                            color: i < 3 ? 'var(--accent)' : 'var(--text-secondary)',
                            fontSize: 'var(--text-xs)', fontWeight: 600,
                          }}
                        >
                          {i + 1}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{rep.user_name}</td>
                      <td>{rep.active_leads}</td>
                      <td>{rep.meetings_booked}</td>
                      <td>
                        <span className="badge badge-success">{rep.conversions}</span>
                      </td>
                      <td>{formatPercent(convRate)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            No performance data available.
          </p>
        )}
      </div>
    </div>
  );
}

function StatBlock({ label, value, color, suffix = '' }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div className="metric-label">{label}</div>
      <div
        className="metric-value"
        style={{ fontSize: 'var(--text-2xl)', color: color || 'var(--text-primary)' }}
      >
        {formatNumber(value)}
        {suffix && (
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

function FunnelBar({ label, rate, highlight = false }) {
  return (
    <div>
      <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
        <span style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-secondary)',
          fontWeight: highlight ? 600 : 400,
        }}>
          {label}
        </span>
        <span style={{
          fontSize: 'var(--text-sm)',
          fontWeight: 600,
          color: highlight ? 'var(--accent)' : 'var(--text-primary)',
        }}>
          {formatPercent(rate)}
        </span>
      </div>
      <div style={{
        height: highlight ? '8px' : '6px',
        background: 'var(--bg-elevated)',
        borderRadius: '4px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${Math.min(rate, 100)}%`,
          background: highlight
            ? 'linear-gradient(90deg, var(--accent), var(--accent-hover))'
            : 'linear-gradient(90deg, var(--accent), var(--success))',
          borderRadius: '4px',
          transition: 'width 0.8s ease',
        }} />
      </div>
    </div>
  );
}
