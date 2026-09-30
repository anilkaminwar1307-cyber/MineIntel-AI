# MineIntel AI — SIH Judge-Ready Prototype Walkthrough

**Team:** BharatBytes  
**Problem Statement ID:** 26023  
**Problem Title:** AI-Powered Geological, Mining and other Reporting solution for CMPDI/CIL subsidiaries  
**Theme:** Smart Automation | **Category:** Software  

---

## 1. Executive Summary & Architectural Compliance

MineIntel is a deterministic, evidence-grounded intelligence platform designed for Coal India Limited (CIL) subsidiaries and CMPDI. In strict accordance with the ten immutable architectural rules in `AGENTS.md`:

1. **Zero LLM Hallucination on Numerical Facts**: All quantitative mining metrics (coal production, offtake, drilling meters, overburden removal) are extracted deterministically via table/CSV parsers and heuristic rules into floating point / integer representations. Calculations are executed strictly via deterministic SQL or Python (`NumberSafe 2.0`).
2. **Strict Provenance Ledger**: Every single `ExtractedFact` retains its location coordinates (`document_id`, `page_number`, `sheet_name`, `row_number`, `column_name`, `cell_reference`, and `source_context`). Citations link directly back to source documents.
3. **Structured Queries via SQL & EvidenceChain**: Analytical queries (e.g. subsidiary production comparisons, target achievements) query the relational ledger using SQL aggregates rather than passing unindexed raw documents into LLM context windows.
4. **Grounded Narrative AI**: Explanations and summaries utilize strict low-temperature grounded synthesis with explicit prompt boundaries forbidding extrapolation.
5. **Transparent Conflict Management**: Discrepant figures between documents are never averaged or silently overwritten; they are logged as `EvidenceConflict` records for human analyst review.
6. **Immutable Human Review & Auditing**: Review actions and modifications are recorded in `ReviewAction` and `AuditEvent` tables, maintaining complete provenance.
7. **Monolithic Architecture**: FastAPI backend + SQLAlchemy/Alembic + Vite React TypeScript frontend.
8. **No Hardcoded Secrets**: All configuration is managed via `app.core.config.settings` backed by `pydantic-settings` and environment variables.
9. **Shared Evidence Database**: All modules (`MineGraph`, `NumberSafe`, `EvidenceChain`, `ReportGuard`) query and write to the unified relational database.
 10. **Typed and Tested**: 146/146 backend tests pass; frontend compiles with 0 TypeScript errors.

---

## 2. Verification & Test Status

### Backend Test Suite
- **Result:** 146 / 146 tests passing (100% pass rate)
- **Command:** `pytest backend/tests`
- **Key Suites Verified:**
  - `test_auth_rbac.py` (8/8 passing): JWT access tokens, bcrypt password hashing, login verification, protected `/me`, Analyst review-action prohibition (403), Reviewer authorization
  - `test_api.py` (8/8 passing): Health check, capabilities, document upload, evidence ledger, analytics, reports, settings (with in-memory isolated SQLite fixture)
  - `test_document_intelligence.py` (13/13 passing): Excel, PDF, scanned document OCR pipeline, CSV acceptance, normalizers (metric, unit, period, organization), confidence engine, provenance retrieval
  - `test_live_document_pipeline.py` (23/23 passing): Single upload, batch upload, SHA-256 deduplication, lifecycle, status tracking, preview
  - `test_number_safe_calculation_engine.py` (15/15 passing): Single-fact calculation, temporal overlap protection, consolidated vs. subsidiary double-counting prevention, target achievement matching, lineage persistence, reconciliation
  - `test_pipeline.py` (9/9 passing): Metric registry, period normalizer, unit normalizer, chunking, full CSV extraction
  - `test_scaled_platform.py` (10/10 passing): Capabilities, analytics overview, query engine, claim verification (including CONTRADICTED verdict), topic intelligence, review queue, conflict resolution, report generation and PDF export
  - `test_ask_mineintel_orchestrator.py` (7/7 passing): 11-step QueryOrchestrator intent routing, entity resolution, NumberSafe SQL dispatch, claim verification, narrative RAG, greeting/help, suggestions
  - `test_query_intent_routing.py` (23/23 passing): Intent classifier boundaries, metric word boundary matching, narrative RAG evidence gating
  - `test_phase0_verification.py` (5/5 passing): Insufficient evidence gating, conflict on duplicate facts, temporal grain mixing refusal, demo data exclusion, extractive labelling
  - `test_asset_resolver.py` (4/4 passing): Portable path resolution, missing asset error handling

### Frontend Compilation
- **Result:** 0 TypeScript errors (`tsc && vite build` succeeded cleanly)
- **Command:** `cd frontend && npm run build`
- **Bundle Output:** Production build generated in `frontend/dist/`

---

## 3. Key Upgrades Completed

