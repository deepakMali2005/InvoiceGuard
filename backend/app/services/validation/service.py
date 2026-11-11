"""Deterministic validation service.

Responsible for schema validation, required-field checks, type conversion,
numeric validation, arithmetic verification, and normalization.
AI never overrides these results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.core.logging import logger
from app.schemas.extraction import ExtractionResult, ExtractedLineItem

settings = get_settings()
TWO_PLACES = Decimal("0.01")


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    normalized: Optional[Dict[str, Any]] = None


class ValidationService:
    """Deterministic validation of extracted document data."""

    REQUIRED_COMMON_FIELDS = ("document_type", "document_number", "vendor_name", "currency")

    def __init__(self, price_tolerance=None, quantity_tolerance=None):
        self.price_tolerance = price_tolerance or settings.price_tolerance
        self.quantity_tolerance = quantity_tolerance or settings.quantity_tolerance

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def validate_document(self, extraction: ExtractionResult) -> ValidationResult:
        issues: List[ValidationIssue] = []

        # Structural / schema validation is already done by Pydantic; here we
        # apply business rules: required fields, numeric sanity, arithmetic.

        data = extraction.model_dump()

        # Required common fields
        for field_name in self.REQUIRED_COMMON_FIELDS:
            value = data.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(ValidationIssue(field=field_name, message=f"Required field '{field_name}' is missing.", severity="error"))

        # Currency must be present for financial documents
        if not data.get("currency"):
            issues.append(ValidationIssue(field="currency", message="Currency is required for financial validation.", severity="error"))

        # Validate line items
        normalized_items = []
        for idx, item in enumerate(extraction.line_items):
            item_issues, normalized_item = self._validate_line_item(idx, item)
            issues.extend(item_issues)
            normalized_items.append(normalized_item)

        # Arithmetic checks (only where structure supports them)
        arithmetic_issues = self._check_arithmetic(extraction, normalized_items)
        issues.extend(arithmetic_issues)

        errors = [i for i in issues if i.severity == "error"]
        is_valid = len(errors) == 0

        normalized = dict(data)
        normalized["line_items"] = normalized_items

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            normalized=normalized,
        )

    # ------------------------------------------------------------------ #
    # Line-item validation
    # ------------------------------------------------------------------ #
    def _validate_line_item(self, index: int, item: ExtractedLineItem) -> tuple[List[ValidationIssue], Dict[str, Any]]:
        issues: List[ValidationIssue] = []
        prefix = f"line_items[{index}]"

        if not item.description or not item.description.strip():
            issues.append(ValidationIssue(field=prefix, message="Line item description is missing.", severity="error"))

        qty = self._to_decimal(item.quantity, f"{prefix}.quantity")
        unit_price = self._to_decimal(item.unit_price, f"{prefix}.unit_price")
        line_total = self._to_decimal(item.line_total, f"{prefix}.line_total")

        normalized = {
            "description": item.description.strip() if item.description else "",
            "product_code": item.product_code,
            "quantity": qty,
            "unit_price": unit_price,
            "line_total": line_total,
            "source_page": item.source_page,
            "source_text": item.source_text,
        }

        # If quantity and unit_price present, line_total can be cross-checked later in arithmetic.
        if qty is not None and qty < 0:
            issues.append(ValidationIssue(field=f"{prefix}.quantity", message="Quantity cannot be negative.", severity="error"))
        if unit_price is not None and unit_price < 0:
            issues.append(ValidationIssue(field=f"{prefix}.unit_price", message="Unit price cannot be negative.", severity="error"))

        return issues, normalized

    def _check_arithmetic(self, extraction: ExtractionResult, items: List[Dict[str, Any]]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        # Per-line: line_total == quantity * unit_price (when all three present)
        for idx, item in enumerate(items):
            qty = item.get("quantity")
            price = item.get("unit_price")
            total = item.get("line_total")
            if qty is None or price is None or total is None:
                continue
            expected = (qty * price).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if total != expected:
                issues.append(
                    ValidationIssue(
                        field=f"line_items[{idx}].line_total",
                        message=f"Line total {total} does not equal quantity × unit_price ({expected}).",
                        severity="error",
                    )
                )

        # Document-level: subtotal == sum(line_totals), grand_total == subtotal + tax
        line_totals = [i["line_total"] for i in items if i["line_total"] is not None]
        subtotal = self._to_decimal(extraction.subtotal, "subtotal")
        tax = self._to_decimal(extraction.tax_amount, "tax_amount")
        grand_total = self._to_decimal(extraction.grand_total, "grand_total")

        if line_totals and subtotal is not None:
            expected_subtotal = sum(line_totals).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if subtotal != expected_subtotal:
                issues.append(
                    ValidationIssue(
                        field="subtotal",
                        message=f"Subtotal {subtotal} does not equal sum of line totals ({expected_subtotal}).",
                        severity="error",
                    )
                )

        if subtotal is not None and grand_total is not None:
            tax_effective = tax if tax is not None else Decimal("0")
            expected_grand = (subtotal + tax_effective).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if grand_total != expected_grand:
                issues.append(
                    ValidationIssue(
                        field="grand_total",
                        message=f"Grand total {grand_total} does not equal subtotal + tax ({expected_grand}).",
                        severity="error",
                    )
                )

        return issues

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_decimal(value: Any, field_name: str) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                return Decimal(value)
            except (InvalidOperation, ValueError) as exc:
                raise ValidationError(f"Cannot convert {field_name}={value!r} to Decimal") from exc
        return None

    @staticmethod
    def normalize_description(text: str) -> str:
        """Normalize a description for matching: lowercase, collapse whitespace, strip punctuation."""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
