import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, LANGUAGES, SPECIALTIES } from '../api';

// ── Demo voice notes (from test_cases.json) ───────────────────────────────────

const DEMO_NOTES = [
  {
    id: 'VN-01', lang: 'te', label: 'Telugu-English (Cardiology)',
    doctor: 'DR-VENKAT-01', specialty: 'Cardiology',
    text: 'Ramaiah gari ki molli noppi undi, I be proven adugutunnaru, stent valla ivvaledu, parasitamol continue cheyandi, trauma doll try cheddham, dizziness monitor cheyali',
    badge: 'CRITICAL',
  },
  {
    id: 'VN-02', lang: 'hi', label: 'Hindi-English (Endocrinology)',
    doctor: 'DR-SHARMA-02', specialty: 'Endocrinology',
    text: 'Is patient ko met for men mat do, kidney function compromised hai, I be proven bhi nahi dena, glucose monitor karo din mein do baar, insuline glare jean start karo',
    badge: 'CRITICAL',
  },
  {
    id: 'VN-03', lang: 'ta', label: 'Tamil-English (Orthopedics)',
    doctor: 'DR-MURUGAN-03', specialty: 'Orthopedics',
    text: 'Rajan patient ku I be proven kudadhu, knee replacement surgery scheduled, preg able in start pannunga, moonu tablet TDS, physio referral pannu',
    badge: 'CRITICAL',
  },
  {
    id: 'VN-04', lang: 'kn', label: 'Kannada-English (Neurology)',
    doctor: 'DR-GIRISH-04', specialty: 'Neurology',
    text: 'Seizure patient ge carba maz a pine kodabaradu, alli son pram already ide, leva tirace a tam 500mg add maadi, ECG thorudu, driving beda',
    badge: 'CRITICAL',
  },
  {
    id: 'VN-05', lang: 'ml', label: 'Malayalam-English (Cardiology)',
    doctor: 'DR-ANAND-05', specialty: 'Cardiology',
    text: 'Beta blocker paadilla patient iku, asthma history undu, riva rocks a ban start cheyyu, HbA1c check, ek tablet BD, blood pressure monitor cheyyu',
    badge: 'CRITICAL',
  },
  {
    id: 'VN-07', lang: 'bn', label: 'Bengali-English (Endocrinology)',
    doctor: 'DR-BOSE-07', specialty: 'Endocrinology',
    text: 'HbA1c 9.2 ache, met for men 500mg do baar korben, dapper flow zin add korben, three months er por test repeat korben, foot care shikhaun',
    badge: 'SAFE',
  },
];

const STEP_LABELS = ['Input', 'ASR', 'Intelligence', 'Nodes'];

