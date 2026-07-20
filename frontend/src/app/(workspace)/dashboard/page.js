// ============================================================
// SalesOS AI — Dashboard Page
// Pipeline overview, key metrics, conversion trends,
// recent activities, rep leaderboard.
// ============================================================

'use client';

import { useCallback } from 'react';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { formatNumber, formatPercent, timeAgo } from '@/lib/utils';

// ── Metric Card ────────────────────────────────────────────

function MetricCard({ label, value, format = 'number' }) {
  const display = format === 'percent' ? formatPercent(value) : formatNumber(value);
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{display}</div>
    </div>
  );
}

// ── Pipeline Funnel ────────────────────────────────────────

function PipelineFunnel({ metrics }) {
  if (!metrics) return null;

  const stages = [
    { key: 'new_leads', label: 'New', count: metrics.new_leads },
    { key: 'in_conversation', label: 'In Conversation', count: metrics.in_conversation },
    { key: 'qualified_leads', label: 'Qualified', count: metrics.qualified_leads },
    { key: 'meetings_booked', label: 'Meetings', count: metrics.meetings_booked },
    { key: 'converted', label: 'Converted', count: metrics.converted },
  ];

  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Pipeline Funnel</div>
      </div>
      <div className="pipeline-stages">
        {stages.map((stage) => (
          <div
            key={stage.key}
            className={`pipeline-stage ${stage.count > 0 ? 'pipeline-stage-active' : ''}`}
          >
            <div className="pipeline-stage-label">{stage.label}</div>
            <div className="pipeline-stage-count">{stage.count}</div>
            <div
              style={{
                height: '4px',
                background: stage.count > 0
                  ? `linear-gradient(90deg, var(--accent), var(--accent-hover))`
                  : 'var(--bg-elevated)',
                borderRadius: '2px',
                marginTop: 'var(--space-2)',
                width: `${Math.max((stage.count / maxCount) * 100, 5)}%`,
                transition: 'width 0.5s ease',
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Conversion Rates ───────────────────────────────────────

function ConversionRates({ metrics }) {
  if (!metrics) return null;

  const rates = [
    { label: 'Lead → Qualified', value: metrics.lead_to_qualified_rate },
    { label: 'Qualified → Meeting', value: metrics.qualified_to_meeting_rate },
    { label: 'Meeting → Conversion', value: metrics.meeting_to_conversion_rate },
    { label: 'Overall', value: metrics.overall_conversion_rate },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Conversion Rates</div>
      </div>
      <div className="flex flex-col gap-4">
        {rates.map((rate) => (
          <div key={rate.label}>
            <div className="flex items-center justify-between" style={{ marginBottom: '6px' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                {rate.label}
              </span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
                {formatPercent(rate.value)}
              </span>
            </div>
            <div
              style={{
                height: '6px',
                background: 'var(--bg-elevated)',
                borderRadius: '3px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${Math.min(rate.value, 100)}%`,
                  background: 'linear-gradient(90deg, var(--accent), var(--success))',
                  borderRadius: '3px',
                  transition: 'width 0.8s ease',
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Rep Leaderboard ────────────────────────────────────────

function RepLeaderboard({ reps }) {
  if (!reps || reps.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">Rep Performance</div>
        </div>
        <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
          No sales reps found.
        </p>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div className="card-header" style={{ padding: 'var(--space-5) var(--space-6) 0' }}>
        <div className="card-title">Rep Performance</div>
      </div>
      <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Rep</th>
              <th>Active Leads</th>
              <th>Meetings</th>
              <th>Conversions</th>
            </tr>
          </thead>
          <tbody>
            {reps.map((rep, i) => (
              <tr key={rep.user_id}>
                <td>
                  <div className="flex items-center gap-3">
                    <span
                      style={{
                        width: 24,
                        height: 24,
                        borderRadius: 'var(--radius-full)',
                        background: i === 0 ? 'var(--accent-muted)' : 'var(--bg-elevated)',
                        color: i === 0 ? 'var(--accent)' : 'var(--text-secondary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 'var(--text-xs)',
                        fontWeight: 600,
                      }}
                    >
                      {i + 1}
                    </span>
                    {rep.user_name}
                  </div>
                </td>
                <td>{rep.active_leads}</td>
                <td>{rep.meetings_booked}</td>
                <td>
                  <span className="badge badge-success">{rep.conversions}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── SLA Alert ──────────────────────────────────────────────

function SLAAlert({ violations }) {
  if (!violations || violations.length === 0) return null;

  return (
    <div
      className="card"
      style={{
        borderColor: 'var(--danger)',
        borderLeftWidth: '3px',
        padding: 'var(--space-4) var(--space-5)',
      }}
    >
      <div className="flex items-center gap-3">
        <span style={{ fontSize: '1.2rem' }}>⚠</span>
        <div>
          <div style={{ fontWeight: 600, color: 'var(--danger)' }}>
            {violations.length} SLA Violation{violations.length !== 1 ? 's' : ''}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            Leads requiring immediate attention
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard Page ─────────────────────────────────────────

export default function DashboardPage() {
  const { data: pipeline, loading: pipeLoading } = useApi(
    useCallback(() => api.getPipelineMetrics({ days: 30 }), [])
  );
  const { data: conversion } = useApi(
    useCallback(() => api.getConversionMetrics({ days: 30 }), [])
  );
  const { data: reps } = useApi(
    useCallback(() => api.getRepPerformance({ days: 30 }), [])
  );
  const { data: violations } = useApi(
    useCallback(() => api.getSLAViolations(), [])
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Sales pipeline overview — last 30 days</p>
        </div>
      </div>

      {/* SLA Alert */}
      <SLAAlert violations={violations} />

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4" style={{ marginTop: 'var(--space-4)' }}>
        {pipeLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 100 }} />
          ))
        ) : (
          <>
            <MetricCard label="Total Leads" value={pipeline?.total_leads} />
            <MetricCard label="Qualified" value={pipeline?.qualified_leads} />
            <MetricCard label="Meetings Booked" value={pipeline?.meetings_booked} />
            <MetricCard label="Converted" value={pipeline?.converted} />
          </>
        )}
      </div>

      {/* Pipeline + Conversion */}
      <div className="grid grid-cols-2 gap-4" style={{ marginTop: 'var(--space-4)' }}>
        <PipelineFunnel metrics={pipeline} />
        <ConversionRates metrics={conversion} />
      </div>

      {/* Rep Leaderboard */}
      <div style={{ marginTop: 'var(--space-4)' }}>
        <RepLeaderboard reps={reps} />
      </div>

      {/* Avg Score */}
      {pipeline && (
        <div className="grid grid-cols-3 gap-4" style={{ marginTop: 'var(--space-4)' }}>
          <MetricCard label="Avg Qualification Score" value={pipeline.avg_qualification_score} />
          <MetricCard label="Disqualified" value={pipeline.disqualified} />
          <MetricCard label="In Conversation" value={pipeline.in_conversation} />
        </div>
      )}
    </div>
  );
}
