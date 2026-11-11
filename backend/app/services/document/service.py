"""Document service: upload handling, storage, PDF text extraction."""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from app.core.config import get_settings
from app.core.exceptions import DocumentError
from app.core.logging import logger

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf"}
MAX_SIZE_BYTES = settings.max_upload_size_bytes


@dataclass
class DocumentPayload:
    original_filename: str
    storage_path: str
    mime_type: str
    file_checksum: str
    size_bytes: int
    extracted_text: str
    page_count: int


class DocumentService:
    """Handles document upload, safe storage, and PDF text extraction."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_filename(original_filename: str) -> str:
        """Generate a safe server-side filename (prevent path traversal)."""
        name = Path(original_filename).name
        # strip dangerous characters
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        if not safe or safe in {".", ".."}:
            safe = "document.pdf"
        return safe

    @staticmethod
    def _checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def save(self, original_filename: str, content: bytes, mime_type: Optional[str] = None) -> DocumentPayload:
        """Save an uploaded document to local storage and extract its text."""
        if len(content) > MAX_SIZE_BYTES:
            raise DocumentError(
                f"File too large: {len(content)} bytes (max {MAX_SIZE_BYTES})",
                code="file_too_large",
            )

        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise DocumentError(
                f"Unsupported file type: {ext} (allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))})",
                code="unsupported_file_type",
            )

        safe_name = self._safe_filename(original_filename)
        # avoid collisions
        dest = self.storage_path / safe_name
        if dest.exists():
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            dest = self.storage_path / f"{stem}_{self._checksum(content)[:8]}{suffix}"

        dest.write_bytes(content)
        logger.info("Saved document to %s (%d bytes)", dest, len(content))

        detected_mime = mime_type or mimetypes.guess_type(str(dest))[0] or "application/pdf"

        extracted_text, page_count = self.extract_pdf_text(dest)

        return DocumentPayload(
            original_filename=original_filename,
            storage_path=str(dest.resolve()),
            mime_type=detected_mime,
            file_checksum=self._checksum(content),
            size_bytes=len(content),
            extracted_text=extracted_text,
            page_count=page_count,
        )

    @staticmethod
    def extract_pdf_text(path: Path) -> tuple[str, int]:
        """Extract text from a PDF using PyMuPDF. Returns (text, page_count)."""
        try:
            doc = fitz.open(str(path))
        except Exception as exc:  # noqa: BLE001
            raise DocumentError(f"Could not open PDF: {exc}", code="unreadable_pdf") from exc

        parts = []
        for page in doc:
            try:
                parts.append(page.get_text())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to extract text from a page: %s", exc)
                parts.append("")
        text = "\n".join(parts)
        doc.close()
        return text, len(parts)
