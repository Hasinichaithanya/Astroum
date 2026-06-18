const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

async function request(method, path, body = null, isForm = false) {
  const opts = {
    method,
    headers: isForm ? {} : { 'Content-Type': 'application/json' },
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  };
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${method} ${path} failed: ${res.status} ${err}`);
  }
  return res.json();
}

export const api = {
  health: () => request('GET', '/health'),

  // Pipeline
  transcribeText: (body) => request('POST', '/transcribe', body),
  fullPipeline: (body) => request('POST', '/pipeline', body),
  review: (body) => request('POST', '/review', body),
  extractNodes: (body) => request('POST', '/extract-nodes', body),

  // Data
  getNodes: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request('GET', `/nodes${q ? '?' + q : ''}`);
  },
  getTranscripts: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request('GET', `/transcripts${q ? '?' + q : ''}`);
  },
  getEvaluations: () => request('GET', '/evaluations'),
  getCostAnalysis: () => request('GET', '/cost-analysis'),
  getBenchmarkResults: () => request('GET', '/benchmark/results'),
  runBenchmark: (body) => request('POST', '/benchmark/run', body),

  // Intelligence test
  testIntelligence: (text) => request('GET', `/intelligence/test?text=${encodeURIComponent(text)}`),
};

export const LANGUAGES = [
  { code: 'te', name: 'Telugu', flag: '🇮🇳', region: 'Andhra/Telangana' },
  { code: 'hi', name: 'Hindi', flag: '🇮🇳', region: 'North India' },
  { code: 'ta', name: 'Tamil', flag: '🇮🇳', region: 'Tamil Nadu' },
  { code: 'kn', name: 'Kannada', flag: '🇮🇳', region: 'Karnataka' },
  { code: 'ml', name: 'Malayalam', flag: '🇮🇳', region: 'Kerala' },
  { code: 'mr', name: 'Marathi', flag: '🇮🇳', region: 'Maharashtra' },
  { code: 'bn', name: 'Bengali', flag: '🇮🇳', region: 'West Bengal' },
  { code: 'gu', name: 'Gujarati', flag: '🇮🇳', region: 'Gujarat' },
];

export const SPECIALTIES = [
  'General', 'Cardiology', 'Endocrinology', 'Neurology', 'Orthopedics',
  'Gastroenterology', 'Pulmonology', 'Nephrology', 'Psychiatry',
  'Rheumatology', 'Oncology', 'Obstetrics', 'Hepatology', 'Geriatrics',
];

export const NODE_TYPE_META = {
  CONSTRAINT: { label: 'CONSTRAINT', emoji: '🚫', color: '#ef4444', description: 'Must NOT happen' },
  DECISION: { label: 'DECISION', emoji: '✅', color: '#6366f1', description: 'Clinical decision' },
  ANTI_PATTERN: { label: 'ANTI_PATTERN', emoji: '⚠️', color: '#f59e0b', description: 'Pattern to avoid' },
  FACT: { label: 'FACT', emoji: 'ℹ️', color: '#10b981', description: 'Clinical fact' },
};

export function formatMs(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatINR(amount) {
  if (amount === 0) return '₹0';
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
  return `₹${amount.toFixed(0)}`;
}
