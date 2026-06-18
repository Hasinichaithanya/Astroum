import { useState, useEffect } from 'react';
import { formatINR } from '../api';

const COSTS = {
  whisper: { label: 'faster-whisper', color: '#6366f1', costPerHour: 0 },
  google: { label: 'Google Speech', color: '#ef4444', costPerHour: 60 },
};

function calcCosts(hospitals, provider) {
  const doctors = hospitals * 30;
  const notesPerDay = doctors * 20;
  const secondsPerNote = 30;
  const dailySeconds = notesPerDay * secondsPerNote;
  const dailyHours = dailySeconds / 3600;
  const monthlyHours = dailyHours * 25;

  const costPerHour = COSTS[provider].costPerHour;
  const asrMonthly = monthlyHours * costPerHour;
  const infraMonthly = 500 + (hospitals * 800);
  const groqMonthly = (notesPerDay * 25) * 0.002;  // ₹0.002 per Groq call
  const totalMonthly = asrMonthly + infraMonthly + groqMonthly;
  const nodesMonthly = notesPerDay * 25 * 4.5;
  const costPerNode = nodesMonthly > 0 ? totalMonthly / nodesMonthly : 0;

  return {
    hospitals,
    doctors,
    dailyNotes: notesPerDay,
    dailyHours: dailyHours.toFixed(1),
    monthlyHours: monthlyHours.toFixed(0),
    asrMonthly,
    infraMonthly,
    groqMonthly,
    totalMonthly,
    annualCost: totalMonthly * 12,
    nodesMonthly,
    costPerNode,
  };
}

