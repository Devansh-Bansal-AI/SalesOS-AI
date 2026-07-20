// ============================================================
// SalesOS AI — Settings Page
// ============================================================

'use client';

import { useAuth } from '@/lib/auth';
import { formatDate } from '@/lib/utils';

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Organization and account settings</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Profile */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Profile</div>
          </div>
          {user ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4">
                <div
                  className="sidebar-avatar"
                  style={{ width: 56, height: 56, fontSize: 'var(--text-xl)' }}
                >
                  {(user.first_name?.[0] || '') + (user.last_name?.[0] || '')}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 'var(--text-lg)' }}>
                    {user.first_name} {user.last_name}
                  </div>
                  <div className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
                    {user.email}
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-3" style={{ marginTop: 'var(--space-2)' }}>
                <SettingRow label="Role" value={user.role?.replace('_', ' ') || '—'} />
                <SettingRow label="Organization" value={user.organization_name || '—'} />
                <SettingRow label="Member since" value={formatDate(user.created_at)} />
                <SettingRow label="Last login" value={formatDate(user.last_login_at)} />
                <SettingRow label="Status" value={
                  <span className={`badge badge-${user.is_active ? 'success' : 'danger'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                } />
              </div>
            </div>
          ) : (
            <div className="skeleton" style={{ height: 200 }} />
          )}
        </div>

        {/* Organization */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Organization</div>
          </div>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-3">
              <SettingRow label="Name" value={user?.organization_name || '—'} />
              <SettingRow label="ID" value={
                <span className="font-mono text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>
                  {user?.organization_id || '—'}
                </span>
              } />
            </div>
          </div>
        </div>

        {/* Platform */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Platform</div>
          </div>
          <div className="flex flex-col gap-3">
            <SettingRow label="Version" value="1.0.0" />
            <SettingRow label="Architecture" value="Multi-agent AI Platform" />
            <SettingRow label="Agents" value="5 registered" />
            <SettingRow label="API" value="32 endpoints" />
          </div>
        </div>

        {/* Actions */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Account</div>
          </div>
          <div className="flex flex-col gap-4">
            <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
              Manage your account and session.
            </p>
            <button className="btn btn-danger" onClick={logout}>
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingRow({ label, value }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>{label}</span>
      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
        {typeof value === 'string' ? value : value}
      </span>
    </div>
  );
}
