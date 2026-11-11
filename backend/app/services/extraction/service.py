"""Extraction service orchestration."""

from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import ExtractionError
from app.core.logging import logger
from app.schemas.extraction import ExtractionResult
from app.services.extraction.provider import extract_document, get_provider, USE_MOCK

settings = get_settings()


class ExtractionService:
    """Coordinates document text extraction via the AI provider adapter."""

    def __init__(self):
        self.provider = get_provider()
        self.mocked = USE_MOCK

    def extract(self, document_text: str, document_type_hint: Optional[str] = None) -> ExtractionResult:
        logger.info(
            "Extracting document (provider=%s, mocked=%s, hint=%s)",
            type(self.provider).__name__,
            self.mocked,
            document_type_hint,
        )
        if not document_text or not document_text.strip():
            raise ExtractionError("Document text is empty; nothing to extract.")
        try:
            result = extract_document(document_text, document_type_hint)
            logger.info("Extraction complete: document_type=%s, line_items=%d", result.document_type, len(result.line_items))
            return result
        except ExtractionError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Extraction service failed")
            raise ExtractionError(f"Extraction service error: {exc}") from exc

    def is_mocked(self) -> bool:
        """Return True if extractions are mocked (not real Nemotron results)."""
        return self.mocked
