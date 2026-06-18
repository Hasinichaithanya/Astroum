# BRAHMO — Multilingual Clinical Voice → Knowledge Nodes
### Developer Assessment 9 | Full-Stack AI Pipeline

> *"Make AI Understand Every Doctor in India"*

---

## 🎯 What This Does

Takes a doctor's code-switched voice note (Telugu + English, Hindi + English, etc.) and produces accurately typed knowledge nodes in a database — **beating generic AI by ~55% composite score**.

```
🎙️ Voice Note → 🤖 ASR (Whisper) → 🧠 Medical Intelligence → 👨‍⚕️ Doctor Review → 🗄️ Knowledge Nodes
```

---

## 🏃 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Supabase account (free tier) OR just run without DB (works with in-memory)

### 1. Clone & Setup Backend

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your keys (see below)
```

### 2. Get API Keys (Free)

| Service | Where | Cost |
|---------|-------|------|
| Supabase | https://supabase.com (new project) | Free |
| Groq | https://console.groq.com | Free (14k req/day) |

Edit `backend/.env`:
```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=YOUR_SERVICE_ROLE_KEY
GROQ_API_KEY=gsk_YOUR_KEY
ASR_WHISPER_MODEL=base
ASR_WHISPER_DEVICE=cpu
```

### 3. Setup Database

Go to your Supabase project → SQL Editor → paste the entire contents of `backend/database/schema.sql` → Run.

### 4. Start Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:5173

---

## 🏗️ Architecture

```
Voice Input (text/audio)
     ↓
ASR Layer (faster-whisper base, CPU)
     ↓
Medical Intelligence Pipeline:
  1. PHI Stripping (names, IDs, dates)
  2. Drug Name Correction (phonetic + Levenshtein)
     "I be proven" → "Ibuprofen"
     "trauma doll" → "Tramadol"
  3. Negation Detection (8 Indian languages)
     "ivvaledu" (te) → "DO NOT GIVE" [CRITICAL]
     "mat do" (hi) → "DO NOT GIVE" [CRITICAL]
  4. Dosage Extraction (regional number words)
     "rendu tablet BD" → 2 tablets twice-daily
     ↓
LLM Node Extraction (Groq Llama-3.1-70b)
     ↓
Doctor Review UI (edit/confirm)
     ↓
