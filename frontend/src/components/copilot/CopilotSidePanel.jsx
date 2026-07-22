// ============================================================
// SalesOS AI — Copilot Side-Panel Drawer
// Floating SDR assistant panel with real-time AI guidance.
// ============================================================

'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export default function CopilotSidePanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Hi! I am your SalesOS AI Copilot. Ask me anything about deals, objections, or request custom outreach drafts!',
      sources: ['Sales Playbook'],
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'draft' | 'prep'

  // Draft state
  const [draftTone, setDraftTone] = useState('professional');
  const [draftResult, setDraftResult] = useState(null);

  const handleSendQuery = async (promptToSend) => {
    const query = promptToSend || inputPrompt;
    if (!query.trim() || loading) return;

    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt('');
    setLoading(true);

    try {
      const res = await api.post('/copilot/query', { prompt: query });
      const data = res.data || {};
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer || 'No answer generated.',
          sources: data.sources || [],
          suggested: data.suggested_actions || [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '⚠️ Failed to connect to Copilot engine. Please check backend status.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDraft = async () => {
    setLoading(true);
    try {
      // Mock or fetch first lead for demo
      const leadsRes = await api.get('/leads?per_page=1');
      const leads = leadsRes.data || [];
      const leadId = leads[0]?.id;

      if (!leadId) {
        setDraftResult({
          subject: 'Sales Automation for Your Team',
          body_text: 'Hi there,\n\nI noticed your team is scaling sales outreach. SalesOS AI helps automate lead qualification and booking 24/7.\n\nBest,\nSDR Team',
        });
        return;
      }

      const res = await api.post('/copilot/draft-email', {
        lead_id: leadId,
        tone: draftTone,
        max_length: 'medium',
      });
      setDraftResult(res.data);
    } catch (err) {
      setDraftResult({
        subject: 'Re: Scaling your SDR team',
        body_text: 'Hi,\n\nFollowing up to see if you had 10 minutes to discuss autonomous sales orchestration.\n\nBest,\nSalesOS AI',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
          color: '#ffffff',
          border: 'none',
          borderRadius: '50px',
          padding: '12px 24px',
          fontWeight: 600,
          boxShadow: '0 8px 24px rgba(147, 51, 234, 0.4)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'transform 0.2s ease',
        }}
      >
        <span>✨</span>
        <span>{isOpen ? 'Close Copilot' : 'AI Sales Copilot'}</span>
      </button>

      {/* Slide-out Drawer */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: '0',
            right: '0',
            width: '420px',
            height: '100vh',
            backgroundColor: '#0f172a',
            borderLeft: '1px solid #1e293b',
            boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
            zIndex: 9998,
            display: 'flex',
            flexDirection: 'column',
            color: '#f8fafc',
          }}
        >
          {/* Drawer Header */}
          <div
            style={{
              padding: '16px 20px',
              borderBottom: '1px solid #1e293b',
              background: '#1e1b4b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.2rem' }}>🤖</span>
              <strong style={{ fontSize: '1.1rem' }}>AI Sales Copilot</strong>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' }}
            >
              ✕
            </button>
          </div>

          {/* Navigation Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', background: '#0f172a' }}>
            <button
              onClick={() => setActiveTab('chat')}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                background: activeTab === 'chat' ? '#1e293b' : 'transparent',
                color: activeTab === 'chat' ? '#38bdf8' : '#94a3b8',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              💬 Copilot Chat
            </button>
            <button
              onClick={() => setActiveTab('draft')}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                background: activeTab === 'draft' ? '#1e293b' : 'transparent',
                color: activeTab === 'draft' ? '#38bdf8' : '#94a3b8',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              ✉️ Email Drafter
            </button>
          </div>

          {/* Tab Content: Chat */}
          {activeTab === 'chat' && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {/* Message History */}
              <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      padding: '12px 16px',
                      borderRadius: '12px',
                      background: msg.role === 'user' ? '#4f46e5' : '#1e293b',
                      color: '#f8fafc',
                      fontSize: '0.9rem',
                      lineHeight: '1.4',
                    }}
                  >
                    <div>{msg.content}</div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#94a3b8' }}>
                        📚 Sources: {msg.sources.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div style={{ alignSelf: 'flex-start', color: '#94a3b8', fontSize: '0.85rem' }}>
                    Thinking with SalesOS AI intelligence…
                  </div>
                )}
              </div>

              {/* Quick Actions Chips */}
              <div style={{ padding: '8px 16px', display: 'flex', gap: '8px', overflowX: 'auto', borderTop: '1px solid #1e293b' }}>
                <button
                  onClick={() => handleSendQuery('How should I handle budget objections?')}
                  style={{
                    padding: '4px 10px',
                    fontSize: '0.75rem',
                    borderRadius: '12px',
                    border: '1px solid #3b82f6',
                    background: 'transparent',
                    color: '#60a5fa',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  💡 Budget Objections
                </button>
                <button
                  onClick={() => handleSendQuery('Give me a 3-step closing playbook')}
                  style={{
                    padding: '4px 10px',
                    fontSize: '0.75rem',
                    borderRadius: '12px',
                    border: '1px solid #a855f7',
                    background: 'transparent',
                    color: '#c084fc',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  🎯 Closing Playbook
                </button>
              </div>

              {/* Input Box */}
              <div style={{ padding: '12px 16px', borderTop: '1px solid #1e293b', display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Ask SalesOS AI Copilot…"
                  value={inputPrompt}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendQuery()}
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: '1px solid #334155',
                    background: '#020617',
                    color: '#ffffff',
                    outline: 'none',
                  }}
                />
                <button
                  onClick={() => handleSendQuery()}
                  disabled={loading}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '8px',
                    border: 'none',
                    background: '#4f46e5',
                    color: '#ffffff',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Send
                </button>
              </div>
            </div>
          )}

          {/* Tab Content: Email Drafter */}
          {activeTab === 'draft' && (
            <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '6px', color: '#94a3b8' }}>
                  Copy Tone:
                </label>
                <select
                  value={draftTone}
                  onChange={(e) => setDraftTone(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: '#020617',
                    color: '#fff',
                    border: '1px solid #334155',
                  }}
                >
                  <option value="professional">Professional & Direct</option>
                  <option value="friendly">Warm & Friendly</option>
                  <option value="persuasive">High Urgency / Persuasive</option>
                  <option value="concise">Short & Punchy</option>
                </select>
              </div>

              <button
                onClick={handleGenerateDraft}
                disabled={loading}
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {loading ? 'Drafting Email…' : '✨ Generate Email Draft'}
              </button>

              {draftResult && (
                <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
                  <div style={{ fontWeight: 600, marginBottom: '8px', color: '#38bdf8' }}>
                    Subject: {draftResult.subject}
                  </div>
                  <div style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap', color: '#cbd5e1', lineHeight: '1.5' }}>
                    {draftResult.body_text}
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(draftResult.body_text)}
                    style={{
                      marginTop: '12px',
                      padding: '6px 12px',
                      fontSize: '0.75rem',
                      background: '#334155',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    📋 Copy Text
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}
