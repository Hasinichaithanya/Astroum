import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import './index.css';

import VoiceCapture from './pages/VoiceCapture';
import Dashboard from './pages/Dashboard';
import Review from './pages/Review';
import Evaluation from './pages/Evaluation';
import CostAnalysis from './pages/CostAnalysis';

// ── Icons (inline SVG to avoid icon package dependency) ──────────────────────

const Icons = {
  Mic: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  ),
  Grid: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  ),
  CheckSquare: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
      <polyline points="9 11 12 14 22 4"/>
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
    </svg>
  ),
  BarChart: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
      <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
    </svg>
  ),
  DollarSign: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
      <line x1="12" y1="1" x2="12" y2="23"/>
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>
  ),
};

// ── Toast Context ─────────────────────────────────────────────────────────────

let _addToast = null;
export function useToast() {
  return { toast: _addToast || (() => {}) };
}

function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  _addToast = useCallback((msg, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const typeColors = { success: '#10b981', danger: '#ef4444', info: '#6366f1', warning: '#f59e0b' };

  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className="toast">
          <span style={{ color: typeColors[t.type] || typeColors.info, fontSize: 16 }}>
            {t.type === 'success' ? '✓' : t.type === 'danger' ? '✕' : 'ℹ'}
          </span>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-text">BRAHMO</div>
        <div className="logo-sub">Voice → Knowledge</div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Pipeline</div>

        <NavLink to="/" end className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
          <Icons.Mic />
          Voice Capture
        </NavLink>

        <NavLink to="/review" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
          <Icons.CheckSquare />
          Doctor Review
        </NavLink>

        <NavLink to="/dashboard" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
          <Icons.Grid />
          Knowledge Nodes
          <span className="nav-badge">DB</span>
        </NavLink>

        <div className="nav-section-label">Research</div>

        <NavLink to="/evaluation" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
          <Icons.BarChart />
          ASR Evaluation
        </NavLink>

        <NavLink to="/cost" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
          <Icons.DollarSign />
          Cost Analysis
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="asr-badge">
          <div className="asr-badge-dot" />
          <div>
            <div className="asr-badge-text">Whisper Base</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>CPU · On-premise</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<VoiceCapture />} />
            <Route path="/review" element={<Review />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/evaluation" element={<Evaluation />} />
            <Route path="/cost" element={<CostAnalysis />} />
          </Routes>
        </main>
        <ToastContainer />
      </div>
    </BrowserRouter>
  );
}