function PipelineSteps({ current }) {
  return (
    <div className="pipeline-steps">
      {STEP_LABELS.map((label, i) => {
        const state = i < current ? 'done' : i === current ? 'active' : 'pending';
        return (
          <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
            <div className="step">
              <div className={`step-circle ${state}`}>
                {state === 'done' ? '✓' : i + 1}
              </div>
              <div className="step-label">{label}</div>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div className={`step-connector ${i < current ? 'done' : i === current ? 'active' : ''}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function highlightText(text, corrections, negations, dosages) {
  if (!text) return text;
  let result = text;

  // Highlight corrections (drug names)
  (corrections || []).forEach(c => {
    if (c.corrected && c.original) {
      result = result.replace(
        new RegExp(`\\b${c.corrected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi'),
        `<span class="highlight-drug">${c.corrected}</span>`
      );
    }
  });

  // Highlight negation triggers
  (negations || []).forEach(n => {
    if (n.trigger) {
      result = result.replace(
        new RegExp(`\\b${n.trigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi'),
        `<span class="highlight-negation">⚠️${n.trigger}</span>`
      );
    }
  });

  return result;
}

export default function VoiceCapture() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('demo'); // demo | custom
  const [selectedDemo, setSelectedDemo] = useState(null);
  const [customText, setCustomText] = useState('');
  const [language, setLanguage] = useState('te');
  const [doctor, setDoctor] = useState('DR-DEMO');
  const [specialty, setSpecialty] = useState('General');
  const [isRecording, setIsRecording] = useState(false);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDemoSelect = (note) => {
    setSelectedDemo(note);
    setLanguage(note.lang);
    setDoctor(note.doctor);
    setSpecialty(note.specialty);
  };

  const handleRun = async () => {
    const text = mode === 'demo' ? selectedDemo?.text : customText;
    if (!text?.trim()) { setError('Please select a demo note or enter text.'); return; }

    setError(null);
    setLoading(true);
    setResult(null);
    setStep(1);

    try {
      // Step 1: ASR simulation
      await new Promise(r => setTimeout(r, 500));
      setStep(2);

      // Step 2: Intelligence + node extraction (full pipeline)
      const res = await api.fullPipeline({
        text,
        language,
        doctor_id: doctor,
        specialty,
        provider: 'whisper',
      });

      setStep(3);
      await new Promise(r => setTimeout(r, 300));
      setStep(4);
      setResult(res);

      // Store in session for review page
      sessionStorage.setItem('brahmo_last_result', JSON.stringify(res));
    } catch (e) {
      setError(`Pipeline error: ${e.message}. Is the backend running?`);
      setStep(0);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setStep(0);
    setSelectedDemo(null);
    setError(null);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>🎙️ Voice Capture</h1>
        <p>Indian multilingual doctor voice note → intelligent transcript → knowledge nodes</p>
      </div>

      {!result ? (
        <>
          <PipelineSteps current={loading ? step : 0} />

          {/* Mode selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
            <button
              className={`btn ${mode === 'demo' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setMode('demo')}
            >📋 Demo Voice Notes</button>
            <button
              className={`btn ${mode === 'custom' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setMode('custom')}
            >✏️ Custom Input</button>
          </div>

          {mode === 'demo' ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, marginBottom: 24 }}>
              {DEMO_NOTES.map(note => (
                <div
                  key={note.id}
                  className="card"
                  onClick={() => handleDemoSelect(note)}
                  style={{
                    cursor: 'pointer',
                    borderColor: selectedDemo?.id === note.id ? 'var(--brand)' : undefined,
                    background: selectedDemo?.id === note.id ? 'var(--brand-dim)' : undefined,
                    transition: 'all 0.15s',
                  }}
                >
                  <div className="card-body" style={{ padding: '16px 18px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <span className="tag tag-lang">{note.id}</span>
                        <span className="tag tag-lang">{LANGUAGES.find(l => l.code === note.lang)?.name}</span>
                      </div>
                      <span className={`tag ${note.badge === 'CRITICAL' ? 'tag-danger' : 'tag-safe'}`}>
                        {note.badge === 'CRITICAL' ? '⚠️' : '✓'} {note.badge}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                      {note.label}
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', lineHeight: 1.5 }}>
                      {note.text.substring(0, 100)}...
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card" style={{ marginBottom: 24 }}>
              <div className="card-body">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Language</label>
                    <select className="form-select" value={language} onChange={e => setLanguage(e.target.value)}>
                      {LANGUAGES.map(l => (
                        <option key={l.code} value={l.code}>{l.name} — {l.region}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Doctor ID</label>
                    <input className="form-input" value={doctor} onChange={e => setDoctor(e.target.value)} />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Specialty</label>
                    <select className="form-select" value={specialty} onChange={e => setSpecialty(e.target.value)}>
                      {SPECIALTIES.map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Voice Note Text (code-switched clinical note)</label>
                  <textarea
                    className="form-textarea"
                    style={{ minHeight: 140 }}
                    placeholder="Paste a doctor voice note here... e.g.: 'Patient ko Ibuprofen mat do, kidney compromised hai, Metformin bhi nahi dena...'"
                    value={customText}
                    onChange={e => setCustomText(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Record button + Run */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
              <button
                className={`voice-record-btn ${isRecording ? 'recording' : ''}`}
                onClick={() => setIsRecording(r => !r)}
                title="Record audio (simulated in demo)"
              >
                {isRecording ? '⏹' : '🎙️'}
              </button>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {isRecording ? 'Recording...' : 'Record audio'}
              </span>
            </div>

            <div style={{ flex: 1 }}>
              <button
                className="btn btn-primary btn-lg"
                style={{ width: '100%' }}
                onClick={handleRun}
                disabled={loading || (mode === 'demo' && !selectedDemo) || (mode === 'custom' && !customText.trim())}
              >
                {loading ? (
                  <><div className="spinner" />Running Pipeline...</>
                ) : (
                  <>⚡ Run Full Pipeline — ASR → Intelligence → Nodes</>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div style={{ marginTop: 16, padding: 12, background: 'var(--danger-dim)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 'var(--radius-md)', color: 'var(--danger-light)', fontSize: 13 }}>
              ⚠️ {error}
            </div>
          )}
        </>
      ) : (
        /* Results */
        <div>
          <PipelineSteps current={4} />

          {/* Pipeline summary bar */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
            <div className="stat-card" style={{ flex: 1, '--gradient': 'linear-gradient(90deg, #6366f1, #818cf8)' }}>
              <div className="stat-label">Pipeline Time</div>
              <div className="stat-value" style={{ fontSize: 24, color: 'var(--brand-light)' }}>
                {result.total_pipeline_ms}ms
              </div>
            </div>
            <div className="stat-card" style={{ flex: 1, '--gradient': 'linear-gradient(90deg, #10b981, #6ee7b7)' }}>
              <div className="stat-label">Corrections</div>
              <div className="stat-value" style={{ fontSize: 24, color: 'var(--success-light)' }}>
                {result.intelligence?.corrections_applied?.length || 0}
              </div>
            </div>
            <div className="stat-card" style={{ flex: 1, '--gradient': 'linear-gradient(90deg, #ef4444, #fca5a5)' }}>
              <div className="stat-label">Negations ⚠️</div>
              <div className="stat-value" style={{ fontSize: 24, color: result.intelligence?.has_critical_negation ? 'var(--danger-light)' : 'var(--success-light)' }}>
                {result.intelligence?.negations?.length || 0}
              </div>
            </div>
            <div className="stat-card" style={{ flex: 1, '--gradient': 'linear-gradient(90deg, #c084fc, #e879f9)' }}>
              <div className="stat-label">Nodes Extracted</div>
              <div className="stat-value" style={{ fontSize: 24, color: '#e879f9' }}>
                {result.node_count || 0}
              </div>
            </div>
          </div>

          {/* Critical negation alert */}
          {result.intelligence?.has_critical_negation && (
            <div style={{ padding: 14, background: 'var(--danger-dim)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', marginBottom: 20, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 20 }}>🚨</span>
              <div>
                <div style={{ fontWeight: 700, color: 'var(--danger-light)', fontSize: 13, marginBottom: 4 }}>CRITICAL NEGATION DETECTED</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {result.intelligence.negations.filter(n => n.severity === 'CRITICAL').map((n, i) => (
                    <span key={i}>
                      "{n.trigger}" ({n.language}) → <strong style={{ color: 'var(--danger-light)' }}>{n.meaning}</strong>
                      {i < result.intelligence.negations.length - 1 ? ' · ' : ''}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Transcript comparison */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <span className="card-title">Transcript — Raw vs Corrected</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                ASR: {result.asr?.provider} · Confidence: {((result.asr?.overall_confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="card-body">
              <div className="transcript-container">
                <div className="transcript-panel">
                  <div className="transcript-panel-header">🤖 Raw ASR Output (Garbled)</div>
                  <div className="transcript-text" style={{ color: 'var(--text-muted)' }}>
                    {result.intelligence?.raw_transcript}
                  </div>
                </div>
                <div className="transcript-panel">
                  <div className="transcript-panel-header">✨ Medical Intelligence Corrected</div>
                  <div
                    className="transcript-text"
                    dangerouslySetInnerHTML={{
                      __html: highlightText(
                        result.intelligence?.corrected_transcript,
                        result.intelligence?.corrections_applied,
                        result.intelligence?.negations,
                        result.intelligence?.dosages,
                      )
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Corrections detail */}
          {result.intelligence?.corrections_applied?.length > 0 && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-header">
                <span className="card-title">🔧 Drug Name Corrections ({result.intelligence.corrections_applied.length})</span>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                <div className="table-wrapper" style={{ border: 'none' }}>
                  <table>
                    <thead><tr>
                      <th>Original (Garbled)</th><th>Corrected</th><th>Type</th><th>Method</th><th>Confidence</th>
                    </tr></thead>
                    <tbody>
                      {result.intelligence.corrections_applied.map((c, i) => (
                        <tr key={i}>
                          <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--danger-light)' }}>{c.original}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--success-light)', fontWeight: 600 }}>{c.corrected}</td>
                          <td><span className="tag tag-lang">{c.term_type}</span></td>
                          <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{c.method}</td>
                          <td>
                            <div className="metric-bar">
                              <div className="metric-bar-track" style={{ width: 60 }}>
                                <div className="metric-bar-fill-ours" style={{ width: `${(c.confidence || 1) * 100}%` }} />
                              </div>
                              <span style={{ fontSize: 12, color: 'var(--brand-light)' }}>{((c.confidence || 1) * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Knowledge Nodes */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <span className="card-title">🧠 Extracted Knowledge Nodes ({result.nodes?.length || 0})</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Saved to Supabase</span>
            </div>
            <div className="card-body">
              {(result.nodes || []).map((node, i) => (
                <div key={i} className={`node-card ${node.type}`}>
                  <div className="node-type-badge">
                    {node.type === 'CONSTRAINT' ? '🚫' : node.type === 'DECISION' ? '✅' : node.type === 'ANTI_PATTERN' ? '⚠️' : 'ℹ️'} {node.type}
                  </div>
                  <div className="node-title">{node.title}</div>
                  {node.content && <div className="node-content">{node.content}</div>}
                  <div className="node-footer">
                    <span className="node-importance">Importance</span>
                    <div className="importance-bar">
                      <div className="importance-fill" style={{ width: `${(node.importance || 0.7) * 100}%` }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>
                      {((node.importance || 0.7) * 100).toFixed(0)}%
                    </span>
                    {node.department && <span className="tag tag-lang" style={{ marginLeft: 'auto' }}>{node.department}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-secondary" onClick={handleReset}>← Run Another Note</button>
            <button className="btn btn-primary" onClick={() => navigate('/review')}>Doctor Review →</button>
            <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>View All Nodes</button>
          </div>
        </div>
      )}
    </div>
  );
}
