# MINEINTEL

> **Evidence Intelligence for Mining & Geological Operations**  
> *AI-Powered Geological, Mining and other Reporting Solution for CMPDI / Coal India Limited*  
> **Ministry of Coal / Coal India Limited — Problem Statement ID: 26023**

---

## Overview

The reporting workflow across CMPDI and Coal India Limited (CIL) subsidiaries currently depends heavily on manually collecting and consolidating data from disparate files: geological reports, monthly production statements, scanned drill logs, CSV/Excel sheets, and historical archives. This causes delays, transcription errors, heavy expert dependency, and slow responses to official/parliamentary queries.

**MineIntel** is an evidence-first mining intelligence platform engineered around four core branded paradigms:

1. **MineGraph**: The multi-tiered relational ontology connecting `Mine ↕ Coalfield ↕ Subsidiary ↕ Metric ↕ Reporting Period ↕ Document ↕ Evidence`.
2. **NumberSafe AI**: Guarantees that quantitative queries and calculations are answered exclusively through structured evidence and deterministic computation—never through generative hallucinations.
3. **EvidenceChain**: Granular end-to-end provenance where every fact, chart, and report claim points to exact document coordinates (`Page`, `Sheet`, `Row`, `Column`, `Cell`, `Table`, and `Snippet`).
4. **ReportGuard**: Automated quality auditor checking for missing citations, low-confidence extractions, unresolved cross-document contradictions, and inconsistent totals.

---

## Phase 1 Deliverables & Architecture

This repository contains **Phase 1** of the 10-prompt sequential build:
- **FastAPI Core Backend**: RESTful API with Pydantic validation, CORS, error handling, and Swagger interactive documentation.
- **Relational Evidence Database**: Comprehensive SQLAlchemy ORM schema supporting Documents, Chunks, Extracted Facts, Validation Issues, Conflicts, Reviews, Reports, Topics, and Audit Events.
- **Alembic Migrations**: Fully configured database versioning with auto-generated initial schema.
- **Dual-Database Support**: Instant zero-dependency local execution via SQLite (`sqlite:///./data/mineintel.db`), with immediate toggle to PostgreSQL for enterprise containerized deployments.
- **Resilient AI Provider Abstraction**: `AIProvider` base class with official `GeminiProvider` implementation. Operates gracefully in `not_configured` mode if an API key is not supplied, eliminating startup crashes.
- **Secure File Ingestion Storage**: Sanitized uploads with extension validation, file-size limits, and path traversal protection for PDF, XLSX, XLS, CSV, TXT, PNG, and JPG.
- **Enterprise Industrial Frontend**: Government/industrial desktop interface styled in Vite + React 18 + TypeScript + Tailwind CSS with dark charcoal sidebar, live health diagnostics, and 11 functional page shells.

---

## Repository Structure

```
mineintel/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI router endpoints
│   │   │   ├── health.py         # GET /api/health (status, db, storage, gemini)
│   │   │   ├── system.py         # GET /api/system/capabilities
│   │   │   ├── documents.py      # Upload, list, detail, and delete documents
│   │   │   ├── evidence.py       # Query structured Evidence Ledger facts
│   │   │   ├── analytics.py      # Aggregated KPIs and subsidiary distributions
│   │   │   ├── reports.py        # Report templates and studio listings
│   │   │   ├── audit.py          # Immutable audit trail queries
│   │   │   ├── reviews.py        # Human-in-the-loop review queue
│   │   │   ├── topics.py         # Topic intelligence & theme clustering
│   │   │   ├── query.py          # Ask MineIntel copilot query interface
│   │   │   └── settings.py       # Live subsystem diagnostics
│   │   ├── core/
│   │   │   ├── config.py         # Centralized pydantic-settings
│   │   │   ├── database.py       # SQLAlchemy engine & session factory
│   │   │   └── logging.py        # Structured logging setup
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── enums.py          # DocumentStatus, ValidationStatus, AuditAction
│   │   │   ├── document.py       # Document & DocumentChunk
│   │   │   ├── fact.py           # ExtractedFact (EvidenceChain core)
│   │   │   ├── validation.py     # ValidationIssue & EvidenceConflict
│   │   │   ├── review.py         # ReviewAction & ProcessingJob
│   │   │   ├── report.py         # GeneratedReport
│   │   │   ├── topic.py          # Topic & TopicMention
│   │   │   ├── query.py          # QueryHistory
│   │   │   ├── audit.py          # AuditEvent
│   │   │   ├── system.py         # SystemSetting
│   │   │   └── user.py           # User
│   │   ├── schemas/              # Pydantic request & response models
│   │   ├── providers/
│   │   │   └── ai/
│   │   │       ├── base.py       # AIProvider abstract base class
│   │   │       └── gemini.py     # Google Gemini SDK implementation
│   │   ├── services/
│   │   │   ├── storage/local.py  # Sanitized local disk storage service
│   │   │   └── audit.py          # Audit logging helper
│   │   └── main.py               # Application factory, CORS, and lifecycles
│   ├── migrations/               # Alembic versioned migration scripts
│   ├── tests/                    # Pytest test suite
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/           # StatusBadge, EmptyState
│   │   │   └── layout/           # Sidebar, Header
│   │   ├── pages/
│   │   │   ├── Overview.tsx      # Operational KPI dashboard & feeds
│   │   │   ├── Documents.tsx     # Drag-and-drop document upload & table
│   │   │   ├── DocumentDetail.tsx# File metadata & storage provenance
│   │   │   ├── EvidenceLedger.tsx# Filterable fact ledger (EvidenceChain)
│   │   │   ├── ReviewQueue.tsx   # Human verification queue
│   │   │   ├── AskMineIntel.tsx  # Natural language Q&A interface
│   │   │   ├── Analytics.tsx     # Recharts trend & subsidiary charts
│   │   │   ├── TopicIntelligence.tsx # Topic clustering shell
│   │   │   ├── ReportStudio.tsx  # Template selector & ReportGuard controls
│   │   │   ├── AuditTrail.tsx    # Immutable chronological event log
│   │   │   └── Settings.tsx      # Live diagnostic matrix of all subsystems
│   │   ├── services/api.ts       # Axios client for backend endpoints
│   │   ├── types/index.ts        # TypeScript interfaces
│   │   ├── App.tsx               # Root app layout & tab routing
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── sample_data/                  # Real CMPDI & CIL sample files for testing
│   ├── CIL_Monthly_Production_Dispatch_Nov2024.csv
│   └── CMPDI_Geological_Drilling_Exploration_Summary.txt
├── docs/                         # Architecture documentation
├── .env.example
├── docker-compose.yml
├── README.md
└── AGENTS.md
```

