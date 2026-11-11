"""Documents API routes."""

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_db, get_document_service
from app.core.exceptions import DocumentError
from app.core.logging import logger
from app.models import DocumentType
from app.repositories.case import CaseRepository
from app.repositories.document import DocumentRepository

router = APIRouter(prefix="/api/v1/cases", tags=["documents"])


@router.post("/{case_id}/documents", status_code=status.HTTP_201_CREATED)
def upload_document(
    case_id: int,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db = Depends(get_db),
    doc_service = Depends(get_document_service),
):
    case = CaseRepository(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        doc_type = DocumentType[document_type.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")

    content = file.file.read()
    try:
        payload = doc_service.save(file.filename or "document.pdf", content)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=exc.message)

    doc = DocumentRepository(db).create(
        case_id=case_id,
        document_type=doc_type,
        original_filename=payload.original_filename,
        storage_path=payload.storage_path,
        mime_type=payload.mime_type,
        file_checksum=payload.file_checksum,
    )
    DocumentRepository(db).update_processing_status(doc, "COMPLETED")

    return {
        "id": doc.id,
        "case_id": doc.case_id,
        "document_type": doc.document_type,
        "original_filename": doc.original_filename,
        "storage_path": doc.storage_path,
        "mime_type": doc.mime_type,
        "file_checksum": doc.file_checksum,
        "processing_status": doc.processing_status,
        "extracted_text_preview": payload.extracted_text[:500],
        "page_count": payload.page_count,
    }


@router.get("/{case_id}/documents")
def list_documents(case_id: int, db = Depends(get_db)):
    if not CaseRepository(db).get(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    docs = DocumentRepository(db).list_for_case(case_id)
    return [
        {
            "id": d.id,
            "document_type": d.document_type,
            "original_filename": d.original_filename,
            "storage_path": d.storage_path,
            "mime_type": d.mime_type,
            "processing_status": d.processing_status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
    }

        for d in docs
    ]


@router.get("/documents/{document_id}")
def get_document(document_id: int, db = Depends(get_db)):
    doc = DocumentRepository(db).get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "case_id": doc.case_id,
        "document_type": doc.document_type,
        "original_filename": doc.original_filename,
        "storage_path": doc.storage_path,
        "mime_type": doc.mime_type,
        "processing_status": doc.processing_status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db = Depends(get_db), doc_service = Depends(get_document_service)):
    """Delete a single document and remove its file from storage."""
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove the physical file from storage
    try:
        if doc.storage_path and os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)
            logger.info("Deleted storage file %s", doc.storage_path)
    except OSError as exc:
        logger.warning("Could not delete storage file %s: %s", doc.storage_path, exc)

    if not doc_repo.delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return None
