"""Unit tests for reconciliation engine."""

from decimal import Decimal

import pytest

from app.services.reconciliation.service import ReconciliationService


class LI:
    def __init__(self, desc, code, qty, price, total, page=1, text=""):
        self.description = desc; self.product_code = code; self.quantity = qty
        self.unit_price = price; self.line_total = total; self.source_page = page; self.source_text = text


class Doc:
    def __init__(self, line_items, document_number=None, vendor_name=None, currency=None,
                 purchase_order_reference=None, subtotal=None, tax_amount=None, grand_total=None):
        self.line_items = line_items
        self.document_number = document_number
        self.vendor_name = vendor_name
        self.currency = currency
        self.purchase_order_reference = purchase_order_reference
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.grand_total = grand_total


def make_item(desc, code, qty, price):
    total = (Decimal(qty) * Decimal(price)).quantize(Decimal("0.01"))
    return LI(desc, code, qty, price, str(total))


def test_price_mismatch_detected():
    svc = ReconciliationService()
    po = Doc([make_item("Motor", "MTR-1", "100", "50000")], document_number="PO-100", vendor_name="Acme", currency="INR")
    inv = Doc([make_item("Motor", "MTR-1", "100", "52000")], purchase_order_reference="PO-100")
    grn = Doc([make_item("Motor", "MTR-1", "95", "0")])
    result, disc = svc.reconcile(po, inv, grn)
    price_discs = [d for d in disc if d.discrepancy_type.value == "PRICE_MISMATCH"]
    assert len(price_discs) == 1
    assert price_discs[0].difference == "2000.00"
    assert result.overall_status == "DISCREPANCIES_FOUND"


def test_quantity_mismatch_detected():
    svc = ReconciliationService()
    po = Doc([make_item("Motor", "MTR-1", "100", "50000")], document_number="PO-100", vendor_name="Acme", currency="INR")
    inv = Doc([make_item("Motor", "MTR-1", "100", "50000")], purchase_order_reference="PO-100")
    grn = Doc([make_item("Motor", "MTR-1", "95", "0")])
    result, disc = svc.reconcile(po, inv, grn)
    qty_discs = [d for d in disc if d.discrepancy_type.value == "QUANTITY_MISMATCH"]
    assert len(qty_discs) == 1
    assert qty_discs[0].difference == "5.00"


def test_reference_mismatch():
    svc = ReconciliationService()
    po = Doc([make_item("Motor", "MTR-1", "100", "50000")], document_number="PO-100", vendor_name="Acme", currency="INR")
    inv = Doc([make_item("Motor", "MTR-1", "100", "50000")], purchase_order_reference="PO-999")
    grn = Doc([make_item("Motor", "MTR-1", "100", "0")])
    result, disc = svc.reconcile(po, inv, grn)
    ref_discs = [d for d in disc if d.discrepancy_type.value == "REFERENCE_MISMATCH"]
    assert len(ref_discs) == 1
    assert ref_discs[0].requires_review is True


def test_unordered_item():
    svc = ReconciliationService()
    po = Doc([make_item("Motor", "MTR-1", "100", "50000")], document_number="PO-100", vendor_name="Acme", currency="INR")
    inv = Doc([make_item("Motor", "MTR-1", "100", "50000"), make_item("Widget", "WID-9", "5", "100")], purchase_order_reference="PO-100")
    grn = Doc([make_item("Motor", "MTR-1", "100", "0")])
    result, disc = svc.reconcile(po, inv, grn)
    unordered = [d for d in disc if d.discrepancy_type.value == "UNORDERED_ITEM"]
    assert len(unordered) == 1


def test_all_match():
    svc = ReconciliationService()
    po = Doc([make_item("Motor", "MTR-1", "100", "50000")], document_number="PO-100", vendor_name="Acme", currency="INR")
    inv = Doc([make_item("Motor", "MTR-1", "100", "50000")], purchase_order_reference="PO-100")
    grn = Doc([make_item("Motor", "MTR-1", "100", "0")])
    result, disc = svc.reconcile(po, inv, grn)
    assert result.overall_status == "MATCHED"
    assert disc == []
