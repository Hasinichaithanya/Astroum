import { useState, useEffect } from 'react';
import { api } from '../api';

const MOCK_NODES = [
  { id: 'KN-001', type: 'CONSTRAINT', title: 'DO NOT give Ibuprofen — cardiac stent contraindication', content: 'Patient has cardiac stent. NSAIDs contraindicated due to increased thrombosis risk.', importance: 1.0, department: 'Cardiology', created_by: 'DR-VENKAT-01' },
  { id: 'KN-002', type: 'DECISION', title: 'Start Insulin Glargine for glycaemic control', content: 'Initiate long-acting insulin. Monitor fasting glucose daily. Target FBG 80-130 mg/dL.', importance: 0.9, department: 'Endocrinology', created_by: 'DR-SHARMA-02' },
  { id: 'KN-003', type: 'CONSTRAINT', title: 'DO NOT give Metformin — CKD eGFR <45', content: 'Renal impairment. Metformin in CKD causes lactic acidosis. eGFR 35 — absolute contraindication.', importance: 1.0, department: 'Nephrology', created_by: 'DR-SURESH-14' },
  { id: 'KN-004', type: 'DECISION', title: 'Salbutamol inhaler 2 puffs BD for COPD', content: 'COPD management. Short-acting bronchodilator. 2 puffs twice daily.', importance: 0.9, department: 'Pulmonology', created_by: 'DR-KRISHNA-09' },
  { id: 'KN-005', type: 'ANTI_PATTERN', title: 'NSAIDs + Methotrexate — Methotrexate toxicity', content: 'Concurrent NSAID use with Methotrexate reduces renal clearance → bone marrow suppression risk.', importance: 0.95, department: 'Rheumatology', created_by: 'DR-MEHTA-13' },
  { id: 'KN-006', type: 'FACT', title: 'HbA1c 9.2 — poor glycaemic control', content: 'Baseline HbA1c measurement. Target <7% with treatment intensification.', importance: 0.85, department: 'Endocrinology', created_by: 'DR-BOSE-07' },
  { id: 'KN-007', type: 'CONSTRAINT', title: 'DO NOT give Beta-blockers — asthma contraindication', content: 'Asthma history documented. Beta-blockers cause fatal bronchospasm in asthma patients.', importance: 1.0, department: 'Cardiology', created_by: 'DR-ANAND-05' },
  { id: 'KN-008', type: 'DECISION', title: 'Methotrexate 15mg weekly with Folic Acid', content: 'DMARD therapy for RA. Folic acid reduces Methotrexate toxicity. Monthly LFT monitoring required.', importance: 0.9, department: 'Rheumatology', created_by: 'DR-MEHTA-13' },
  { id: 'KN-009', type: 'CONSTRAINT', title: 'STOP Insulin Aspart — DO NOT discontinue in Type 1 DM', content: 'Type 1 DM: stopping insulin causes DKA within hours. Never withold insulin.', importance: 1.0, department: 'Endocrinology', created_by: 'DR-JOSHI-20' },
  { id: 'KN-010', type: 'FACT', title: 'CKD Stage 3, eGFR 35 — drug dose adjustments required', content: 'Multiple drug dose adjustments needed. Avoid renally-cleared medications.', importance: 0.9, department: 'Nephrology', created_by: 'DR-SURESH-14' },
];

const TYPE_COLORS = {
  CONSTRAINT: { bg: 'var(--constraint-bg)', border: 'var(--constraint-color)', color: 'var(--constraint-color)', emoji: '🚫' },
  DECISION: { bg: 'var(--decision-bg)', border: 'var(--decision-color)', color: 'var(--decision-color)', emoji: '✅' },
  ANTI_PATTERN: { bg: 'var(--antipat-bg)', border: 'var(--antipat-color)', color: 'var(--antipat-color)', emoji: '⚠️' },
  FACT: { bg: 'var(--fact-bg)', border: 'var(--fact-color)', color: 'var(--fact-color)', emoji: 'ℹ️' },
};

