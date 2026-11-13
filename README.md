# InvoiceGuard

AI-Assisted Invoice Reconciliation and Verification System.

Compares Purchase Order (PO), Vendor Invoice, and Goods Receipt Note (GRN)
documents, extracts their contents via AI, performs deterministic financial
reconciliation, identifies discrepancies, and produces evidence-backed reports.

## Architecture

**AI interprets documents; deterministic Python verifies financial facts.**

- **AI (Nemotron API)** — document type identification, structured field
  extraction, line-item interpretation. Never trusted to calculate discrepancies.
- **Deterministic Python services** — schema validation, decimal-safe arithmetic,
  line-item matching, price/quantity comparison, discrepancy classification,
  final reconciliation status.

The backend is a modular FastAPI application. The frontend is Next.js + Tailwind.
PostgreSQL stores cases, documents, extracted data, and reconciliation results.

## Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy + Pydantic |
| Database | PostgreSQL |
| PDF extraction | PyMuPDF |
| AI provider | Nemotron API (provider adapter, env-driven) |
| HTTP client | HTTPX |
| Reports | reportlab (PDF) + csv (CSV) |
| Testing | pytest |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Container | Docker + Docker Compose |

## Project structure

```
InvoiceGuard/
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── api/routes/     # cases, documents, extraction, reconciliation, reports
│   │   ├── core/           # config, database, exceptions, logging
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic extraction schemas
│   │   ├── services/       # document, extraction, validation, reconciliation, reporting
│   │   └── main.py
│   ├── tests/              # unit + integration tests
│   └── requirements.txt
├── frontend/               # Next.js app
├── evaluation/
│   ├── dataset/            # synthetic documents + ground truth
│   ├── scripts/            # generate_dataset, run_evaluation, metrics, confusion matrix
│   └── results/            # metrics JSON, PNG matrices, report (regenerated)
├── storage/                # local uploaded documents
├── docker-compose.yml
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.12 + `venv`
- PostgreSQL (local or Docker)
- Node.js 20 + npm (frontend)
- Nemotron API credentials (optional; mocked locally by default)

## Backend setup (Windows CMD)

```cmd
REM Create and activate the virtual environment
python -m venv .venv
.venv\Scripts\activate.bat

REM Install backend dependencies
pip install -r backend\requirements.txt

REM Configure environment
copy .env.example .env
REM Edit .env and set DATABASE_URL / Nemotron credentials as needed

REM Ensure PostgreSQL is running and the role/database exist:
REM   role: invoiceguard / password: invoiceguard / db: invoiceguard

REM Start the API
cd backend
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000` (docs at `/docs`).

## Frontend setup

```cmd
cd frontend
npm install
npm run dev
```

The dashboard is at `http://localhost:3000` and calls `http://localhost:8000`.

## Docker (all-in-one)

```cmd
docker compose up --build
```

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- PostgreSQL: `localhost:5432`

The backend runs with `USE_MOCK_NEMOTRON=true` by default (mocked extractions,
clearly labeled). To use the real Nemotron API, set `NEMOTRON_API_KEY` and
`USE_MOCK_NEMOTRON=false` in `.env`.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/cases/` | Create a reconciliation case |
| GET | `/api/v1/cases/` | List cases |
| GET | `/api/v1/cases/{case_id}` | Get a case |
| POST | `/api/v1/cases/{case_id}/documents` | Upload a document |
| GET | `/api/v1/cases/{case_id}/documents` | List case documents |
| GET | `/api/v1/documents/{document_id}` | Get a document |
| POST | `/api/v1/documents/{document_id}/extract` | Extract document contents |
| GET | `/api/v1/documents/{document_id}/extraction` | Get extraction |
| POST | `/api/v1/cases/{case_id}/reconcile` | Reconcile a case |
| GET | `/api/v1/cases/{case_id}/reconciliation` | Get reconciliation result |
| GET | `/api/v1/cases/{case_id}/report?format=pdf\|csv` | Download report |
| GET | `/health` | Health check |

## Testing

```cmd
cd backend
pytest tests/ -q
```

Executed test results: **14 passed** (11 unit + 3 integration).
External Nemotron calls are mocked in tests (`USE_MOCK_NEMOTRON=true`).

## Evaluation

InvoiceGuard includes a mandatory, reproducible evaluation framework:

```cmd
cd ..\   (project root)
.venv\Scripts\python.exe evaluation\scripts\generate_dataset.py
.venv\Scripts\python.exe evaluation\scripts\run_evaluation.py
```

Outputs in `evaluation/results/`:
- `extraction_metrics.json` — field- and line-item-level extraction metrics
- `discrepancy_metrics.json` — precision/recall/F1/accuracy per category
- `confusion_matrices/*.png` — **separate** matrices for price, quantity,
  missing item, arithmetic, and reference mismatch
- `evaluation_report.md` — human-readable report with limitations

### Latest Evaluation Results (real Nemotron provider, 7 synthetic cases)

| Metric | Value |
|---|---|
| Field accuracy | 49.21% (62/126) |
| Line-item accuracy | 48.15% (13/27) |
| Evaluation mode | real_nemotron (USE_MOCK_NEMOTRON=false) |

| Discrepancy Category | TP | FP | FN | TN | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|---|---|---|---|
| Price | 0 | 0 | 1 | 6 | 0.00% | 0.00% | 0.00% | 85.71% |
| Quantity | 0 | 0 | 2 | 5 | 0.00% | 0.00% | 0.00% | 71.43% |
| Missing Item | 0 | 0 | 1 | 6 | 0.00% | 0.00% | 0.00% | 85.71% |
| Arithmetic | 0 | 0 | 1 | 6 | 0.00% | 0.00% | 0.00% | 85.71% |
| Reference Mismatch | 0 | 0 | 1 | 6 | 0.00% | 0.00% | 0.00% | 85.71% |

> **Note:** Line-item extraction improved to 48.15% with real Nemotron (vs 0.00% with mocked). However, discrepancy detection shows 0 true positives across all categories — the reconciliation engine is not flagging discrepancies that exist in the synthetic test data. This indicates a gap between extraction output and reconciliation rule matching that should be investigated. Results are from a synthetic, small dataset and are illustrative, not real-world evidence.

## Key design decisions (documented)

- Mocked vs real Nemotron is distinguished at every layer; mocked extractions
  are never presented as real model results.
- Financial arithmetic uses `decimal.Decimal` — no binary floating point for
  currency.
- No credentials are hardcoded; all configuration is environment-driven.
- Ambiguous cases route to `NEEDS_REVIEW`; the system never silently guesses
  missing financial information.
- Reconciliation rules: price mismatch, quantity mismatch, unordered items,
  unbilled receipts, reference mismatch, arithmetic inconsistency.

## Known limitations

- Local evaluation uses synthetic documents and the mocked provider; not
  real-world evidence of accuracy.
- PostgreSQL must be provisioned separately when not using Docker Compose.
- Frontend evaluation page documents how to regenerate results; live metrics
  are read from `evaluation/results/`.
