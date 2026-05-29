# AI-Powered Bank Statement Analyser

An industry-grade bank statement analysis platform similar to Perfios / Signzy. Upload any bank statement (PDF, scanned image, passbook photos) and get a full financial intelligence report instantly.

## Live Demo
- **Frontend:** https://your-app.netlify.app  
- **API Docs:** https://your-api.onrender.com/docs  

---

## Features

### Document Ingestion
- Digital PDFs (pdfplumber — table-aware extraction)
- Scanned PDFs & passbook photos (pytesseract OCR + OpenCV preprocessing)
- All major Indian banks — auto-detected

### AI Pipeline (3-tier cost optimization)
| Tier | Tool | Handles | Cost |
|------|------|---------|------|
| Regex | Built-in | ~70% of transactions (salary, EMI, ATM…) | Free |
| Gemini 1.5 Flash | Google AI | Remaining ~30% ambiguous | Free tier |
| Claude Sonnet 4.6 | Anthropic | Extraction + QA + Chatbot | ~$0.01/statement |

### Analytics & Insights
- **BSA Score** (0–100) — proprietary creditworthiness index
- **FOIR** — Fixed Obligation to Income Ratio
- Monthly inflow/outflow trends
- Average Monthly Balance (AMB)
- Income stability index
- Disposable income & max eligible EMI
- 15-category transaction classification
- Fraud signal detection: round-tripping, structuring, cash dependency

### Dashboard (6 tabs)
1. **Overview** — Key metric cards + BSA Score ring
2. **Transactions** — Searchable/filterable table with category badges
3. **Analytics** — 4 animated Recharts (bar, donut, area, composed)
4. **Risk** — FOIR gauge, income vs obligations, risk flags
5. **QA Report** — AI validation confidence scores per metric
6. **AI Chat** — Claude-powered financial advisor with suggested question chips

### Exports
- PDF report (Perfios-style layout via reportlab)
- Excel workbook — 3 sheets: Transactions, Monthly Summary, Risk Report

---

## Architecture

```
Bank Statement (PDF / Image)
    ↓
Document Processor (pdfplumber + pytesseract + OpenCV)
    ↓
Claude Sonnet 4.6 — Structured extraction (tool_use + prompt caching)
    ↓
Two-tier Classifier (Regex → Gemini Flash for ambiguous)
    ↓
Analytics Engine (pandas — FOIR, BSA Score, fraud signals)
    ↓
Claude QA Validator — Cross-checks extracted data vs source
    ↓
Next.js Dashboard (Recharts + shadcn/ui) + Chatbot
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.9 |
| AI Extraction | Claude Sonnet 4.6 (tool_use + prompt caching) |
| Bulk Classification | Gemini 1.5 Flash (free tier) |
| PDF Processing | pdfplumber, pytesseract, pdf2image, OpenCV |
| Analytics | pandas, numpy |
| Reports | reportlab (PDF), openpyxl (Excel) |
| Database | SQLite (dev) |
| Deploy | Netlify (frontend) + Render (backend) |

---

## Local Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- Tesseract OCR: `brew install tesseract`
- Poppler (for pdf2image): `brew install poppler`

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY and GEMINI_API_KEY

uvicorn main:app --reload
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install

cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# App running at http://localhost:3000
```

---

## Deployment

### Backend → Render
1. Push to GitHub
2. New Web Service → connect repo → set root dir to `backend`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`

### Frontend → Netlify
1. New site → connect GitHub repo
2. Base dir: `frontend`, Build: `npm run build`, Publish: `.next`
3. Add env var: `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`
4. Plugin `@netlify/plugin-nextjs` handles SSR automatically

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload bank statement |
| GET | `/api/analysis/{id}` | Get full analysis result |
| GET | `/api/analysis/{id}/status` | Poll analysis status |
| POST | `/api/chat/{id}` | Chat with AI about the analysis |
| GET | `/api/report/{id}/pdf` | Download PDF report |
| GET | `/api/report/{id}/excel` | Download Excel report |

---

## AI QA Layer

A second Claude pass cross-checks the generated analytics:
- Total credits/debits match sum of transactions?
- Balance progression valid (prev_balance ± transaction = next_balance)?
- Opening/closing balance matches statement header?
- FOIR calculation correct?
- Categorization accuracy via spot-check

Returns confidence scores (0–100%) per metric and a data quality grade (A–F).

---

*Assignment submission for LeadSquared Product Intern – AI role*
