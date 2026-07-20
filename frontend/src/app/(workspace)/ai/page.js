// ============================================================
// SalesOS AI — AI Workspace (Agent Registry + Monitor)
// ============================================================

'use client';

import Link from 'next/link';

// Static registry data — in production this would come from an API endpoint.
// Matches the 5 agents registered in app/agents/registry.py
const AGENTS = [
  {
    type: 'qualification',
    name: 'Qualification Agent',
    description: 'Scores and qualifies inbound leads using AI analysis of company, role, and intent signals.',
    version: 'v1.0',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Lead scoring', 'Priority classification', 'Intent detection', 'Urgency assessment'],
    input_fields: ['email', 'first_name', 'last_name', 'job_title', 'company_name', 'message'],
    output_fields: ['score', 'priority', 'intent', 'urgency', 'reasoning', 'confidence'],
  },
  {
    type: 'enrichment',
    name: 'Enrichment Agent',
    description: 'Enriches leads with company data, social profiles, technology stack, and firmographic information.',
    version: 'v1.0',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Company lookup', 'Firmographics', 'Tech stack detection', 'Social profiles'],
    input_fields: ['email', 'company_name', 'website'],
    output_fields: ['company_data', 'industry', 'employee_count', 'technology_stack'],
  },
  {
    type: 'conversation_intelligence',
    name: 'Conversation Intelligence Agent',
    description: '9-dimension conversation analysis with memory. Detects sentiment, buying signals, objections, and customer stage.',
    version: 'v1.0',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Sentiment analysis', 'Buying signal detection', 'Objection tracking', 'Risk assessment', 'Stage prediction', 'Follow-up recommendation'],
    input_fields: ['conversation_history', 'lead_context', 'memory'],
    output_fields: ['sentiment', 'buying_signals', 'objections', 'risk_level', 'customer_stage', 'recommended_action'],
  },
  {
    type: 'outreach',
    name: 'Outreach Agent',
    description: 'Generates personalized outreach emails using lead qualification, enrichment, and conversation context.',
    version: 'v1.0',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Email personalization', 'Subject line generation', 'Tone matching', 'CTA optimization'],
    input_fields: ['lead_data', 'qualification', 'enrichment', 'email_type'],
    output_fields: ['subject', 'body_html', 'body_text', 'tone', 'reasoning'],
  },
  {
    type: 'booking',
    name: 'Booking Agent',
    description: 'Determines optimal meeting setup: type, duration, title, description, and preferred time window.',
    version: 'v1.0',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Meeting type selection', 'Duration recommendation', 'Title generation', 'Time window ranking'],
    input_fields: ['lead_data', 'qualification', 'conversation_summary', 'available_slots'],
    output_fields: ['meeting_type', 'duration_minutes', 'title', 'description', 'preferred_time_window'],
  },
];

const STATUS_COLOR = {
  active: 'var(--success)',
  inactive: 'var(--text-tertiary)',
  error: 'var(--danger)',
};

export default function AIWorkspacePage() {
  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">AI Workspace</h1>
          <p className="page-subtitle">Agent registry, monitoring, and prompt management</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="badge badge-success">{AGENTS.length} agents registered</span>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-2 gap-4">
        {AGENTS.map((agent) => (
          <Link
            key={agent.type}
            href={`/ai/${agent.type}`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="card" style={{ cursor: 'pointer', height: '100%' }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-3)' }}>
                <div className="flex items-center gap-3">
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 'var(--radius-lg)',
                      background: 'var(--accent-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '1.1rem',
                    }}
                  >
                    ⬡
                  </div>
                  <div>
                    <div style={{ fontWeight: 600 }}>{agent.name}</div>
                    <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>
                      {agent.type} · {agent.version}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    style={{
                      width: 8, height: 8,
                      borderRadius: 'var(--radius-full)',
                      background: STATUS_COLOR[agent.status],
                    }}
                  />
                  <span style={{ fontSize: 'var(--text-xs)', color: STATUS_COLOR[agent.status] }}>
                    {agent.status}
                  </span>
                </div>
              </div>

              <p className="text-secondary" style={{ fontSize: 'var(--text-sm)', marginBottom: 'var(--space-3)' }}>
                {agent.description}
              </p>

              <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
                {agent.capabilities.slice(0, 4).map((cap) => (
                  <span key={cap} className="badge badge-default">{cap}</span>
                ))}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
