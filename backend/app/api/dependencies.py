"""FastAPI dependencies."""

from typing import Generator

from app.core.database import SessionLocal, get_db as _get_db
from app.core.config import get_settings
from app.services.extraction.service import ExtractionService
from app.services.validation.service import ValidationService
from app.services.reconciliation.service import ReconciliationService
from app.services.reporting.service import ReportingService
from app.services.document.service import DocumentService


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings_dep():
    return get_settings()


def get_extraction_service() -> ExtractionService:
    return ExtractionService()


def get_validation_service() -> ValidationService:
    return ValidationService()


def get_reconciliation_service() -> ReconciliationService:
    return ReconciliationService()


def get_reporting_service() -> ReportingService:
    return ReportingService()


def get_document_service() -> DocumentService:
    return DocumentService()
