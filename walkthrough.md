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
10. **Typed and Tested**: 78/78 backend tests pass; frontend compiles with 0 TypeScript errors.

---

## 2. Verification & Test Status

### Backend Test Suite
- **Result:** 78 / 78 tests passing (100% pass rate)
- **Command:** `python -m pytest backend/tests -v`
- **Key Suites Verified:**
  - `test_api.py`: Health check, capabilities, document upload, evidence ledger, analytics, reports, settings
  - `test_document_intelligence.py`: Excel, PDF, scanned document OCR pipeline, CSV acceptance, normalizers (metric, unit, period, organization), confidence engine, provenance retrieval
  - `test_live_document_pipeline.py`: Single upload, batch upload, SHA-256 deduplication, lifecycle, status tracking, preview
  - `test_number_safe_calculation_engine.py`: Single-fact calculation, temporal overlap protection, consolidated vs. subsidiary double-counting prevention, target achievement matching, lineage persistence, reconciliation
  - `test_pipeline.py`: Metric registry, period normalizer, unit normalizer, chunking, full CSV extraction
  - `test_scaled_platform.py`: Capabilities, analytics overview, query engine, claim verification, topic intelligence, review queue, conflict resolution, report generation and PDF export

### Frontend Compilation
- **Result:** 0 TypeScript errors (`tsc && vite build` succeeded cleanly)
- **Command:** `cd frontend && npm run build`
- **Bundle Output:** Production build generated in `frontend/dist/`

---

## 3. Key Upgrades Completed

1. **Authentication & RBAC Integration**:
   - Seeded demo roles (`analyst_demo`, `reviewer_demo`, `admin_demo`) with secure password hashes.
   - JWT identity extraction (`get_current_user_optional`) seamlessly integrated into:
     - Review mutation endpoints (`approve`, `reject`, `edit-and-approve`)
     - Evidence ledger direct verifications and fact superseding
     - Query history and audit trail logging
   - Graceful degradation: operates in demo fallback mode if JWT/passlib dependencies are not present.

2. **Database & Schema Completeness**:
   - Root `data/mineintel.db` and runtime databases synchronized.
   - Added missing `password_hash` and `is_demo` columns to `users` table.
   - Ensured idempotency on table creation and schema column upgrades across startups.

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
