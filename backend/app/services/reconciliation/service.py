"""Deterministic reconciliation engine.

Compares PO, invoice, and GRN extracted data and produces verified discrepancies.
AI suggests candidate matches; deterministic rules decide reliability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.exceptions import ReconciliationError
from app.core.logging import logger
from app.models import (
    Discrepancy,
    DiscrepancyType,
    ReconciliationResult,
    Severity,
)
from app.services.validation.service import ValidationService

settings = get_settings()
TWO_PLACES = Decimal("0.01")


@dataclass
class MatchedItem:
    po_item: Optional[Dict[str, Any]]
    invoice_item: Optional[Dict[str, Any]]
    grn_item: Optional[Dict[str, Any]]
    match_basis: str  # "product_code" | "description" | "ambiguous" | "unmatched"


@dataclass
class DiscrepancyFinding:
    discrepancy_type: DiscrepancyType
    severity: Severity
    description: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    difference: Optional[str] = None
    calculation_details: Optional[str] = None
    evidence_references: Optional[str] = None
    requires_review: bool = False
    plain_language_explanation: Optional[str] = None


class ReconciliationService:
    """Deterministic reconciliation of PO, invoice, and GRN."""

    def __init__(self, price_tolerance=None, quantity_tolerance=None):
        self.price_tolerance = price_tolerance or settings.price_tolerance
        self.quantity_tolerance = quantity_tolerance or settings.quantity_tolerance
        self.validator = ValidationService(
            price_tolerance=self.price_tolerance,
            quantity_tolerance=self.quantity_tolerance,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def reconcile(
        self,
        po: Any,
        invoice: Any,
        grn: Any,
    ) -> Tuple[ReconciliationResult, List[Discrepancy]]:
        """Run full reconciliation. Returns (result, discrepancies)."""
        findings: List[DiscrepancyFinding] = []

        po_items = self._items(po)
        invoice_items = self._items(invoice)
        grn_items = self._items(grn)

        # Rule E: document reference mismatch
        findings.extend(self._check_reference_mismatch(po, invoice))

        # Match invoice items to PO items
        matched: List[MatchedItem] = []

        for inv in invoice_items:
            match = self._find_best_match(inv, po_items, grn_items)
            matched.append(match)

        # Evaluate each matched triplet (flags price, quantity, unordered, ambiguous)
        for match in matched:
            findings.extend(self._evaluate_match(match))

        # Rule D: unbilled receipts (GRN items not matched to any invoice)
        for grn in grn_items:
            if not any(m.grn_item is grn for m in matched):
                findings.append(DiscrepancyFinding(
                    discrepancy_type=DiscrepancyType.UNBILLED_RECEIPT,
                    severity=Severity.MEDIUM,
                    description=f"Received item '{grn.get('description')}' has no matching invoice item.",
                    expected_value="Invoice line",
                    actual_value=grn.get("description"),
                    evidence_references=self._evidence(grn),
                    requires_review=False,
                    plain_language_explanation=self._plain_language_explanation(
                        "UNBILLED_RECEIPT", description=None,
                        expected_value="Invoice line",
                        actual_value=grn.get("description"),
                        difference=None,
                    ),
                ))

        # Rule F: arithmetic inconsistencies on each document
        for label, doc in (("purchase order", po), ("vendor invoice", invoice), ("goods receipt note", grn)):
            findings.extend(self._check_document_arithmetic(doc, label))

        # Build result
        review_required = any(f.requires_review for f in findings) or any(
            f.discrepancy_type == DiscrepancyType.MISSING_LINE_ITEM for f in findings
        )

        if findings:
            overall_status = "NEEDS_REVIEW" if review_required else "DISCREPANCIES_FOUND"
        else:
            overall_status = "MATCHED"

        result = ReconciliationResult(
            overall_status=overall_status,
            findings_count=len(findings),
            review_required=review_required,
        )
        discrepancies = [
            Discrepancy(
                discrepancy_type=f.discrepancy_type,
                severity=f.severity,
                description=f.description,
                expected_value=f.expected_value,
                actual_value=f.actual_value,
                difference=f.difference,
                calculation_details=f.calculation_details,
                evidence_references=f.evidence_references,
                requires_review=f.requires_review,
                plain_language_explanation=f.plain_language_explanation,
            )
            for f in findings
        ]
        return result, discrepancies

    def _items(self, doc: Any) -> List[Dict[str, Any]]:
        """Extract normalized line items from an extraction object."""
        items = []
        line_items = getattr(doc, "line_items", None) or []
        for idx, li in enumerate(line_items):
            items.append({
                "_index": idx,
                "description": li.description or "",
                "product_code": li.product_code,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "line_total": li.line_total,
                "source_page": li.source_page,
                "source_text": li.source_text,
            })
        return items

    # ------------------------------------------------------------------ #
    # Matching
    # ------------------------------------------------------------------ #
    def _find_best_match(
        self,
        invoice_item: Dict[str, Any],
        po_items: List[Dict[str, Any]],
        grn_items: List[Dict[str, Any]],
    ) -> MatchedItem:
        po_match = None
        grn_match = None
        basis = "unmatched"

        inv_code = invoice_item.get("product_code")
        inv_desc_norm = ValidationService.normalize_description(invoice_item.get("description", ""))

        # 1. Exact product code match
        if inv_code:
            for po in po_items:
                if po.get("product_code") and po["product_code"].strip().lower() == inv_code.strip().lower():
                    po_match = po
                    basis = "product_code"
                    break
            for grn in grn_items:
                if grn.get("product_code") and grn["product_code"].strip().lower() == inv_code.strip().lower():
                    grn_match = grn

        # 2. Exact normalized description match
        if po_match is None:
            for po in po_items:
                if ValidationService.normalize_description(po.get("description", "")) == inv_desc_norm and inv_desc_norm:
                    po_match = po
                    basis = "description"
                    break
        if grn_match is None:
            for grn in grn_items:
                if ValidationService.normalize_description(grn.get("description", "")) == inv_desc_norm and inv_desc_norm:
                    grn_match = grn

        # 3 / 4. No exact product code or description match. Without a similarity
        # candidate this is an unordered item (Rule C); we do not auto-merge
        # dissimilar descriptions. Treat as unmatched.
        if po_match is None:
            basis = "unmatched"

        return MatchedItem(
            po_item=po_match,
            invoice_item=invoice_item,
            grn_item=grn_match,
            match_basis=basis,
        )

    # ------------------------------------------------------------------ #
    # Rule evaluations
    # ------------------------------------------------------------------ #
    def _evaluate_match(self, match: MatchedItem) -> List[DiscrepancyFinding]:
        findings: List[DiscrepancyFinding] = []

        if match.match_basis == "ambiguous":
            findings.append(DiscrepancyFinding(
                discrepancy_type=DiscrepancyType.MISSING_LINE_ITEM,
                severity=Severity.HIGH,
                description=(
                    f"Invoice item '{match.invoice_item.get('description')}' could not be reliably matched "
                    "to a purchase order item. Ambiguous match — manual review required."
                ),
                expected_value="PO line item",
                actual_value=match.invoice_item.get("description"),
                evidence_references=self._evidence(match.invoice_item),
                requires_review=True,
                plain_language_explanation=self._plain_language_explanation(
                    "MISSING_LINE_ITEM",
                    description=match.invoice_item.get("description"),
                    expected_value="PO line item",
                    actual_value=match.invoice_item.get("description"),
                    difference=None,
                ),
            ))
            return findings

        if match.match_basis == "unmatched":
            findings.append(DiscrepancyFinding(
                discrepancy_type=DiscrepancyType.UNORDERED_ITEM,
                severity=Severity.HIGH,
                description=(
                    f"Invoiced item '{match.invoice_item.get('description')}' has no matching purchase order item."
                ),
                expected_value="No PO match",
                actual_value=match.invoice_item.get("description"),
                evidence_references=self._evidence(match.invoice_item),
                requires_review=False,
                plain_language_explanation=self._plain_language_explanation(
                    "UNORDERED_ITEM",
                    description=match.invoice_item.get("description"),
                    expected_value="No PO match",
                    actual_value=match.invoice_item.get("description"),
                    difference=None,
                ),
            ))
            return findings

        po = match.po_item
        inv = match.invoice_item
        grn = match.grn_item

        # Rule A: price discrepancy (PO vs Invoice)
        if po and inv:
            po_price = self._decimal(po.get("unit_price"))
            inv_price = self._decimal(inv.get("unit_price"))
            inv_qty = self._decimal(inv.get("quantity"))
            if po_price is not None and inv_price is not None:
                diff = inv_price - po_price
                if abs(diff) > self.price_tolerance:
                    variance = (diff * (inv_qty if inv_qty is not None else Decimal("1"))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                    findings.append(DiscrepancyFinding(
                        discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                        severity=Severity.HIGH,
                        description=(
                            f"Unit price mismatch for '{inv.get('description')}': "
                            f"PO {po_price} vs Invoice {inv_price}."
                        ),
                        expected_value=str(po_price),
                        actual_value=str(inv_price),
                        difference=str(diff.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                        calculation_details=(
                            f"price_difference = {inv_price} - {po_price} = {diff}; "
                            f"total_price_variance = {diff} × {inv_qty if inv_qty is not None else 1} = {variance}"
                        ),
                        evidence_references=self._evidence(po, inv),
                        plain_language_explanation=self._plain_language_explanation(
                            "PRICE_MISMATCH",
                            description=inv.get("description"),
                            expected_value=str(po_price),
                            actual_value=str(inv_price),
                            difference=str(diff.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                        ),
                    ))

        # Rule B: quantity discrepancy (Invoice vs GRN)
        if inv and grn:
            inv_qty = self._decimal(inv.get("quantity"))
            grn_qty = self._decimal(grn.get("quantity"))
            if inv_qty is not None and grn_qty is not None:
                qty_diff = inv_qty - grn_qty
                if abs(qty_diff) > self.quantity_tolerance:
                    direction = "invoiced but undelivered" if qty_diff > 0 else "received but not fully invoiced"
                    findings.append(DiscrepancyFinding(
                        discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                        severity=Severity.HIGH,
                        description=(
                            f"Quantity mismatch for '{inv.get('description')}': "
                            f"invoiced {inv_qty} vs received {grn_qty} ({direction})."
                        ),
                        expected_value=str(inv_qty),
                        actual_value=str(grn_qty),
                        difference=str(qty_diff.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                        calculation_details=f"quantity_difference = {inv_qty} - {grn_qty} = {qty_diff}",
                        evidence_references=self._evidence(inv, grn),
                        plain_language_explanation=self._plain_language_explanation(
                            "QUANTITY_MISMATCH",
                            description=(
                                f"Quantity mismatch for '{inv.get('description')}': "
                                f"invoiced {inv_qty} vs received {grn_qty} ({direction})."
                            ),
                            expected_value=str(inv_qty),
                            actual_value=str(grn_qty),
                            difference=str(qty_diff.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                        ),
                    ))

        # Rule B-extended: quantity discrepancy (PO vs Invoice)
        if po and inv:
            po_qty = self._decimal(po.get("quantity"))
            inv_qty = self._decimal(inv.get("quantity"))
            if po_qty is not None and inv_qty is not None:
                qty_diff = po_qty - inv_qty
                if abs(qty_diff) > self.quantity_tolerance:
                    direction = "ordered but not invoiced" if qty_diff > 0 else "invoiced beyond ordered"
                    findings.append(DiscrepancyFinding(
                        discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                        severity=Severity.HIGH,
                        description=(
                            f"Quantity mismatch for '{inv.get('description')}': "
                            f"ordered {po_qty} vs invoiced {inv_qty} ({direction})."
                        ),
                        expected_value=str(po_qty),
                        actual_value=str(inv_qty),
                        difference=str(qty_diff.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                        calculation_details=f"quantity_difference = {po_qty} - {inv_qty} = {qty_diff}",
                        evidence_references=self._evidence(po, inv),
                        plain_language_explanation=self._plain_language_explanation(
                            "QUANTITY_MISMATCH",
                            description=(
                                f"Quantity mismatch for '{inv.get('description')}': "
                                f"ordered {po_qty} vs invoiced {inv_qty} ({direction})."
                            ),
                            expected_value=str(po_qty),
                            actual_value=str(inv_qty),
                            difference=str(qty_diff.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                        ),
                    ))

        return findings

    def _check_reference_mismatch(self, po: Any, invoice: Any) -> List[DiscrepancyFinding]:
        findings: List[DiscrepancyFinding] = []
        po_number = getattr(po, "document_number", None) or getattr(po, "document_number", None)
        inv_ref = getattr(invoice, "purchase_order_reference", None)
        if po_number and inv_ref and str(po_number).strip() != str(inv_ref).strip():
            findings.append(DiscrepancyFinding(
                discrepancy_type=DiscrepancyType.REFERENCE_MISMATCH,
                severity=Severity.CRITICAL,
                description=(
                    f"Invoice PO reference '{inv_ref}' does not match purchase order number '{po_number}'."
                ),
                expected_value=str(po_number),
                actual_value=str(inv_ref),
                evidence_references=f"PO document number: {po_number}; Invoice PO reference: {inv_ref}",
                requires_review=True,
                plain_language_explanation=self._plain_language_explanation(
                    "REFERENCE_MISMATCH",
                    description=f"Invoice PO reference '{inv_ref}' does not match purchase order number '{po_number}'.",
                    expected_value=str(po_number),
                    actual_value=str(inv_ref),
                    difference=None,
                ),
            ))
        return findings

    def _check_document_arithmetic(self, doc: Any, label: str) -> List[DiscrepancyFinding]:
        findings: List[DiscrepancyFinding] = []
        line_items = getattr(doc, "line_items", None) or []
        subtotal = self._decimal(getattr(doc, "subtotal", None))
        tax = self._decimal(getattr(doc, "tax_amount", None))
        grand_total = self._decimal(getattr(doc, "grand_total", None))

        # line_total == qty * unit_price
        for idx, li in enumerate(line_items):
            qty = self._decimal(li.quantity)
            price = self._decimal(li.unit_price)
            total = self._decimal(li.line_total)
            if qty is None or price is None or total is None:
                continue
            expected = (qty * price).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if total != expected:
                findings.append(DiscrepancyFinding(
                    discrepancy_type=DiscrepancyType.ARITHMETIC_INCONSISTENCY,
                    severity=Severity.MEDIUM,
                    description=(
                        f"{label} line '{li.description}': line total {total} "
                        f"≠ quantity × unit_price ({expected})."
                    ),
                    expected_value=str(expected),
                    actual_value=str(total),
                    difference=str((total - expected).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                    calculation_details=f"{qty} × {price} = {expected}; recorded {total}",
                    evidence_references=self._evidence({
                        "description": li.description,
                        "source_page": li.source_page,
                        "source_text": li.source_text,
                    }),
                    plain_language_explanation=self._plain_language_explanation(
                        "ARITHMETIC_INCONSISTENCY",
                        description=f"{label} line '{li.description}': line total {total} ≠ quantity × unit_price ({expected}).",
                        expected_value=str(expected),
                        actual_value=str(total),
                        difference=str((total - expected).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                    ),
                ))

        # subtotal == sum(line_totals)
        line_totals = [self._decimal(li.line_total) for li in line_items if self._decimal(li.line_total) is not None]
        if line_totals and subtotal is not None:
            expected_subtotal = sum(line_totals).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if subtotal != expected_subtotal:
                findings.append(DiscrepancyFinding(
                    discrepancy_type=DiscrepancyType.ARITHMETIC_INCONSISTENCY,
                    severity=Severity.MEDIUM,
                    description=f"{label}: subtotal {subtotal} ≠ sum of line totals ({expected_subtotal}).",
                    expected_value=str(expected_subtotal),
                    actual_value=str(subtotal),
                    calculation_details=f"sum of line totals = {expected_subtotal}",
                    plain_language_explanation=self._plain_language_explanation(
                        "ARITHMETIC_INCONSISTENCY",
                        description=f"{label}: subtotal {subtotal} ≠ sum of line totals ({expected_subtotal}).",
                        expected_value=str(expected_subtotal),
                        actual_value=str(subtotal),
                        difference=str((subtotal - expected_subtotal).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                    ),
                ))

        # grand_total == subtotal + tax
        if subtotal is not None and grand_total is not None:
            tax_eff = tax if tax is not None else Decimal("0")
            expected_grand = (subtotal + tax_eff).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if grand_total != expected_grand:
                findings.append(DiscrepancyFinding(
                    discrepancy_type=DiscrepancyType.ARITHMETIC_INCONSISTENCY,
                    severity=Severity.MEDIUM,
                    description=f"{label}: grand total {grand_total} ≠ subtotal + tax ({expected_grand}).",
                    expected_value=str(expected_grand),
                    actual_value=str(grand_total),
                    calculation_details=f"{subtotal} + {tax_eff} = {expected_grand}",
                    plain_language_explanation=self._plain_language_explanation(
                        "ARITHMETIC_INCONSISTENCY",
                        description=f"{label}: grand total {grand_total} ≠ subtotal + tax ({expected_grand}).",
                        expected_value=str(expected_grand),
                        actual_value=str(grand_total),
                        difference=str((grand_total - expected_grand).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)),
                    ),
                ))

        return findings

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _decimal(value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                return Decimal(value)
            except Exception:
                return None
        return None

    @staticmethod
    def _plain_language_explanation(
        dtype: str,
        description: str,
        expected_value: Optional[str],
        actual_value: Optional[str],
        difference: Optional[str],
    ) -> str:
        """Generate a plain-language explanation anyone can understand."""
        if dtype == "PRICE_MISMATCH":
            return (
                f"The vendor charged {actual_value} per unit, but the purchase order "
                f"agreed on {expected_value} per unit. That's a {difference} difference per unit."
            )
        if dtype == "QUANTITY_MISMATCH":
            if description and "ordered but not invoiced" in description:
                return (
                    f"You ordered {expected_value} units but the invoice only bills {actual_value} units. "
                    f"{abs(float(difference)) if difference else 0} units were never invoiced."
                )
            if description and "invoiced but undelivered" in description:
                return (
                    f"The invoice bills {expected_value} units, but only {actual_value} units were received. "
                    f"{abs(float(difference)) if difference else 0} units were billed but not delivered."
                )
            if description and "received but not fully invoiced" in description:
                return (
                    f"You received {actual_value} units, but the invoice only covers {expected_value} units. "
                    f"{abs(float(difference)) if difference else 0} units were received but not billed."
                )
            return (
                f"The quantities don't match: expected {expected_value}, got {actual_value}. "
                f"Difference of {difference} units."
            )
        if dtype == "UNORDERED_ITEM":
            return (
                f"The invoice includes '{actual_value}', which was never on the purchase order. "
                f"This item was not ordered."
            )
        if dtype == "UNBILLED_RECEIPT":
            return (
                f"You received '{actual_value}' but it was never billed on the invoice. "
                f"This item was received but not invoiced."
            )
        if dtype == "MISSING_LINE_ITEM":
            return (
                f"The invoice item '{actual_value}' could not be matched to any purchase order item. "
                f"Manual review is recommended."
            )
        if dtype == "REFERENCE_MISMATCH":
            return (
                f"The invoice references purchase order '{actual_value}', but the actual PO is '{expected_value}'. "
                f"The document references don't match."
            )
        if dtype == "ARITHMETIC_INCONSISTENCY":
            return (
                f"The math doesn't add up: expected {expected_value} but the document shows {actual_value}. "
                f"Difference of {difference}."
            )
        return description or "A discrepancy was found."

    @staticmethod
    def _evidence(*items: Dict[str, Any]) -> str:
        refs = []
        for item in items:
            if not item:
                continue
            desc = item.get("description") or "item"
            page = item.get("source_page")
            text = item.get("source_text") or ""
            ref = f"{desc}" + (f" (page {page})" if page is not None else "")
            if text:
                ref += f" — '{text[:80]}'"
            refs.append(ref)
        return "; ".join(refs)
