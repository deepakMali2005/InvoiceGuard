"""Nemotron AI provider adapter.

InvoiceGuard keeps the AI provider independent of the extraction service through this adapter.
Configuration is entirely environment-driven; no credentials are ever hardcoded.

Two modes are supported:
  * REAL mode: calls the configured Nemotron API endpoint (requires NEMOTRON_API_KEY).
  * MOCK mode: returns deterministic, clearly-labeled mocked responses for local development
    and tests. Mocked extractions are never presented as real model results.

Set USE_MOCK_NEMOTRON=true (or leave NEMOTRON_API_KEY unset) to use mocked responses locally.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import ExtractionError
from app.core.logging import logger
from app.schemas.extraction import ExtractionResult

SETTINGS = get_settings()

USE_MOCK = SETTINGS.USE_MOCK_NEMOTRON or not SETTINGS.NEMOTRON_API_KEY


class ExtractionProvider(ABC):
    """Abstract provider interface for document extraction."""

    @abstractmethod
    def extract(self, document_text: str, document_type_hint: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured data from document text. Returns a raw dict."""
        raise NotImplementedError


class NemotronProvider(ExtractionProvider):
    """Real Nemotron API provider."""

    def __init__(self, endpoint: str, model: str, api_key: str, timeout: int = 30, max_retries: int = 2):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def extract(self, document_text: str, document_type_hint: Optional[str] = None) -> Dict[str, Any]:
        prompt = self._build_prompt(document_text, document_type_hint)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a document extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code == 429:
                    logger.warning("Nemotron rate-limited on attempt %s", attempt)
                    last_error = ExtractionError(f"Rate limited (attempt {attempt})")
                    continue
                response.raise_for_status()
                data = response.json()
                content = self._extract_content(data)
                return self._parse_json(content)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error = exc
                logger.warning("Nemotron request failed on attempt %s: %s", attempt, exc)
                continue
            except ExtractionError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Nemotron unexpected error on attempt %s: %s", attempt, exc)
                continue
        raise ExtractionError(f"Nemotron extraction failed after {self.max_retries} attempts: {last_error}")

    @staticmethod
    def _build_prompt(document_text: str, document_type_hint: Optional[str]) -> str:
        hint = f"\nThe document is suspected to be a: {document_type_hint}." if document_type_hint else ""
        return (
            "You extract structured information from procurement documents. "
            "Follow these rules strictly:\n"
            "1. Extract ONLY information supported by the supplied document.\n"
            "2. Never invent missing values. Return null for absent or uncertain fields.\n"
            "3. Preserve original descriptions exactly.\n"
            "4. Do not silently convert currencies.\n"
            "5. Distinguish subtotal, tax, and grand total.\n"
            "6. Return page numbers and source text evidence where available.\n"
            "7. Identify the document type: PURCHASE_ORDER, VENDOR_INVOICE, or GOODS_RECEIPT_NOTE.\n"
            "8. Return valid JSON matching the requested schema, with no extra text.\n"
            'Schema: {"document_type":"...","document_number":"...","document_date":"...",'
            '"vendor_name":"...","purchase_order_reference":"...","currency":"...",'
            '"line_items":[{"description":"...","product_code":"...","quantity":"...",'
            '"unit_price":"...","line_total":"...","source_page":1,"source_text":"..."}],'
            '"subtotal":"...","tax_amount":"...","grand_total":"..."}\n'
            f"Use decimal strings for financial and quantity values.{hint}\n\n"
            f"DOCUMENT TEXT:\n{document_text}\n"
        )

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if content:
                return content
        # Some providers return content at top level
        if isinstance(data.get("content"), str):
            return data["content"]
        raise ExtractionError("Nemotron response did not contain extractable text content.")

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        # Strip markdown fences if present
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1] if "```" in text[3:] else text
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Nemotron returned invalid JSON: {exc}") from exc


