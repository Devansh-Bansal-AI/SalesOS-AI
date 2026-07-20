// ============================================================
// SalesOS AI — API Client
// JWT auto-refresh, typed responses, error handling.
// ============================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Token management
let accessToken = null;
let refreshToken = null;
let refreshPromise = null;

export function setTokens(access, refresh) {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }
}

export function getTokens() {
  if (typeof window !== 'undefined' && !accessToken) {
    accessToken = localStorage.getItem('access_token');
    refreshToken = localStorage.getItem('refresh_token');
  }
  return { accessToken, refreshToken };
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

async function refreshAccessToken() {
  const { refreshToken: rt } = getTokens();
  if (!rt) throw new ApiError('No refresh token', 401);

  // Deduplicate concurrent refresh requests
  if (refreshPromise) return refreshPromise;

  refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: rt }),
  })
    .then(async (res) => {
      if (!res.ok) throw new ApiError('Token refresh failed', 401);
      const json = await res.json();
      setTokens(json.data.access_token, json.data.refresh_token);
      return json.data.access_token;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

async function request(method, path, { body, params, requiresAuth = true } = {}) {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });
  }

  const headers = { 'Content-Type': 'application/json' };

  if (requiresAuth) {
    const { accessToken: at } = getTokens();
    if (at) headers['Authorization'] = `Bearer ${at}`;
  }

  let res = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Auto-refresh on 401
  if (res.status === 401 && requiresAuth && refreshToken) {
    try {
      const newToken = await refreshAccessToken();
      headers['Authorization'] = `Bearer ${newToken}`;
      res = await fetch(url.toString(), {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch {
      clearTokens();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new ApiError('Session expired', 401);
    }
  }

  const json = await res.json().catch(() => null);

  if (!res.ok) {
    throw new ApiError(
      json?.detail || json?.message || `Request failed (${res.status})`,
      res.status,
      json
    );
  }

  return json;
}

// ── Public API Methods ─────────────────────────────────────

export const api = {
  // Auth
  login: (email, password) =>
    request('POST', '/auth/login', { body: { email, password }, requiresAuth: false }),
  register: (data) =>
    request('POST', '/auth/register', { body: data, requiresAuth: false }),
  getMe: () =>
    request('GET', '/auth/me'),

  // Leads
  getLeads: (params) =>
    request('GET', '/leads', { params }),
  getLead: (id) =>
    request('GET', `/leads/${id}`),
  createLead: (data) =>
    request('POST', '/leads', { body: data }),
  updateLead: (id, data) =>
    request('PATCH', `/leads/${id}`, { body: data }),
  deleteLead: (id) =>
    request('DELETE', `/leads/${id}`),

  // Lead Timeline
  getLeadTimeline: (id, params) =>
    request('GET', `/leads/${id}/activities`, { params }),
  getActivityCounts: (id) =>
    request('GET', `/leads/${id}/activities/counts`),

  // Assignment
  autoAssignLead: (id, config) =>
    request('POST', `/leads/${id}/auto-assign`, { body: config }),

  // SLA
  getLeadSLA: (id) =>
    request('GET', `/leads/${id}/sla`),
  getSLAViolations: () =>
    request('GET', '/sla/violations'),

  // Conversations
  getLeadConversations: (leadId) =>
    request('GET', `/leads/${leadId}/conversations`),
  getConversation: (id) =>
    request('GET', `/conversations/${id}`),
  getMessages: (id) =>
    request('GET', `/conversations/${id}/messages`),

  // Meetings
  bookMeeting: (data) =>
    request('POST', '/meetings', { body: data }),
  getMeetings: (params) =>
    request('GET', '/meetings', { params }),
  getMeeting: (id) =>
    request('GET', `/meetings/${id}`),
  rescheduleMeeting: (id, data) =>
    request('PATCH', `/meetings/${id}/reschedule`, { body: data }),
  cancelMeeting: (id, data) =>
    request('POST', `/meetings/${id}/cancel`, { body: data }),
  getLeadMeetings: (leadId, params) =>
    request('GET', `/meetings/lead/${leadId}`, { params }),

  // Activities
  createActivity: (data) =>
    request('POST', '/activities', { body: data }),

  // Dashboard
  getPipelineMetrics: (params) =>
    request('GET', '/dashboard/pipeline', { params }),
  getConversionMetrics: (params) =>
    request('GET', '/dashboard/conversion', { params }),
  getRepPerformance: (params) =>
    request('GET', '/dashboard/reps', { params }),
};

export { ApiError };