export default function Dashboard() {
  const [nodes, setNodes] = useState(MOCK_NODES);
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadNodes();
  }, []);

  const loadNodes = async () => {
    setLoading(true);
    try {
      const res = await api.getNodes({ limit: 50 });
      if (res.nodes?.length > 0) {
        setNodes([...res.nodes, ...MOCK_NODES.slice(res.nodes.length)]);
      }
    } catch {
      // Use mock data
    } finally {
      setLoading(false);
    }
  };

  const filtered = nodes.filter(n => {
    const matchType = filter === 'ALL' || n.type === filter;
    const matchSearch = !search || n.title.toLowerCase().includes(search.toLowerCase()) || n.content?.toLowerCase().includes(search.toLowerCase());
    return matchType && matchSearch;
  });

  const counts = {
    ALL: nodes.length,
    CONSTRAINT: nodes.filter(n => n.type === 'CONSTRAINT').length,
    DECISION: nodes.filter(n => n.type === 'DECISION').length,
    ANTI_PATTERN: nodes.filter(n => n.type === 'ANTI_PATTERN').length,
    FACT: nodes.filter(n => n.type === 'FACT').length,
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>🧠 Knowledge Node Dashboard</h1>
        <p>All clinical knowledge extracted from doctor voice notes, stored and searchable</p>
      </div>

      {/* Stats */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        {[
          { key: 'ALL', label: 'Total Nodes', gradient: 'linear-gradient(90deg, #6366f1, #818cf8)' },
          { key: 'CONSTRAINT', label: 'Constraints 🚫', gradient: 'linear-gradient(90deg, #ef4444, #fca5a5)' },
          { key: 'DECISION', label: 'Decisions ✅', gradient: 'linear-gradient(90deg, #6366f1, #c084fc)' },
          { key: 'ANTI_PATTERN', label: 'Anti-Patterns ⚠️', gradient: 'linear-gradient(90deg, #f59e0b, #fcd34d)' },
          { key: 'FACT', label: 'Facts ℹ️', gradient: 'linear-gradient(90deg, #10b981, #6ee7b7)' },
        ].map(({ key, label, gradient }) => (
          <div key={key} className="stat-card" style={{ '--gradient': gradient, cursor: 'pointer', borderColor: filter === key ? 'var(--brand)' : undefined }} onClick={() => setFilter(key)}>
            <div className="stat-label">{label}</div>
            <div className="stat-value" style={{ fontSize: 36 }}>{counts[key]}</div>
          </div>
        ))}
      </div>

      {/* Filter + Search */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center' }}>
        <input
          className="form-input"
          style={{ flex: 1, maxWidth: 400 }}
          placeholder="🔍 Search nodes..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div style={{ display: 'flex', gap: 6 }}>
          {['ALL', 'CONSTRAINT', 'DECISION', 'ANTI_PATTERN', 'FACT'].map(t => (
            <button
              key={t}
              className={`btn btn-sm ${filter === t ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(t)}
            >
              {t === 'ALL' ? 'All' : t.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadNodes}>↻ Refresh</button>
      </div>

      {/* Nodes grid */}
      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 140 }} />)}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
          {filtered.map((node, i) => {
            const meta = TYPE_COLORS[node.type] || TYPE_COLORS.FACT;
            return (
              <div
                key={node.id || i}
                style={{
                  background: meta.bg,
                  border: `1px solid ${meta.border}30`,
                  borderLeft: `3px solid ${meta.border}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 18px',
                  transition: 'all 0.15s',
                }}
                className="card"
                onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'none'}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.8px', textTransform: 'uppercase', color: meta.border, background: `${meta.border}20`, padding: '3px 8px', borderRadius: 4 }}>
                    {meta.emoji} {node.type}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: node.importance >= 0.9 ? 'var(--danger-light)' : 'var(--text-muted)' }}>
                    {node.importance >= 0.9 ? '🔴' : node.importance >= 0.7 ? '🟡' : '🟢'} {((node.importance || 0.7) * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6, lineHeight: 1.4 }}>
                  {node.title}
                </div>
                {node.content && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 10 }}>
                    {node.content}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {node.department && <span className="tag tag-lang">{node.department}</span>}
                  {node.created_by && <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{node.created_by}</span>}
                  {node.id && <span style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 'auto', fontFamily: 'var(--font-mono)' }}>{node.id?.substring(0, 12)}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {filtered.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
          <div>No nodes match your filter</div>
        </div>
      )}
    </div>
  );
}