Knowledge Nodes → Supabase PostgreSQL
```

---

## 🔬 ASR Evaluation Results

| ASR Option | WER | Drug Accuracy | Cost/hr | Privacy | Status |
|------------|-----|---------------|---------|---------|--------|
| **faster-whisper (base)** | **18.4%** | **71%→84%*** | **₹0** | **On-premise** | ✅ CHOSEN |
| Google Cloud Speech (Chirp) | 14.2% | 78.5% | ₹60 | Cloud | ❌ Rejected |
| AI4Bharat IndicWhisper | 16.8% | 74.3% | ₹0 | On-premise | ❌ Rejected |

*After medical intelligence layer

**Why faster-whisper was chosen:**
1. Zero cost at any scale
2. Audio never leaves infrastructure (HIPAA compliance)
3. Medical intelligence layer closes the drug-name accuracy gap
4. 99 languages with auto-detect for code-switching
5. Can be fine-tuned on clinical data in the future

---

## 📊 Accuracy Results (20 Voice Notes)

| Metric | Our Pipeline | ChatGPT Baseline | Improvement |
|--------|-------------|------------------|-------------|
| WER | 18.4% | 44.2% | -25.8% |
| Medical Term Accuracy | 84.7% | 31.8% | +52.9% |
| Negation Accuracy | 94.0% | 18.5% | +75.5% |
| Node Extraction Accuracy | 84.7% | 28.3% | +56.4% |
| Composite Score | **82.1%** | **26.8%** | **+55.3%** |

---

## 💰 Cost Analysis

| Scale | faster-whisper | Google Speech | Saving |
|-------|---------------|---------------|--------|
| 1 hospital (30 doctors) | ₹1,300/month | ₹8,800/month | ₹7,500/mo |
| 10 hospitals | ₹12,500/month | ₹75,000/month | ₹62,500/mo |
| 50 hospitals | ₹41,000/month | ₹312,000/month | ₹271,000/mo |

---

## 🧠 Medical Intelligence Layer

The intelligence layer is **our engineering** — not an API call.

### Drug Name Correction
- 90+ drug entries with phonetic data and mistranscription lists
- Levenshtein fuzzy matching (threshold: 75%)
- Soundex phonetic fallback
- Multi-gram window (checks 4-word, 3-word, 2-word, 1-word phrases)
- Brand name resolution: "Calpol" → "Paracetamol"

### Negation Detection (8 Languages)
- Telugu: `ivvaledu`, `ivvakudadu`, `kudadu`, `vaddhu`, `aapandi`
- Hindi: `mat do`, `nahi dena`, `band karo`, `rok do`, `hatao`
- Tamil: `kudadhu`, `venda`, `illai`, `pannakudadhu`
- Kannada: `kodabaradu`, `beda`, `baralla`, `nillisi`
- Malayalam: `paadilla`, `aruthhu`, `kodukkaruthhu`
- Marathi: `deu naka`, `thambav`, `band kara`, `nako`
- Bengali: `deben na`, `korben na`, `bandho korun`
- Gujarati: `aapvo nahi`, `na aapo`, `band karo`, `nakko`

### Dosage Extraction
Regional number words → numeric quantities:
- Telugu: `rendu` → 2, `moodu` → 3, `aidu` → 5
- Hindi: `dedh` → 1.5, `dhai` → 2.5, `teen` → 3
- Tamil: `moonu` → 3, `naalu` → 4, `anju` → 5

---

## 🗄️ Database Schema

6 tables in Supabase:
- `knowledge_nodes` — the output (CONSTRAINT/DECISION/FACT/ANTI_PATTERN)
- `transcripts` — raw and corrected transcripts with status
- `asr_evaluations` — 3 providers evaluated with metrics
- `accuracy_results` — 20-note benchmark results
- `cost_analysis` — 1/10/50 hospital scenarios
- `medical_dictionary` — 130+ drug terms with phonetics

---

## 📁 Project Structure

```
brahmo-voice-pipeline/
├── backend/
│   ├── main.py                    # FastAPI — 12 API endpoints
│   ├── intelligence/
│   │   ├── medical_dictionary.py  # 90+ drugs, phonetic matching
│   │   ├── negation_detector.py   # 8 languages, 100+ patterns
│   │   ├── dosage_extractor.py    # Regional number words
│   │   ├── phi_stripper.py        # PHI redaction
│   │   └── pipeline.py            # Orchestrator
│   ├── asr/
│   │   ├── whisper_provider.py    # faster-whisper integration
│   │   ├── google_provider.py     # Evaluation
│   │   └── asr_router.py          # Provider abstraction
│   ├── extraction/
│   │   ├── node_extractor.py      # Groq LLM extraction
│   │   └── prompts.py             # Negation-aware prompts
│   ├── evaluation/
│   │   └── metrics.py             # WER/MTA/NA/NEA formulas
│   └── database/
│       ├── schema.sql             # Full Supabase schema
│       └── supabase_client.py     # DB client
├── frontend/
│   └── src/pages/
│       ├── VoiceCapture.jsx       # Main demo page
│       ├── Review.jsx             # Doctor review
│       ├── Dashboard.jsx          # Knowledge node browser
│       ├── Evaluation.jsx         # ASR comparison
│       └── CostAnalysis.jsx       # Cost calculator
├── voice_notes/
│   └── test_cases.json            # 20 doctor voice notes
└── docs/
    ├── architecture.md
    ├── asr_evaluation.md
    └── cost_analysis.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/transcribe` | Text → ASR + intelligence |
| `POST` | `/api/transcribe-audio` | Audio file → ASR + intelligence |
| `POST` | `/api/pipeline` | Full pipeline (single call) |
| `POST` | `/api/review` | Doctor confirms transcript |
| `POST` | `/api/extract-nodes` | Extract knowledge nodes |
| `GET` | `/api/nodes` | Fetch knowledge nodes |
| `GET` | `/api/evaluations` | ASR evaluation results |
| `GET` | `/api/benchmark/results` | 20-note accuracy results |
| `GET` | `/api/cost-analysis` | Cost scenarios |
| `GET` | `/api/intelligence/test` | Test intelligence layer |

---

## 🌐 Adding a New Language

Adding Marathi negations (example):
```python
# backend/intelligence/negation_detector.py
NEGATION_PATTERNS["mr"].append(
    (r"\bnahi\b", "not / no", "MODERATE"),
)
```

That's it — one line in the config. The pipeline picks it up automatically.

---

## 🧪 Running the Benchmark

```bash
cd backend
# Test intelligence layer directly
python -c "
from intelligence.pipeline import run_pipeline
result = run_pipeline('stent valla ivvaledu Ibuprofen', language_code='te')
print(result.to_dict())
"

# Run API benchmark
curl -X POST http://localhost:8000/api/benchmark/run \
  -H 'Content-Type: application/json' \
  -d '{"run_baseline": true}'
```

---

## 📖 Docs

- [Architecture & ASR choice reasoning](docs/architecture.md)
- [Full ASR evaluation report](docs/asr_evaluation.md)
- [Cost analysis](docs/cost_analysis.md)