export default function CostAnalysis() {
  const [hospitals, setHospitals] = useState(1);
  const [provider, setProvider] = useState('whisper');

  const costs = calcCosts(hospitals, provider);
  const comparison = calcCosts(hospitals, provider === 'whisper' ? 'google' : 'whisper');
  const savings = comparison.totalMonthly - costs.totalMonthly;

  const breakeven = Math.ceil(
    (500) / Math.max(COSTS.google.costPerHour * (30 * 20 * 30 / 3600 * 25), 1)
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>💰 Cost Analysis</h1>
        <p>Real cost at scale — 1 hospital to 50 hospitals, with break-even analysis</p>
      </div>

      {/* Control */}
      <div className="card" style={{ marginBottom: 28 }}>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 12 }}>
                Number of Hospitals: <span style={{ color: 'var(--brand-light)', fontSize: 18 }}>{hospitals}</span>
              </div>
              <input
                type="range"
                min="1" max="50" value={hospitals}
                onChange={e => setHospitals(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--brand)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                <span>1 hospital</span><span>25</span><span>50 hospitals</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 10 }}>Provider</div>
              <div style={{ display: 'flex', gap: 8 }}>
                {Object.entries(COSTS).map(([key, val]) => (
                  <button
                    key={key}
                    className={`btn ${provider === key ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setProvider(key)}
                  >
                    {val.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Big numbers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        {[
          { label: 'Monthly Cost', value: formatINR(costs.totalMonthly), sub: 'Total infrastructure', color: costs.totalMonthly === 0 ? 'var(--success-light)' : 'var(--brand-light)' },
          { label: 'Annual Cost', value: formatINR(costs.annualCost), sub: 'Per year', color: 'var(--brand-light)' },
          { label: 'Cost per Node', value: costs.costPerNode < 0.01 ? '< ₹0.01' : formatINR(costs.costPerNode), sub: 'Per knowledge node', color: 'var(--success-light)' },
          { label: 'Monthly Audio', value: `${costs.monthlyHours}h`, sub: `${costs.doctors} doctors × 20 notes/day`, color: 'var(--text-primary)' },
        ].map((s, i) => (
          <div key={i} className="stat-card" style={{ '--gradient': `linear-gradient(90deg, ${COSTS[provider].color}, ${COSTS[provider].color}80)` }}>
            <div className="stat-label">{s.label}</div>
            <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: -1, color: s.color, lineHeight: 1, marginBottom: 4 }}>{s.value}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Cost breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <div className="card">
          <div className="card-header"><span className="card-title">Monthly Cost Breakdown</span></div>
          <div className="card-body">
            {[
              { label: `ASR (${COSTS[provider].label})`, value: costs.asrMonthly, color: provider === 'whisper' ? 'var(--success)' : 'var(--danger)' },
              { label: 'Infrastructure (servers/DB)', value: costs.infraMonthly, color: 'var(--brand)' },
              { label: 'LLM Extraction (Groq)', value: costs.groqMonthly, color: 'var(--warning)' },
            ].map((item, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.label}</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: item.color }}>{formatINR(item.value)}/mo</span>
                </div>
                <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${costs.totalMonthly > 0 ? (item.value / costs.totalMonthly) * 100 : (i === 1 ? 80 : i === 2 ? 18 : 2)}%`, background: item.color, borderRadius: 3, transition: 'width 0.8s' }} />
                </div>
              </div>
            ))}
            <div style={{ paddingTop: 12, borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Total</span>
              <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--brand-light)' }}>{formatINR(costs.totalMonthly)}/mo</span>
            </div>
          </div>
        </div>

        {/* Scale comparison */}
        <div className="card">
          <div className="card-header"><span className="card-title">Scale Scenarios</span></div>
          <div className="card-body">
            {[1, 10, 30, 50].map(h => {
              const c = calcCosts(h, provider);
              return (
                <div key={h} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, padding: '10px 12px', background: hospitals === h ? 'var(--brand-dim)' : 'var(--bg-elevated)', borderRadius: 8, cursor: 'pointer', border: hospitals === h ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent' }}
                  onClick={() => setHospitals(h)}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', width: 100 }}>{h} hospital{h > 1 ? 's' : ''}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.doctors} doctors · {c.dailyHours}h/day</div>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: c.totalMonthly < 5000 ? 'var(--success-light)' : c.totalMonthly < 50000 ? 'var(--warning-light)' : 'var(--danger-light)' }}>
                    {formatINR(c.totalMonthly)}/mo
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Whisper vs Google comparison */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">🆚 faster-whisper vs Google Cloud Speech — {hospitals} Hospital{hospitals > 1 ? 's' : ''}</span>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {[
              { key: 'whisper', label: 'faster-whisper (Our Choice)', chosen: true },
              { key: 'google', label: 'Google Cloud Speech', chosen: false },
            ].map(({ key, label, chosen }) => {
              const c = calcCosts(hospitals, key);
              return (
                <div key={key} style={{ padding: 20, background: chosen ? 'var(--success-dim)' : 'var(--danger-dim)', border: `1px solid ${chosen ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`, borderRadius: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: chosen ? 'var(--success-light)' : 'var(--danger-light)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.8 }}>
                    {chosen ? '✅ CHOSEN' : '❌ REJECTED'} · {label}
                  </div>
                  <div style={{ fontSize: 36, fontWeight: 900, letterSpacing: -1, color: chosen ? 'var(--success-light)' : 'var(--danger-light)', lineHeight: 1, marginBottom: 6 }}>
                    {formatINR(c.totalMonthly)}<span style={{ fontSize: 16, fontWeight: 500 }}>/mo</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Annual: {formatINR(c.annualCost)} · ₹{c.costPerNode < 0.01 ? '<0.01' : c.costPerNode.toFixed(2)}/node
                  </div>
                  {!chosen && savings > 0 && (
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--success-light)', background: 'var(--success-dim)', padding: '6px 10px', borderRadius: 6 }}>
                      Switch to Whisper → Save {formatINR(savings)}/month
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ marginTop: 20, padding: 14, background: 'var(--bg-elevated)', borderRadius: 10, fontSize: 13, color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>Break-even analysis:</strong> At <strong style={{ color: 'var(--brand-light)' }}>hospital #1</strong>, self-hosted Whisper is already {COSTS.google.costPerHour > 0 ? formatINR(calcCosts(1, 'google').totalMonthly - calcCosts(1, 'whisper').totalMonthly) : 'significantly'} cheaper per month. Google Speech becomes exponentially more expensive at scale. At 50 hospitals, Whisper saves <strong style={{ color: 'var(--success-light)' }}>{formatINR(calcCosts(50, 'google').totalMonthly - calcCosts(50, 'whisper').totalMonthly)}/month.</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
