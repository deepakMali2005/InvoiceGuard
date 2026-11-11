# InvoiceGuard — Engineering Context (AGENTS.md)

## Project
InvoiceGuard — AI-Assisted Invoice Reconciliation and Verification System.
Authoritative spec: `BLUEPRINT.md` (Section 1–20, esp. 18 for agent instructions).

## Stack
- Backend: Python 3.12 + FastAPI + SQLAlchemy + Pydantic + PyMuPDF + httpx + pytest
- AI provider: Nemotron API (provider adapter, env-driven config) — now REAL by default
- DB: PostgreSQL
- Frontend: Next.js + TypeScript + Tailwind CSS
- Reports: PDF + CSV generation
- Container: Docker + Docker Compose
- venv: `.venv` (activate with `.venv\Scripts\Activate.ps1` on Windows)

## Key constraints
- AI interprets documents; deterministic Python code performs financial validation/reconciliation.
- Never fabricate missing document values or evaluation results.
- Distinguish mocked model responses from real Nemotron API responses.
- Separate confusion matrices per discrepancy category (price, quantity, missing items, arithmetic, reference mismatch).
- Decimal-safe arithmetic (no binary float for currency).
- Write tests alongside implementation; report only tests actually executed.

## Nemotron config
- Use env vars for endpoint, model, API key (never hardcode credentials).
- `USE_MOCK_NEMOTRON=false` → real Nemotron API; `true` (or unset key) → clearly-labeled mock.
- Config reads `.env` from project root via absolute path.
- Health endpoint reports `mocked_ai` status.

## Progress tracking (update as work completes)

### Done
- Read BLUEPRINT.md completely (1738 lines).
- Created Python venv `.venv`.
- Activated venv; confirmed fastapi 0.116.1 installed; pymupdf ok. sqlalchemy/pytest installed.
- Project structure created (backend, frontend, evaluation, storage).
- Config, database, SQLAlchemy models implemented.
- Document service (upload, PDF text extraction via PyMuPDF) implemented.
- Nemotron provider adapter + extraction service implemented (mocked locally, clearly labeled).
- Deterministic validation service implemented.
- Reconciliation engine implemented (price, quantity, missing item, unbilled receipt, reference mismatch, arithmetic).
- Reporting service (PDF + CSV) implemented.
- FastAPI routes + main.py implemented; all endpoints registered.
- Backend tests: 14 passed (11 unit + 3 integration).
- Evaluation framework implemented: dataset generator, run_evaluation, extraction metrics, 5 separate confusion matrices (PNG + JSON), evaluation report.
- Frontend (Next.js) implemented and builds successfully.
- Docker Compose + Dockerfiles + README + .gitignore created.

### Done (ALL COMPLETE)
- Read BLUEPRINT.md completely (1738 lines).
- Created Python venv `.venv`.
- Installed all backend dependencies.
- Project structure created (backend, frontend, evaluation, storage).
- Config, database, SQLAlchemy models implemented.
- Document service (upload, PDF text extraction via PyMuPDF) implemented.
- Nemotron provider adapter + extraction service implemented (mocked locally, clearly labeled).
- Deterministic validation service implemented.
- Reconciliation engine implemented (price, quantity, missing item, unbilled receipt, reference mismatch, arithmetic).
- Reporting service (PDF + CSV) implemented.
- FastAPI routes + main.py implemented; all endpoints registered.
- Backend tests: 14 passed (11 unit + 3 integration).
- Evaluation framework implemented: dataset generator, run_evaluation, extraction metrics, 5 separate confusion matrices (PNG + JSON), evaluation report.
- Frontend (Next.js) implemented — all pages load (Dashboard, Cases, New Reconciliation, Case Detail, Evaluation).
- Docker Compose + Dockerfiles + README + .gitignore created.
- Final engineering handoff written (ENGINEERING_HANDOFF.md).

### Session updates (latest)
- Manual test docs: `manual test docs/MT-001` through `MT-010`, each with PO + Invoice + GRN PDF (10 scenarios: clean match, price discrepancy, quantity discrepancy, missing item, unbilled receipt, arithmetic error, reference mismatch, multi-line USD, mixed discrepancies, clean USD).
- DELETE `/api/v1/cases/{case_id}` — deletes case + storage files.
- DELETE `/api/v1/documents/{document_id}` — deletes document + storage file.
- 7-day auto-cleanup on startup (`CASE_RETENTION_DAYS`, default 7) + manual `POST /api/v1/admin/cleanup`.
- Config: `USE_MOCK_NEMOTRON` added to Settings; reads `.env` from project root via absolute path.
- Mock extraction provider rewritten to parse table-format PDFs (description/code/qty/price/total), including dash values for GRN price/total.
- Extraction schema: comma-stripping validators for numeric/financial strings (Nemotron returns "50,000.00").
- Health endpoint: `mocked_ai` now reflects real state (false when using Nemotron).
- Real Nemotron AI enabled by default (`USE_MOCK_NEMOTRON=false`, endpoint `.../v1/chat/completions`).
- Fixed quantity mismatch expected/actual value swap (expected=invoiced, actual=received).
- Added PO→Invoice quantity comparison (in addition to existing Invoice→GRN).
- Frontend: delete button on cases list with confirmation modal.
- Frontend: remove button on individual document uploads in new case.
- Frontend: delete button on documents in case detail.
- Frontend: beautiful discrepancy cards with dynamic labels (Invoiced Qty/Received Qty, PO Unit Price/Invoice Unit Price, etc.).
- Frontend: consistent input styling in globals.css (white bg, slate text, blue focus).
- Frontend: redesigned cases page (professional B2B UI, search/dropdown width adjusted).
- Frontend: delete buttons in reconciliation findings with severity badges.
- Backend: `storage_path` stored as absolute path for portability.
- Plain language explanations added to all discrepancy types (price, quantity, unordered, unbilled, missing, reference, arithmetic) — human-readable "What this means" box on frontend.
- `plain_language_explanation` column added to Discrepancy DB model.
- DiscrepancyFinding dataclass extended with `plain_language_explanation` field.

### Running now
- Backend: http://127.0.0.1:8000 (health: {"status":"ok","mocked_ai":false})
- Frontend: http://localhost:3000

## Working directory
`C:\Users\DEEPAK MALI\Coding n prog\Better Placement\InvoiceGuard\project`

## Notes
- PowerShell `2>/dev/null` redirection fails on this shell (uses `C:\dev\null`); use `-ErrorAction SilentlyContinue` or omit redirection.
- Activate venv before pip/python commands: `.venv\Scripts\Activate.ps1`.
- To switch back to mock: set `USE_MOCK_NEMOTRON=true` in `.env` or remove `NEMOTRON_API_KEY`.
- Test PDFs are in `manual test docs/MT-XXX/` folders — 10 complete sets for manual testing.
- Output standardization: plain language explanations are now generated server-side for every discrepancy type and displayed prominently in a green "What this means" box on the Case Detail page.
- Input templates: NOT implemented — determined that manual template filling defeats the purpose of automated analysis.

## TODO (next session — input standardization)
- [ ] Option 2: Few-shot prompting — include 1–2 example extractions per document type in Nemotron prompt to teach expected format.
- [ ] Option 3: Layout normalization pipeline — pre-process PDFs (detect table headers, align columns, standardize number formats / strip commas / handle dashes) before extraction.

## Current state
- Backend: http://127.0.0.1:8000 (health: {"status":"ok","mocked_ai":false})
- Frontend: http://localhost:3000
- Real Nemotron AI enabled; reconciliation working with plain-language explanations.
