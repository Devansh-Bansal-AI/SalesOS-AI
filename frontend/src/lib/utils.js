// ============================================================
// SalesOS AI — Utility Functions
// ============================================================

/**
 * Format a date to a human-readable string.
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format a date to relative time (e.g., "2 hours ago").
 */
export function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const now = new Date();
  const then = new Date(dateStr);
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return formatDate(dateStr);
}

/**
 * Format a datetime with time.
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Get initials from a name.
 */
export function getInitials(firstName, lastName) {
  const f = firstName?.charAt(0)?.toUpperCase() || '';
  const l = lastName?.charAt(0)?.toUpperCase() || '';
  return f + l || '?';
}

/**
 * Capitalize first letter.
 */
export function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}

/**
 * Get status badge variant.
 */
export function getStatusVariant(status) {
  const map = {
    new: 'info',
    contacted: 'default',
    qualified: 'success',
    outreach: 'accent',
    conversation: 'warning',
    nurture: 'warning',
    meeting_booked: 'accent',
    demo: 'accent',
    negotiation: 'warning',
    converted: 'success',
    lost: 'danger',
    disqualified: 'default',
  };
  return map[status] || 'default';
}

/**
 * Get priority badge variant.
 */
export function getPriorityVariant(priority) {
  const map = {
    critical: 'danger',
    high: 'warning',
    medium: 'accent',
    low: 'default',
  };
  return map[priority] || 'default';
}

/**
 * Format a number with commas.
 */
export function formatNumber(n) {
  if (n === null || n === undefined) return '—';
  return n.toLocaleString();
}

/**
 * Format a percentage.
 */
export function formatPercent(n) {
  if (n === null || n === undefined) return '—';
  return `${n.toFixed(1)}%`;
}

/**
 * Truncate text to a max length.
 */
export function truncate(str, maxLen = 50) {
  if (!str) return '';
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str;
}