---

## Technology Stack

- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2, `pydantic-settings`, Alembic, `aiofiles`, `python-multipart`.
- **Database**: SQLite (default local development) / PostgreSQL 16 (production).
- **AI Provider**: Google Gemini (`google-genai` official SDK) behind `AIProvider` abstraction.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Recharts, Axios.
- **Testing**: Pytest, HTTPX TestClient.

---

## Quickstart Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# (Optional) Create virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

FastAPI interactive Swagger UI will be available at:  
👉 **`http://127.0.0.1:8000/docs`**

### 2. Frontend Setup

```bash
# Open a new terminal in the frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Web interface will be available at:  
👉 **`http://127.0.0.1:5173`**

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` in the project root or configure backend environment variables:

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Platform title | `MineIntel` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./data/mineintel.db` |
| `UPLOAD_DIR` | Directory for uploaded source files | `./data/uploads` |
| `MAX_UPLOAD_SIZE_MB` | Maximum file size allowed | `50` |
| `AI_PROVIDER` | Active LLM provider | `gemini` |
| `GEMINI_API_KEY` | Official Google Gemini API Key | *(Optional; app runs gracefully without)* |
| `GEMINI_MODEL` | Target Gemini model | `gemini-2.5-flash` |
| `DEMO_MODE` | Active demo user mode | `true` |

---

## Current Platform Capabilities (Phase 1)

| Capability | Status | Notes |
|---|---|---|
| **Document Upload & Storage** | **OPERATIONAL** | Supports PDF, XLSX, XLS, CSV, TXT, PNG, JPG up to 50MB |
| **Evidence Ledger Schema** | **OPERATIONAL** | Zero-hallucination NumberSafe schema with cell/page provenance |
| **Audit Trail** | **OPERATIONAL** | Records document upload, deletion, and user mutations |
| **Diagnostics & Health** | **OPERATIONAL** | Live `/api/health` and `/api/settings` endpoints |
| **PDF / OCR Extraction** | *Phase 2* | PyMuPDF, PaddleOCR, openpyxl, pandas |
| **Semantic Search / Vector Index**| *Phase 3* | Sentence Transformers, chunk indexing |
| **Topic Intelligence** | *Phase 4* | TF-IDF, clustering, trend discovery |
| **NumberSafe Query Engine** | *Phase 5* | SQL query synthesis, grounded evidence Q&A |
| **Report Studio & ReportGuard** | *Phase 7* | Automatic report generation and verification |

---

## Verification & Tests

Run the backend test suite:
```bash
python -m pytest backend/tests/test_api.py -v
```

Validate frontend production build:
```bash
cd frontend
npm run build
```

---

## Docker Deployment

To launch all services (PostgreSQL, FastAPI Backend, and Nginx-served Frontend) via Docker Compose:
```bash
docker-compose up --build
```