class MockExtractionProvider(ExtractionProvider):
    """Deterministic mocked provider for local development and tests.

    All responses are clearly labeled as mocked and must never be presented
    as real Nemotron API results.
    """

    MOCK_SOURCE = "mock"

    def extract(self, document_text: str, document_type_hint: Optional[str] = None) -> Dict[str, Any]:
        logger.info("Using MOCK Nemotron provider (not a real model result).")
        return self._mock_extract(document_text, document_type_hint)

    @staticmethod
    def _mock_extract(document_text: str, document_type_hint: Optional[str]) -> Dict[str, Any]:
        import re

        lowered = document_text.lower()

        # Heuristic document-type identification (mock only).
        type_keywords = {
            "PURCHASE_ORDER": ["purchase order", "po number", "po no", "ordered qty", "order date"],
            "VENDOR_INVOICE": ["invoice", "inv-", "grand total", "bill to", "invoice date"],
            "GOODS_RECEIPT_NOTE": ["goods receipt", "grn-", "grn ", "received qty", "received date", "receipt note"],
        }
        scores = {}
        for dtype, keywords in type_keywords.items():
            scores[dtype] = sum(2 if len(kw) > 5 else 1 for kw in keywords if kw in lowered)
        best_score = max(scores.values())
        best_types = [dtype for dtype, s in scores.items() if s == best_score]
        if best_score > 0:
            if len(best_types) == 1:
                doc_type = best_types[0]
            elif document_type_hint and document_type_hint in best_types:
                doc_type = document_type_hint
            else:
                if "GOODS_RECEIPT_NOTE" in best_types:
                    doc_type = "GOODS_RECEIPT_NOTE"
                elif "VENDOR_INVOICE" in best_types:
                    doc_type = "VENDOR_INVOICE"
                else:
                    doc_type = best_types[0]
        else:
            doc_type = document_type_hint or "VENDOR_INVOICE"

        # --- Parse header fields ---
        def _after(label: str) -> Optional[str]:
            """Return the value after 'Label:' on the same line."""
            m = re.search(rf"{re.escape(label)}\s*:\s*([^\n]+)", document_text, re.IGNORECASE)
            return m.group(1).strip() if m else None

        doc_number = _after(r"(?:PO|INV|GRN|Document) Number") or _after(r"(?:PO|INV|GRN) Number")
        if not doc_number:
            m = re.search(r"\b(PO|INV|GRN)[- ]?\d+", document_text, re.IGNORECASE)
            doc_number = m.group(0) if m else None

        vendor_name = _after("Vendor")
        currency = _after("Currency")
        document_date = _after("Date")
        po_reference = _after("PO Reference")
        grand_total = _after("Grand Total")

        # Normalize currency
        if currency:
            currency = currency.strip().upper()
            if currency in ("₹", "INR"):
                currency = "INR"
            elif currency in ("$", "USD"):
                currency = "USD"

        # --- Parse line items ---
        # Expected table format:
        # Description          Code       Qty     Unit Price     Line Total
        # Industrial Motor    MTR-100   100     50,000.00     5,000,000.00
        # Industrial Motor    MTR-100   100     -             -
        line_items = []
        lines = document_text.splitlines()
        in_item_section = False
        item_re = re.compile(
            r"^(?P<desc>.+?)\s+(?P<code>[A-Z]{2,}-\d+)\s+(?P<qty>\d+)\s+(?P<price>[\d,.]+|-)\s+(?P<total>[\d,.]+|-)\s*$"
        )
        for line in lines:
            low = line.lower()
            # Detect the header row
            if any(k in low for k in ("description", "qty", "quantity", "unit price", "line total")):
                if "code" in low or "qty" in low or "quantity" in low:
                    in_item_section = True
                    continue
            if not in_item_section:
                continue
            # Skip empty lines
            if not line.strip():
                continue
            # Stop if we hit a non-item line (e.g. Grand Total)
            if "grand total" in low:
                break
            m = item_re.match(line.strip())
            if not m:
                continue
            gd = m.group("desc").strip()
            gc = m.group("code")
            gq = m.group("qty")
            gp = m.group("price")
            gt = m.group("total")

            def _clean(v: str) -> Optional[str]:
                if v == "-" or v is None:
                    return None
                return v.replace(",", "")

            line_items.append({
                "description": gd,
                "product_code": gc,
                "quantity": _clean(gq),
                "unit_price": _clean(gp),
                "line_total": _clean(gt),
                "source_page": 1,
                "source_text": line.strip(),
            })

        # Fallback: crude per-line number extraction if table parsing found nothing
        if not line_items:
            for line in document_text.splitlines():
                low = line.lower()
                nums = re.findall(r"\d[\d,]*(?:\.\d+)?", line)
                if len(nums) >= 2 and any(w in low for w in ("qty", "quantity", "rate", "price", "total", "unit", "received")):
                    line_items.append({
                        "description": line.strip()[:120],
                        "product_code": None,
                        "quantity": nums[0].replace(",", "") if len(nums) >= 1 else None,
                        "unit_price": nums[1].replace(",", "") if len(nums) >= 2 else None,
                        "line_total": nums[2].replace(",", "") if len(nums) >= 3 else None,
                        "source_page": 1,
                        "source_text": line.strip(),
                    })

        # Clean numeric strings (remove commas)
        def _clean_num(v: Optional[str]) -> Optional[str]:
            if v is None:
                return None
            return v.replace(",", "")

        cleaned_items = []
        for it in line_items:
            cleaned_items.append({
                "description": it["description"],
                "product_code": it["product_code"],
                "quantity": _clean_num(it["quantity"]),
                "unit_price": _clean_num(it["unit_price"]),
                "line_total": _clean_num(it["line_total"]),
                "source_page": it["source_page"],
                "source_text": it["source_text"],
            })

        return {
            "document_type": doc_type,
            "document_number": doc_number,
            "document_date": document_date,
            "vendor_name": vendor_name,
            "purchase_order_reference": po_reference,
            "currency": currency,
            "line_items": cleaned_items,
            "subtotal": None,
            "tax_amount": None,
            "grand_total": _clean_num(grand_total),
        }


def get_provider() -> ExtractionProvider:
    """Factory returning the configured extraction provider.

    Returns a MockExtractionProvider when USE_MOCK_NEMOTRON=true or no API key is set,
    otherwise returns the real NemotronProvider.
    """
    if USE_MOCK:
        logger.warning(
            "MOCK Nemotron provider active. Extractions are simulated and labeled mocked. "
            "Set NEMOTRON_API_KEY and USE_MOCK_NEMOTRON=false to use the real API."
        )
        return MockExtractionProvider()
    return NemotronProvider(
        endpoint=SETTINGS.NEMOTRON_API_ENDPOINT,
        model=SETTINGS.NEMOTRON_MODEL,
        api_key=SETTINGS.NEMOTRON_API_KEY,
        timeout=SETTINGS.NEMOTRON_EXTRACTION_TIMEOUT_SECONDS,
        max_retries=SETTINGS.NEMOTRON_MAX_RETRIES,
    )


def extract_document(document_text: str, document_type_hint: Optional[str] = None) -> ExtractionResult:
    """Extract and validate a document through the configured provider.

    Returns a validated ExtractionResult. Raises ExtractionError on unrecoverable failure.
    """
    provider = get_provider()
    raw = provider.extract(document_text, document_type_hint)
    try:
        return ExtractionResult.model_validate(raw)
    except ValidationError as exc:
        raise ExtractionError(f"Extraction response failed schema validation: {exc}") from exc
