// ============================================================
// SalesOS AI — Agent Detail Page
// ============================================================

'use client';

import { useParams } from 'next/navigation';

// Full agent metadata — matches registry.py registrations
const AGENT_DATA = {
  qualification: {
    name: 'Qualification Agent',
    type: 'qualification',
    version: 'v1.0',
    module: 'app.agents.qualification.QualificationAgent',
    description: 'Scores and qualifies inbound leads using AI analysis of company, role, and intent signals.',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Lead scoring (0-100)', 'Priority classification (critical/high/medium/low)', 'Intent detection', 'Urgency assessment', 'Reasoning explanation'],
    input_schema: {
      email: 'string (required)',
      first_name: 'string',
      last_name: 'string',
      job_title: 'string',
      company_name: 'string',
      message: 'string',
    },
    output_schema: {
      score: 'int (0-100)',
      priority: 'critical | high | medium | low',
      intent: 'string',
      urgency: 'critical | high | medium | low',
      reasoning: 'string',
      confidence: 'float (0-1)',
    },
    prompt_template: `You are SalesOS AI's Lead Qualification Agent.

Analyze the lead and return a qualification assessment:
- Score (0-100)
- Priority (critical/high/medium/low)
- Intent detection
- Urgency assessment
- Reasoning`,
  },
  enrichment: {
    name: 'Enrichment Agent',
    type: 'enrichment',
    version: 'v1.0',
    module: 'app.agents.enrichment.EnrichmentAgent',
    description: 'Enriches leads with company data, firmographic information, and technology stack.',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Company lookup', 'Firmographics', 'Technology stack', 'Social profiles', 'Revenue estimation'],
    input_schema: { email: 'string', company_name: 'string', website: 'string' },
    output_schema: { company_data: 'object', industry: 'string', employee_count: 'int', tech_stack: 'array' },
    prompt_template: 'Enrichment prompt (v1) — see app/prompts/enrichment_v1.py',
  },
  conversation_intelligence: {
    name: 'Conversation Intelligence Agent',
    type: 'conversation_intelligence',
    version: 'v1.0',
    module: 'app.agents.conversation_intelligence.ConversationIntelligenceAgent',
    description: '9-dimension conversation analysis with memory.',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Sentiment (positive/neutral/negative)', 'Buying signals', 'Objections', 'Risk level', 'Customer stage', 'Pain points', 'Decision criteria', 'Urgency signals', 'Follow-up recommendation'],
    input_schema: { conversation_history: 'array', lead_context: 'object', memory: 'array' },
    output_schema: { sentiment: 'string', buying_signals: 'array', objections: 'array', risk_level: 'string', customer_stage: 'string', recommended_action: 'string' },
    prompt_template: 'CI prompt (v1) — see app/prompts/conversation_intelligence_v1.py',
  },
  outreach: {
    name: 'Outreach Agent',
    type: 'outreach',
    version: 'v1.0',
    module: 'app.agents.outreach.OutreachAgent',
    description: 'Generates personalized outreach emails.',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Subject line generation', 'Body personalization', 'Tone matching', 'CTA optimization'],
    input_schema: { lead_data: 'object', qualification: 'object', email_type: 'string' },
    output_schema: { subject: 'string', body_html: 'string', body_text: 'string', tone: 'string', reasoning: 'string' },
    prompt_template: 'Outreach prompt (v1) — see app/prompts/outreach_v1.py',
  },
  booking: {
    name: 'Booking Agent',
    type: 'booking',
    version: 'v1.0',
    module: 'app.agents.booking.BookingAgent',
    description: 'Determines optimal meeting setup.',
    prompt_version: 'v1',
    status: 'active',
    capabilities: ['Meeting type selection', 'Duration recommendation', 'Title generation', 'Description generation', 'Time window ranking'],
    input_schema: { lead_data: 'object', qualification: 'object', conversation_summary: 'string', available_slots: 'string' },
    output_schema: { meeting_type: 'string', duration_minutes: 'int', title: 'string', description: 'string', preferred_time_window: 'string' },
    prompt_template: 'Booking prompt (v1) — see app/prompts/booking_v1.py',
  },
};

export default function AgentDetailPage() {
  const { type } = useParams();
  const agent = AGENT_DATA[type];

  if (!agent) {
    return (
      <div className="card">
        <p className="text-danger">Agent &ldquo;{type}&rdquo; not found.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{agent.name}</h1>
          <p className="page-subtitle">{agent.module}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="badge badge-success">{agent.status}</span>
          <span className="badge badge-accent">{agent.version}</span>
          <span className="badge badge-default">Prompt {agent.prompt_version}</span>
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-2 gap-4">
        {/* Left: Info + Capabilities */}
        <div className="flex flex-col gap-4">
          <div className="card">
            <div className="card-header">
              <div className="card-title">Description</div>
            </div>
            <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-relaxed)' }}>
              {agent.description}
            </p>
          </div>

          <div className="card">
            <div className="card-header">
              <div className="card-title">Capabilities</div>
            </div>
            <div className="flex flex-col gap-2">
              {agent.capabilities.map((cap) => (
                <div key={cap} className="flex items-center gap-2">
                  <span style={{ color: 'var(--success)', fontSize: 'var(--text-xs)' }}>✓</span>
                  <span style={{ fontSize: 'var(--text-sm)' }}>{cap}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: I/O Schema */}
        <div className="flex flex-col gap-4">
          <div className="card">
            <div className="card-header">
              <div className="card-title">Input Schema</div>
            </div>
            <div
              style={{
                background: 'var(--bg-primary)',
                padding: 'var(--space-4)',
                borderRadius: 'var(--radius-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-sm)',
              }}
            >
              {Object.entries(agent.input_schema).map(([key, val]) => (
                <div key={key} style={{ marginBottom: 4 }}>
                  <span style={{ color: 'var(--accent-hover)' }}>{key}</span>
                  <span className="text-tertiary">: </span>
                  <span className="text-secondary">{val}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div className="card-title">Output Schema</div>
            </div>
            <div
              style={{
                background: 'var(--bg-primary)',
                padding: 'var(--space-4)',
                borderRadius: 'var(--radius-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-sm)',
              }}
            >
              {Object.entries(agent.output_schema).map(([key, val]) => (
                <div key={key} style={{ marginBottom: 4 }}>
                  <span style={{ color: 'var(--success)' }}>{key}</span>
                  <span className="text-tertiary">: </span>
                  <span className="text-secondary">{val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Prompt Preview */}
      <div className="card" style={{ marginTop: 'var(--space-4)' }}>
        <div className="card-header">
          <div className="card-title">Prompt Template ({agent.prompt_version})</div>
          <span className="badge badge-accent">Active</span>
        </div>
        <pre
          style={{
            background: 'var(--bg-primary)',
            padding: 'var(--space-4)',
            borderRadius: 'var(--radius-md)',
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
            overflow: 'auto',
            maxHeight: 300,
            border: '1px solid var(--border)',
          }}
        >
          {agent.prompt_template}
        </pre>
      </div>
    </div>
  );
}