1. **Repository Hygiene & Clean Checkout Reproducibility**:
   - Tracked live databases (`.db`), user uploads (`data/uploads`), generated PDF reports (`data/reports`), `.env`, `dist/`, and cache directories removed from git tracking.
   - Root `.gitignore` and `.dockerignore` updated to guard against committing sensitive artifacts or local database files.
   - Clean `.env.example` created with safe placeholders (`CHANGE_ME`) and documented demo defaults.

2. **Alembic Migrations & PostgreSQL Driver Pinning**:
   - Removed SQLite-specific `PRAGMA table_info` and `ALTER TABLE` hacks from `main.py` startup handler.
   - Implemented clean programmatic Alembic execution on startup (`command.upgrade(alembic_cfg, "head")`).
   - Added `render_as_batch=True` to `migrations/env.py` for full SQLite compatibility.
   - Pinned `psycopg2-binary>=2.9.9,<3.0.0` in `backend/requirements.txt` for production PostgreSQL Docker deployments.

3. **Authentication & RBAC Enforcement**:
   - Implemented JWT bearer authentication and bcrypt password hashing via `app.core.auth`.
   - Role-Based Access Control matrix:
     - **Analyst**: Upload documents, execute queries, view evidence ledger, access analytics and topic intelligence.
     - **Reviewer**: Verify facts, edit data points, resolve cross-document evidence conflicts.
     - **Admin**: System configuration, user management, and administrative audit inspection.
   - Enforced reviewer provenance from the authenticated JWT principal to prevent reviewer identity spoofing.

4. **Frontend Auth State & Operator Sign In**:
   - Created dedicated `Login.tsx` component with Coal India / CMPDI branding, operator sign-in form, and quick demo logins for Analyst, Reviewer, and Admin.
   - Configured Axios request interceptor to attach `Authorization: Bearer <token>` on all API requests.
   - Configured Axios response interceptor for automatic 401 redirection and session cleanup.
   - Integrated operator identity card, role badges, and logout flow into the navigation sidebar.

5. **Storage Security & MIME Magic Validation**:
   - Added magic bytes signature verification (`verify_magic_bytes`) in `LocalStorageService` to prevent file extension spoofing.
   - Path traversal prevention to ensure all file writes and reads remain strictly within designated storage boundaries.
   - Added `.docx` support to `FileType` enum and storage MIME mapping.


3. **API Contract & Route Aliasing**:
   - Added `/calculations/calculate` alias matching frontend `api.runCalculation`.
   - Added `/calculations/reconcile` (GET & POST) supporting dual-method queries with issue aggregation.
   - Added `/calculations/achievement` alias for target vs. actual achievement calculations.
   - Verified exact field mappings (`actual_mt`, `target_mt`, `dispatch_mt`, `production_mt`) across `AnalyticsOverview`, `EvidenceLedger`, and `AskMineIntel`.

---

## 4. Local Run & Demonstration Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ and npm

### Backend Setup & Launch
```bash
# Navigate to backend directory
cd backend

# Start the FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Documentation (Swagger): `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

### Frontend Setup & Launch
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start Vite dev server
npm run dev
```
- Web Application: `http://localhost:5173`

### Demo Credentials (Demo Mode)
- **Analyst:** `analyst_demo` / `Analyst@Demo2026`
- **Reviewer:** `reviewer_demo` / `Reviewer@Demo2026`
- **Admin:** `admin_demo` / `Admin@Demo2026!`

---

## 5. Demonstration Walkthrough for Judges

1. **Overview Dashboard**:
   - Inspect overall metrics: processed documents, verified facts, active subsidiaries.
   - Observe deterministic production trends and subsidiary breakdowns directly aggregated from verified evidence.

2. **Document Ingestion & Provenance**:
   - Upload sample mining reports (CSV, XLSX, PDF) from `sample_docs/` or `sample_data/`.
   - Inspect extracted facts in the **Evidence Ledger** with complete page, sheet, row, and cell citations.

3. **Ask MineIntel (NumberSafe Query Engine)**:
   - Ask: *"What was SECL's raw coal production in FY 2024-25?"*
   - Verify deterministic SQL execution, citations, and calculation steps.
   - Check Claim Verification: *"Verify claim: ECL raw coal production was 42.1 MT in FY 2024-25"*.

4. **Review Queue & Conflict Management**:
   - Navigate to **Review Queue** to view pending validations.
   - Review and approve or edit facts; observe immediate immutable audit entry in **Audit Trail**.
   - Review detected conflicts between multi-source documents and resolve with an authoritative selection.

5. **MineGraph & Parliamentary Brief**:
   - Explore entity hierarchy (CIL -> Subsidiaries -> Coalfields -> Mines -> Extracted Facts).
   - Generate grounded Parliamentary QA briefs backed exclusively by verified records.
