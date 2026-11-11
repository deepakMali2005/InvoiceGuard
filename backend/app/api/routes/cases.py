"""Cases API routes."""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_document_service, get_extraction_service, get_validation_service
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.core.exceptions import InvoiceGuardError
from app.core.logging import logger
from app.models import DocumentType, ReconciliationCase
from app.repositories.case import CaseRepository
from app.repositories.document import DocumentRepository

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def _repo(db: Session) -> CaseRepository:
    return CaseRepository(db)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_case(case_reference: str, vendor_name: Optional[str] = None, db: Session = Depends(get_db)):
    if _repo(db).get_by_reference(case_reference):
        raise HTTPException(status_code=409, detail="Case reference already exists")
    case = _repo(db).create(case_reference=case_reference, vendor_name=vendor_name)
    return {"id": case.id, "case_reference": case.case_reference, "vendor_name": case.vendor_name, "status": case.status}


@router.get("/")
def list_cases(db: Session = Depends(get_db)):
    cases = _repo(db).list()
    return [
        {"id": c.id, "case_reference": c.case_reference, "vendor_name": c.vendor_name, "status": c.status,
         "created_at": c.created_at.isoformat() if c.created_at else None}
        for c in cases
    ]


@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = _repo(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "id": case.id,
        "case_reference": case.case_reference,
        "vendor_name": case.vendor_name,
        "status": case.status,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """Delete a case and all its associated documents and extracted data."""
    case = _repo(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Delete associated document files from storage
    doc_repo = DocumentRepository(db)
    for d in doc_repo.list_for_case(case_id):
        try:
            if d.storage_path and os.path.exists(d.storage_path):
                os.remove(d.storage_path)
                logger.info("Deleted storage file %s", d.storage_path)
        except OSError as exc:
            logger.warning("Could not delete storage file %s: %s", d.storage_path, exc)

    if not _repo(db).delete(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return None
