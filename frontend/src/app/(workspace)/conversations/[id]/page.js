// ============================================================
// SalesOS AI — Conversation Detail (Thread View)
// ============================================================

'use client';

import { useCallback } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { useApi } from '@/lib/hooks';
import { formatDateTime, capitalize } from '@/lib/utils';

export default function ConversationDetailPage() {
  const { id } = useParams();

  const { data: lead } = useApi(
    useCallback(() => api.getLead(id), [id])
  );
  const { data: conversations, loading } = useApi(
    useCallback(() => api.getLeadConversations(id), [id])
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">
            {lead ? `${lead.first_name} ${lead.last_name}` : 'Conversation'}
          </h1>
          <p className="page-subtitle">{lead?.email || 'Loading…'}</p>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 80 }} />
          ))}
        </div>
      ) : !conversations || conversations.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
          <p className="text-secondary">No conversations found for this lead.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {conversations.map((conv) => (
            <ConversationThread key={conv.id} conversation={conv} />
          ))}
        </div>
      )}
    </div>
  );
}

function ConversationThread({ conversation }) {
  const { data: messages, loading } = useApi(
    useCallback(() => api.getMessages(conversation.id), [conversation.id])
  );

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div style={{ fontWeight: 500 }}>
            {conversation.subject || 'Conversation'}
          </div>
          <div className="text-secondary" style={{ fontSize: 'var(--text-xs)' }}>
            {conversation.channel || 'email'} · {formatDateTime(conversation.created_at)}
          </div>
        </div>
        {conversation.ai_analysis && (
          <span className="badge badge-accent">AI Analyzed</span>
        )}
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: 60 }} />
      ) : messages && messages.length > 0 ? (
        <div className="flex flex-col gap-3">
          {messages.map((msg, i) => (
            <div
              key={msg.id || i}
              style={{
                padding: 'var(--space-3) var(--space-4)',
                borderRadius: 'var(--radius-lg)',
                background: msg.direction === 'inbound' ? 'var(--bg-elevated)' : 'var(--accent-muted)',
                borderLeft: msg.direction === 'inbound'
                  ? '3px solid var(--text-tertiary)'
                  : '3px solid var(--accent)',
              }}
            >
              <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  {msg.direction === 'inbound' ? '← Received' : '→ Sent'}
                </span>
                <span className="text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>
                  {formatDateTime(msg.created_at)}
                </span>
              </div>
              <div style={{ fontSize: 'var(--text-sm)', whiteSpace: 'pre-wrap' }}>
                {msg.content || msg.body_text || '(no content)'}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>No messages.</p>
      )}

      {/* AI Analysis Panel */}
      {conversation.ai_analysis && (
        <div
          style={{
            marginTop: 'var(--space-4)',
            padding: 'var(--space-4)',
            background: 'var(--bg-elevated)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--accent-border)',
          }}
        >
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--accent)', marginBottom: 'var(--space-3)' }}>
            ⬡ AI ANALYSIS
          </div>
          <div className="grid grid-cols-3 gap-3">
            {conversation.ai_analysis.sentiment && (
              <AnalysisItem label="Sentiment" value={capitalize(conversation.ai_analysis.sentiment)} />
            )}
            {conversation.ai_analysis.buying_signals && (
              <AnalysisItem
                label="Buying Signals"
                value={conversation.ai_analysis.buying_signals.join(', ') || 'None'}
              />
            )}
            {conversation.ai_analysis.objections && (
              <AnalysisItem
                label="Objections"
                value={conversation.ai_analysis.objections.join(', ') || 'None'}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function AnalysisItem({ label, value }) {
  return (
    <div>
      <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)', marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 'var(--text-sm)' }}>{value}</div>
    </div>
  );
}
