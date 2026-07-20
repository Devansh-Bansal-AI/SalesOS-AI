// ============================================================
// SalesOS AI — Sidebar Navigation
// ============================================================

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { getInitials } from '@/lib/utils';

const navItems = [
  {
    section: 'Overview',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: '◈' },
    ],
  },
  {
    section: 'Sales',
    items: [
      { href: '/leads', label: 'Leads', icon: '◎' },
      { href: '/conversations', label: 'Conversations', icon: '◉' },
      { href: '/meetings', label: 'Meetings', icon: '◆' },
      { href: '/crm', label: 'CRM', icon: '◇' },
    ],
  },
  {
    section: 'Intelligence',
    items: [
      { href: '/analytics', label: 'Analytics', icon: '▤' },
      { href: '/ai', label: 'AI Workspace', icon: '⬡' },
    ],
  },
  {
    section: 'System',
    items: [
      { href: '/settings', label: 'Settings', icon: '⚙' },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-brand">SalesOS AI</div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((group) => (
          <div key={group.section}>
            <div className="sidebar-section">{group.section}</div>
            {group.items.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                >
                  <span className="nav-item-icon">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user" onClick={logout} title="Sign out">
          <div className="sidebar-avatar">
            {user ? getInitials(user.first_name, user.last_name) : '?'}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name truncate">
              {user ? `${user.first_name} ${user.last_name}` : 'Loading…'}
            </div>
            <div className="sidebar-user-role">
              {user?.role?.replace('_', ' ') || ''}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
