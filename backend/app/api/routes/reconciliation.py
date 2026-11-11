"""Reconciliation API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db, get_reconciliation_service
from app.models import ExtractedDocumentData, ReconciliationResult
from app.repositories.case import CaseRepository
from app.models import Discrepancy
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/cases", tags=["reconciliation"])


@router.post("/{case_id}/reconcile")
def reconcile(case_id: int, db: Session = Depends(get_db), svc = Depends(get_reconciliation_service)):
    case = CaseRepository(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    extras = {e.document.document_type: e for e in db.query(ExtractedDocumentData).filter(ExtractedDocumentData.case_id == case_id).all()}

    po = extras.get("PURCHASE_ORDER")
    invoice = extras.get("VENDOR_INVOICE")
    grn = extras.get("GOODS_RECEIPT_NOTE")

    missing = [name for name, obj in (("PURCHASE_ORDER", po), ("VENDOR_INVOICE", invoice), ("GOODS_RECEIPT_NOTE", grn)) if obj is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing extracted documents: {', '.join(missing)}")

    try:
        result, discrepancies = svc.reconcile(po, invoice, grn)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    rr = ReconciliationResult(
        case_id=case_id,
        overall_status=result.overall_status,
        findings_count=len(discrepancies),
        review_required=result.review_required,
    )
    db.add(rr)
    db.flush()
    for d in discrepancies:
        db.add(Discrepancy(
            reconciliation_result_id=rr.id,
            discrepancy_type=d.discrepancy_type,
            severity=d.severity,
            description=d.description,
            expected_value=d.expected_value,
            actual_value=d.actual_value,
            difference=d.difference,
            calculation_details=d.calculation_details,
            evidence_references=d.evidence_references,
            requires_review=d.requires_review,
            plain_language_explanation=d.plain_language_explanation,
        ))
    new_status = "RECONCILED" if result.overall_status == "MATCHED" else ("NEEDS_REVIEW" if result.review_required else "RECONCILED")
    CaseRepository(db).update_status(case, new_status)
    db.commit()
    db.refresh(rr)
    return {
        "reconciliation_result_id": rr.id,
        "case_id": case_id,
        "overall_status": result.overall_status,
        "findings_count": len(discrepancies),
        "review_required": result.review_required,
        "discrepancies": [
            {
                "type": d.discrepancy_type,
                "severity": d.severity,
                "description": d.description,
                "expected_value": d.expected_value,
                "actual_value": d.actual_value,
                "difference": d.difference,
                "calculation_details": d.calculation_details,
                "evidence_references": d.evidence_references,
                "requires_review": d.requires_review,
                "plain_language_explanation": d.plain_language_explanation,
            }
            for d in discrepancies
        ],
    }


@router.get("/{case_id}/reconciliation")
def get_reconciliation(case_id: int, db: Session = Depends(get_db)):
    rr = db.query(ReconciliationResult).filter(ReconciliationResult.case_id == case_id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return {
        "id": rr.id,
        "case_id": rr.case_id,
        "overall_status": rr.overall_status,
        "findings_count": rr.findings_count,
        "review_required": rr.review_required,
        "created_at": rr.created_at.isoformat() if rr.created_at else None,
        "discrepancies": [
            {
                "type": d.discrepancy_type,
                "severity": d.severity,
                "description": d.description,
                "expected_value": d.expected_value,
                "actual_value": d.actual_value,
                "difference": d.difference,
                "calculation_details": d.calculation_details,
                "evidence_references": d.evidence_references,
                "requires_review": d.requires_review,
            }
            for d in rr.discrepancies
        ],
    }
