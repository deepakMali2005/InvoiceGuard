"""InvoiceGuard FastAPI application."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_settings
from app.api.routes import cases, documents, extraction, reconciliation, reports
from app.core.database import Base, engine
from app.core.logging import configure_logging, logger
from app.repositories.case import CaseRepository
from app.repositories.document import DocumentRepository
from app.services.extraction.provider import USE_MOCK

settings = get_settings()
configure_logging("DEBUG" if settings.DEBUG else "INFO")

# Create tables (for production use Alembic migrations)
Base.metadata.create_all(bind=engine)

# Add plain_language_explanation column if it doesn't exist (dev migration)
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE discrepancies ADD COLUMN plain_language_explanation TEXT"))
        conn.commit()
except Exception:
    pass  # Column may already exist

app = FastAPI(title="InvoiceGuard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(reconciliation.router)
app.include_router(reports.router)

EVAL_RESULTS_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "results"

# --- 7-day auto cleanup -----------------------------------------------------

CASE_RETENTION_DAYS = int(os.environ.get("CASE_RETENTION_DAYS", "7"))


def cleanup_old_cases(db: Session) -> int:
    """Delete cases older than CASE_RETENTION_DAYS and their document files."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=CASE_RETENTION_DAYS)
    case_repo = CaseRepository(db)
    doc_repo = DocumentRepository(db)
    deleted = 0

    for case in case_repo.list():
        if case.created_at and case.created_at.tzinfo is None:
            # make naive datetimes timezone-aware (assume UTC)
            case_created = case.created_at.replace(tzinfo=timezone.utc)
        else:
            case_created = case.created_at
        if case_created and case_created < cutoff:
            # remove physical document files
            for d in doc_repo.list_for_case(case.id):
                try:
                    if d.storage_path and os.path.exists(d.storage_path):
                        os.remove(d.storage_path)
                        logger.info("Auto-cleanup: deleted storage file %s", d.storage_path)
                except OSError as exc:
                    logger.warning("Auto-cleanup: could not delete %s: %s", d.storage_path, exc)
            if case_repo.delete(case.id):
                deleted += 1
                logger.info("Auto-cleanup: deleted case %s (%s)", case.id, case.case_reference)
    return deleted


@app.on_event("startup")
def _startup_cleanup():
    """Run 7-day auto-cleanup on server startup."""
    db = next(get_db())
    try:
        n = cleanup_old_cases(db)
        if n:
            logger.info("Startup cleanup removed %d case(s) older than %d days", n, CASE_RETENTION_DAYS)
    finally:
        db.close()


@app.post("/api/v1/admin/cleanup", status_code=200)
def admin_cleanup(db: Session = Depends(get_db)):
    """Manually trigger cleanup of cases older than the retention window."""
    n = cleanup_old_cases(db)
    return {"deleted": n, "retention_days": CASE_RETENTION_DAYS}


# --- Routes -----------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "mocked_ai": USE_MOCK}


@app.get("/api/v1/evaluation/results")
def evaluation_results():
    """Serve evaluation results for the frontend."""
    result = {"available": False, "files": []}

    metrics_file = EVAL_RESULTS_DIR / "extraction_metrics.json"
    discrepancy_file = EVAL_RESULTS_DIR / "discrepancy_metrics.json"
    report_file = EVAL_RESULTS_DIR / "evaluation_report.md"

    if metrics_file.exists():
        try:
            result["extraction_metrics"] = json.loads(metrics_file.read_text())
            result["available"] = True
            result["files"].append("extraction_metrics.json")
        except Exception:
            pass

    if discrepancy_file.exists():
        try:
            result["discrepancy_metrics"] = json.loads(discrepancy_file.read_text())
            result["available"] = True
            result["files"].append("discrepancy_metrics.json")
        except Exception:
            pass

    if report_file.exists():
        result["report"] = report_file.read_text()
        result["available"] = True
        result["files"].append("evaluation_report.md")

    # List confusion matrix PNGs
    cm_dir = EVAL_RESULTS_DIR / "confusion_matrices"
    if cm_dir.exists():
        result["confusion_matrices"] = [f.name for f in cm_dir.glob("*.png")]

    return JSONResponse(content=result)


@app.get("/api/v1/evaluation/confusion-matrices/{name}")
def confusion_matrix_image(name: str):
    """Serve a confusion matrix PNG image."""
    cm_dir = EVAL_RESULTS_DIR / "confusion_matrices"
    file_path = cm_dir / f"{name}.png"
    if file_path.exists():
        return FileResponse(str(file_path), media_type="image/png")
    return JSONResponse(content={"error": "not found"}, status_code=404)
