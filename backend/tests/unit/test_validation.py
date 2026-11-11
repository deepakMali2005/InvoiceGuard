"""Unit tests for validation service."""

from decimal import Decimal

import pytest

from app.services.validation.service import ValidationService, ValidationResult


def test_normalize_description():
    svc = ValidationService()
    assert svc.normalize_description("Industrial Motor") == "industrial motor"
    assert svc.normalize_description("  INDUSTRIAL   MOTOR  ") == "industrial motor"
    assert svc.normalize_description("Item-100 (Type A)") == "item 100 type a"
    assert svc.normalize_description("") == ""


def test_to_decimal():
    svc = ValidationService()
    assert svc._to_decimal("52000.00", "f") == Decimal("52000.00")
    assert svc._to_decimal(100, "f") == Decimal("100")
    assert svc._to_decimal(None, "f") is None
    assert svc._to_decimal("", "f") is None


def test_arithmetic_line_total_mismatch():
    # Build a fake extraction-like object via ValidationService directly is complex;
    # instead test _check_arithmetic with a lightweight namespace.
    from types import SimpleNamespace

    svc = ValidationService()
    class LI:  # line item
        def __init__(self, desc, qty, price, total):
            self.description = desc; self.quantity = qty; self.unit_price = price; self.line_total = total
            self.source_page = 1; self.source_text = ""

    doc = SimpleNamespace(
        line_items=[LI("Motor", "2", "50000", "90000")],  # 2*50000=100000, not 90000
        subtotal="100000.00", tax_amount=None, grand_total="100000.00",
    )
    items = [{"description": i.description, "quantity": svc._to_decimal(i.quantity, "q"),
              "unit_price": svc._to_decimal(i.unit_price, "p"), "line_total": svc._to_decimal(i.line_total, "t")}
             for i in doc.line_items]
    issues = svc._check_arithmetic(doc, items)
    assert any("Line total" in i.message and "90000" in i.message for i in issues)


def test_arithmetic_match():
    from types import SimpleNamespace
    svc = ValidationService()
    class LI:
        def __init__(self, desc, qty, price, total):
            self.description = desc; self.quantity = qty; self.unit_price = price; self.line_total = total
            self.source_page = 1; self.source_text = ""
    doc = SimpleNamespace(
        line_items=[LI("Motor", "2", "50000", "100000")],
        subtotal="100000.00", tax_amount=None, grand_total="100000.00",
    )
    items = [{"description": i.description, "quantity": svc._to_decimal(i.quantity, "q"),
              "unit_price": svc._to_decimal(i.unit_price, "p"), "line_total": svc._to_decimal(i.line_total, "t")}
             for i in doc.line_items]
    issues = svc._check_arithmetic(doc, items)
    assert issues == []
