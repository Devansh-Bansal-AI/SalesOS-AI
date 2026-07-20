// ============================================================
// SalesOS AI — Leads List Page
// ============================================================

'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useApi, useDebounce } from '@/lib/hooks';
import { capitalize, getStatusVariant, getPriorityVariant, timeAgo, formatNumber } from '@/lib/utils';

const STATUS_OPTIONS = [
  'all', 'new', 'contacted', 'qualified', 'outreach',
  'conversation', 'nurture', 'meeting_booked', 'demo',
  'negotiation', 'converted', 'lost', 'disqualified',
];

export default function LeadsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);

  const fetchLeads = useCallback(() => {
    const params = { page, per_page: 20 };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (debouncedSearch) params.search = debouncedSearch;
    return api.getLeads(params);
  }, [page, statusFilter, debouncedSearch]);

  const { data: leads, loading, error } = useApi(fetchLeads, [page, statusFilter, debouncedSearch]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Leads</h1>
          <p className="page-subtitle">Manage your sales pipeline</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4" style={{ marginBottom: 'var(--space-4)' }}>
        <input
          type="text"
          className="input"
          placeholder="Search leads…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          style={{ maxWidth: 300 }}
        />
        <div className="tabs" style={{ borderBottom: 'none' }}>
          {STATUS_OPTIONS.slice(0, 7).map((s) => (
            <button
              key={s}
              className={`tab ${statusFilter === s ? 'tab-active' : ''}`}
              onClick={() => { setStatusFilter(s); setPage(1); }}
            >
              {s === 'all' ? 'All' : capitalize(s)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 48 }} />
          ))}
        </div>
      ) : error ? (
        <div className="card">
          <p className="text-danger">{error}</p>
        </div>
      ) : !leads || leads.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
          <p className="text-secondary">No leads found.</p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Company</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Score</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    <Link
                      href={`/leads/${lead.id}`}
                      style={{ fontWeight: 500 }}
                    >
                      {lead.first_name} {lead.last_name}
                    </Link>
                  </td>
                  <td className="text-secondary">{lead.email}</td>
                  <td>{lead.company_name || '—'}</td>
                  <td>
                    <span className="flex items-center gap-2">
                      <span className={`status-dot status-dot-${lead.status}`} />
                      <span className={`badge badge-${getStatusVariant(lead.status)}`}>
                        {capitalize(lead.status)}
                      </span>
                    </span>
                  </td>
                  <td>
                    {lead.priority ? (
                      <span className={`badge badge-${getPriorityVariant(lead.priority)}`}>
                        {capitalize(lead.priority)}
                      </span>
                    ) : '—'}
                  </td>
                  <td>
                    {lead.qualification_score !== null && lead.qualification_score !== undefined ? (
                      <span
                        style={{
                          fontWeight: 600,
                          color: lead.qualification_score >= 70
                            ? 'var(--success)'
                            : lead.qualification_score >= 40
                            ? 'var(--warning)'
                            : 'var(--text-secondary)',
                        }}
                      >
                        {lead.qualification_score}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="text-secondary">{timeAgo(lead.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {leads && leads.length > 0 && (
        <div className="flex items-center justify-between" style={{ marginTop: 'var(--space-4)' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            ← Previous
          </button>
          <span className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            Page {page}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={leads.length < 20}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
