# AGENTS.md — Developer & AI Agent Guidelines for MineIntel

Welcome to the **MineIntel** repository: Evidence Intelligence for Mining & Geological Operations (Smart India Hackathon Problem Statement 26023).

All AI agents and developers extending or modifying this codebase across the 10-phase build MUST strictly comply with these ten immutable rules:

---

## 10 Core Architectural Rules

### 1. Numerical facts must NEVER originate from LLM hallucination
- Never ask Gemini or any language model to calculate or invent mining metrics (production MT, stripping ratio, drilling meters, overburden BCM, offtake).
- Quantitative values must be extracted deterministically via table parsers or heuristic regex, parsed into floating point / integer numbers, and stored directly in the `ExtractedFact` table.
- NumberSafe AI guarantees that any calculation is executed deterministically in SQL or Python.

### 2. Every numerical fact must preserve provenance
- An extracted fact without provenance is considered corrupted and invalid.
- Every `ExtractedFact` row must contain location coordinates (`document_id`, plus `page_number` for PDFs, `sheet_name`, `row_number`, `column_name`, `cell_reference` for spreadsheets, and `source_context`).
- Answers and reports must provide citations linking directly back to source documents.

### 3. Structured queries should use SQL and EvidenceChain
- For questions such as "What was SECL's raw coal production in Q2 2024?", query the `extracted_facts` relational database using SQL aggregates or deterministic filters.
- Do not pass unindexed raw documents into an LLM context window hoping it sums the numbers correctly.

### 4. Narrative AI must use grounded source context
- When Gemini is used to generate summaries, executive narratives, or explanations, provide the exact verified evidence records and document snippets in the prompt context.
- Enforce strict temperature settings (0.0 to 0.2) and prompt instructions: "If the requested information is absent from the provided context, state that it is not available. Never extrapolate or assume figures."

### 5. Never hide conflicts
- If two documents report contradictory values for the same metric, subsidiary, and period (e.g. 1.85 MT vs 1.92 MT), log an `EvidenceConflict` record.
- Surface discrepancies honestly to analysts in the Review Queue. Never silently overwrite or average conflicting data points.

### 6. Human review history must be preserved
- All human analyst modifications, verifications, approvals, or rejections must be immutably recorded in `ReviewAction` and `AuditEvent`.
- The `human_verified` flag on `ExtractedFact` must only be set by explicit analyst confirmation.

### 7. Do not introduce unrelated microservices
- Maintain a clean monolithic architecture: FastAPI backend with SQLAlchemy + Alembic, and a single Vite React TypeScript frontend.
- Do not add complex message brokers, distributed worker swarms, or secondary microservices unless explicitly specified in later prompts.

### 8. Do not hardcode API keys or secrets
- Always load configuration through `app.core.config.settings` backed by `pydantic-settings` and environment variables.
- System must boot gracefully and expose `not_configured` if `GEMINI_API_KEY` is not present.

### 9. All modules must ultimately share one evidence database
- The future MineGraph, NumberSafe AI, EvidenceChain, and ReportGuard modules must all query and write to the single shared relational database (`mineintel.db` / PostgreSQL).
- Do not create isolated silo databases or in-memory caches that bypass the Evidence Ledger.

### 10. Keep code modular, typed, and tested
- Write clear Pydantic schemas and SQLAlchemy models.
- Maintain comprehensive backend tests in `backend/tests/` and verify that `npm run build` in `frontend/` compiles with 0 TypeScript errors.
- Update `walkthrough.md` and documentation upon completing tasks.
