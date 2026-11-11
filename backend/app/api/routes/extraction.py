"""Extraction API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db, get_extraction_service
from app.core.exceptions import ExtractionError
from app.models import Document, ExtractedDocumentData, ExtractionStatus
from app.repositories.document import DocumentRepository
from app.repositories.case import CaseRepository
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/documents", tags=["extraction"])


@router.post("/{document_id}/extract")
def extract(document_id: int, db: Session = Depends(get_db), svc = Depends(get_extraction_service)):
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Re-extract text from stored PDF
    from app.services.document.service import DocumentService
    from pathlib import Path
    dsvc = DocumentService()
    text, _ = dsvc.extract_pdf_text(Path(doc.storage_path))

    try:
        result = svc.extract(text)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=exc.message)

    # Persist extracted data
    case_repo = CaseRepository(db)
    case = case_repo.get(doc.case_id)
    ed = ExtractedDocumentData(
        document_id=doc.id,
        case_id=doc.case_id,
        document_number=result.document_number,
        document_date=result.document_date,
        vendor_name=result.vendor_name,
        purchase_order_reference=result.purchase_order_reference,
        currency=result.currency,
        subtotal=result.subtotal,
        tax_amount=result.tax_amount,
        grand_total=result.grand_total,
        extraction_status=ExtractionStatus.COMPLETED if result else ExtractionStatus.FAILED,
        extraction_model="mock" if svc.is_mocked() else "nemotron",
        extraction_provider="mock" if svc.is_mocked() else "nemotron",
    )
    db.add(ed)
    db.flush()
    for li in result.line_items:
        from app.models import ExtractedLineItem
        db.add(ExtractedLineItem(
            extracted_document_id=ed.id,
            description=li.description,
            product_code=li.product_code,
            quantity=li.quantity,
            unit_price=li.unit_price,
            line_total=li.line_total,
            source_page=li.source_page,
            source_text=li.source_text,
        ))
    doc_repo.update_processing_status(doc, "COMPLETED")
    db.commit()
    db.refresh(ed)
    return {
        "extracted_document_id": ed.id,
        "document_type": result.document_type,
        "document_number": result.document_number,
        "vendor_name": result.vendor_name,
        "currency": result.currency,
        "line_items_count": len(result.line_items),
        "mocked": svc.is_mocked(),
    }


@router.get("/{document_id}/extraction")
def get_extraction(document_id: int, db: Session = Depends(get_db)):
    ed = db.query(ExtractedDocumentData).filter(ExtractedDocumentData.document_id == document_id).first()
    if not ed:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return {
        "id": ed.id,
        "document_number": ed.document_number,
        "document_date": ed.document_date,
        "vendor_name": ed.vendor_name,
        "purchase_order_reference": ed.purchase_order_reference,
        "currency": ed.currency,
        "subtotal": str(ed.subtotal) if ed.subtotal is not None else None,
        "tax_amount": str(ed.tax_amount) if ed.tax_amount is not None else None,
        "grand_total": str(ed.grand_total) if ed.grand_total is not None else None,
        "extraction_status": ed.extraction_status,
        "extraction_model": ed.extraction_model,
        "extraction_provider": ed.extraction_provider,
        "line_items": [
            {
                "description": li.description,
                "product_code": li.product_code,
                "quantity": str(li.quantity) if li.quantity is not None else None,
                "unit_price": str(li.unit_price) if li.unit_price is not None else None,
                "line_total": str(li.line_total) if li.line_total is not None else None,
                "source_page": li.source_page,
                "source_text": li.source_text,
            }
            for li in ed.line_items
        ],
    }
