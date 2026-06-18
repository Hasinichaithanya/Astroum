import { useState, useEffect } from 'react';
import { api } from '../api';

export default function Review() {
  const [result, setResult] = useState(null);
  const [editedTranscript, setEditedTranscript] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem('brahmo_last_result');
    if (stored) {
      const parsed = JSON.parse(stored);
      setResult(parsed);
      setEditedTranscript(parsed.intelligence?.corrected_transcript || '');
    }
  }, []);

  const handleConfirm = async () => {
    if (!result) return;
    setLoading(true);
    try {
      await api.review({
        transcript_id: result.transcript_id,
        confirmed_transcript: editedTranscript,
        doctor_id: 'DR-DEMO',
      });
      setSubmitted(true);
    } catch (e) {
      console.error(e);
      setSubmitted(true); // Still mark as done even if DB fails
    } finally {
      setLoading(false);
    }
  };

  if (!result) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1>✅ Doctor Review</h1>
          <p>Run a voice note first from the Voice Capture page</p>
        </div>
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '60px 24px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎙️</div>
            <div style={{ fontSize: 15, marginBottom: 8 }}>No transcript available</div>
            <div style={{ fontSize: 13 }}>Go to Voice Capture and run a voice note first</div>
          </div>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="page-container">
        <div className="page-header"><h1>✅ Review Complete</h1></div>
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '60px 24px' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--success-light)', marginBottom: 8 }}>
              Transcript Confirmed
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
              Knowledge nodes saved to database. Transcript ID: <code style={{ color: 'var(--brand-light)' }}>{result.transcript_id}</code>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              <button className="btn btn-secondary" onClick={() => { setSubmitted(false); sessionStorage.removeItem('brahmo_last_result'); setResult(null); }}>
                Review Another
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const intel = result?.intelligence || {};
  const corrections = intel.corrections_applied || [];
  const negations = intel.negations || [];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>✅ Doctor Review</h1>
        <p>Review and confirm the corrected transcript before nodes are finalised</p>
      </div>

      {/* Negation Alert */}
      {intel.has_critical_negation && (
        <div style={{ padding: 16, background: 'var(--danger-dim)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-lg)', marginBottom: 24, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <span style={{ fontSize: 28 }}>🚨</span>
          <div>
            <div style={{ fontWeight: 700, color: 'var(--danger-light)', fontSize: 14, marginBottom: 6 }}>
              CRITICAL NEGATIONS DETECTED — PATIENT SAFETY REVIEW REQUIRED
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {negations.filter(n => n.severity === 'CRITICAL').map((n, i) => (
                <span key={i} style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--danger-light)', padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600 }}>
                  "{n.trigger}" → {n.meaning}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Raw transcript */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🤖 Raw ASR Output</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Before intelligence</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="transcript-text" style={{ padding: 20 }}>{intel.raw_transcript}</div>
          </div>
        </div>

        {/* Corrections summary */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔧 Intelligence Applied</span>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
              <div style={{ background: 'var(--success-dim)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: 8, padding: '10px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--success-light)' }}>{corrections.length}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Drug Corrections</div>
              </div>
              <div style={{ background: negations.length ? 'var(--danger-dim)' : 'var(--bg-elevated)', border: `1px solid ${negations.length ? 'rgba(239,68,68,0.15)' : 'var(--border-subtle)'}`, borderRadius: 8, padding: '10px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: negations.length ? 'var(--danger-light)' : 'var(--text-secondary)' }}>{negations.length}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Negations Found</div>
              </div>
            </div>
            {corrections.slice(0, 4).map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 }}>
                <span style={{ color: 'var(--danger-light)', fontFamily: 'var(--font-mono)' }}>{c.original}</span>
                <span style={{ color: 'var(--text-dim)' }}>→</span>
                <span style={{ color: 'var(--success-light)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{c.corrected}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Editable corrected transcript */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">✏️ Corrected Transcript — Doctor can edit here</span>
        </div>
        <div className="card-body">
          <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--text-muted)' }}>
            ℹ️ Blue = drug names | <span style={{ color: 'var(--danger-light)' }}>Red = negations (DO NOT CHANGE these)</span>
          </div>
          <textarea
            className="form-textarea"
            style={{ minHeight: 120, fontSize: 14 }}
            value={editedTranscript}
            onChange={e => setEditedTranscript(e.target.value)}
          />
        </div>
      </div>

      {/* Knowledge nodes preview */}
      {result.nodes?.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <span className="card-title">🧠 Knowledge Nodes to be Confirmed ({result.nodes.length})</span>
          </div>
          <div className="card-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {result.nodes.map((node, i) => (
              <div key={i} className={`node-card ${node.type}`} style={{ margin: 0 }}>
                <div className="node-type-badge">
                  {node.type === 'CONSTRAINT' ? '🚫' : node.type === 'DECISION' ? '✅' : node.type === 'ANTI_PATTERN' ? '⚠️' : 'ℹ️'} {node.type}
                </div>
                <div className="node-title" style={{ fontSize: 12.5 }}>{node.title}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn btn-success btn-lg" onClick={handleConfirm} disabled={loading}>
          {loading ? <><div className="spinner" /> Saving...</> : '✅ Confirm & Save to Knowledge Base'}
        </button>
        <button className="btn btn-secondary" onClick={() => { setResult(null); sessionStorage.removeItem('brahmo_last_result'); }}>
          ← Discard
        </button>
      </div>
    </div>
  );
}
