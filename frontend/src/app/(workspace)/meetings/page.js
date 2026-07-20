// ============================================================
// SalesOS AI — Meetings Page
// ============================================================

'use client';

import { useCallback } from 'react';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { capitalize, formatDateTime } from '@/lib/utils';

const TYPE_COLORS = {
  discovery: 'var(--info)',
  demo: 'var(--accent)',
  follow_up: 'var(--warning)',
  onboarding: 'var(--success)',
  custom: 'var(--text-secondary)',
};

export default function MeetingsPage() {
  const { data: meetings, loading } = useApi(
    useCallback(() => api.getMeetings({ limit: 50 }), [])
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Meetings</h1>
          <p className="page-subtitle">Upcoming and recent meetings</p>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 100 }} />
          ))}
        </div>
      ) : !meetings || meetings.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 'var(--space-3)' }}>◆</div>
          <p className="text-secondary">No meetings scheduled.</p>
          <p className="text-tertiary" style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>
            Meetings appear here when booked via the Booking Agent or API.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {meetings.map((meeting) => (
            <div key={meeting.id} className="card" style={{ padding: 'var(--space-4)' }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Type indicator */}
                  <div
                    style={{
                      width: 4,
                      height: 48,
                      borderRadius: 2,
                      background: TYPE_COLORS[meeting.meeting_type] || 'var(--accent)',
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 600 }}>{meeting.title}</div>
                    <div className="flex items-center gap-3" style={{ marginTop: 4 }}>
                      <span className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
                        {formatDateTime(meeting.scheduled_at)}
                      </span>
                      <span className="text-tertiary" style={{ fontSize: 'var(--text-sm)' }}>
                        {meeting.duration_minutes} min
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="badge badge-accent">
                    {capitalize(meeting.meeting_type)}
                  </span>
                  <span className={`badge badge-${
                    meeting.status === 'confirmed' ? 'success' :
                    meeting.status === 'cancelled' ? 'danger' :
                    meeting.status === 'completed' ? 'default' :
                    'warning'
                  }`}>
                    {capitalize(meeting.status)}
                  </span>
                </div>
              </div>
              {meeting.description && (
                <div
                  className="text-secondary"
                  style={{
                    fontSize: 'var(--text-sm)',
                    marginTop: 'var(--space-3)',
                    marginLeft: 'calc(4px + var(--space-4))',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {meeting.description}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
