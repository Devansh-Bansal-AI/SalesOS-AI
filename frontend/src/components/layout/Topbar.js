// ============================================================
// SalesOS AI — Topbar
// ============================================================

'use client';

import { usePathname } from 'next/navigation';

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/leads': 'Leads',
  '/conversations': 'Conversations',
  '/meetings': 'Meetings',
  '/crm': 'CRM',
  '/analytics': 'Analytics',
  '/ai': 'AI Workspace',
  '/settings': 'Settings',
};

function getPageTitle(pathname) {
  // Exact match first
  if (pageTitles[pathname]) return pageTitles[pathname];
  // Prefix match for nested routes
  for (const [path, title] of Object.entries(pageTitles)) {
    if (pathname.startsWith(path)) return title;
  }
  return 'SalesOS AI';
}

export default function Topbar() {
  const pathname = usePathname();
  const title = getPageTitle(pathname);

  return (
    <header className="topbar">
      <h2 className="topbar-title">{title}</h2>
      <div className="topbar-actions">
        {/* Notifications and search will be added later */}
      </div>
    </header>
  );
}
