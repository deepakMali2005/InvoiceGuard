"""Integration tests for the document service (PDF text extraction)."""

import os
import tempfile

import fitz  # PyMuPDF
import pytest

from app.services.document.service import DocumentService


def _make_pdf(path, text_lines):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72,), "\n".join(text_lines))
    doc.save(path)
    doc.close()


def test_extract_pdf_text():
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "sample.pdf")
        _make_pdf(pdf_path, ["INV-2026-001", "Vendor: Acme Corp", "Industrial Motor Qty 100 Rate 52000"])
        text, page_count = DocumentService.extract_pdf_text(__import__("pathlib").Path(pdf_path))
        assert page_count == 1
        assert "INV-2026-001" in text
        assert "Acme Corp" in text


def test_save_document_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        svc = DocumentService(storage_path=tmp)
        pdf_path = os.path.join(tmp, "in.pdf")
        _make_pdf(pdf_path, ["PO-100", "Motor Qty 100 Rate 50000"])
        content = open(pdf_path, "rb").read()
        payload = svc.save("sample.pdf", content)
        assert payload.original_filename == "sample.pdf"
        assert payload.page_count == 1
        assert payload.file_checksum
        assert "PO-100" in payload.extracted_text
        assert os.path.exists(payload.storage_path)
