"""Application exceptions."""

from typing import Any, Dict, Optional


class InvoiceGuardError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DocumentError(InvoiceGuardError):
    pass


class ExtractionError(InvoiceGuardError):
    pass


class ValidationError(InvoiceGuardError):
    pass


class ReconciliationError(InvoiceGuardError):
    pass


class ReportError(InvoiceGuardError):
    pass
