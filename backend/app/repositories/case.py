"""SQLAlchemy repositories for InvoiceGuard."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import (
    Document,
    DocumentType,
    ExtractedDocumentData,
    ProcessingStatus,
    ReconciliationCase,
)


class CaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, case_reference: str, vendor_name: Optional[str] = None) -> ReconciliationCase:
        case = ReconciliationCase(case_reference=case_reference, vendor_name=vendor_name)
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def get(self, case_id: int) -> Optional[ReconciliationCase]:
        return self.db.query(ReconciliationCase).filter(ReconciliationCase.id == case_id).first()

    def get_by_reference(self, case_reference: str) -> Optional[ReconciliationCase]:
        return self.db.query(ReconciliationCase).filter(
            ReconciliationCase.case_reference == case_reference
        ).first()

    def list(self) -> List[ReconciliationCase]:
        return self.db.query(ReconciliationCase).order_by(ReconciliationCase.created_at.desc()).all()

    def update_status(self, case: ReconciliationCase, status: str) -> ReconciliationCase:
        case.status = status
        self.db.commit()
        self.db.refresh(case)
        return case

    def delete(self, case_id: int) -> bool:
        case = self.get(case_id)
        if not case:
            return False
        self.db.delete(case)
        self.db.commit()
        return True


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        case_id: int,
        document_type: DocumentType,
        original_filename: str,
        storage_path: str,
        mime_type: str,
        file_checksum: str,
    ) -> Document:
        doc = Document(
            case_id=case_id,
            document_type=document_type,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_checksum=file_checksum,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get(self, document_id: int) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def list_for_case(self, case_id: int) -> List[Document]:
        return self.db.query(Document).filter(Document.case_id == case_id).all()

    def update_processing_status(self, document: Document, status: ProcessingStatus) -> Document:
        document.processing_status = status
        self.db.commit()
        self.db.refresh(document)
        return document
