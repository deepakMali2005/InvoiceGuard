"""SQLAlchemy repository for documents."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Document, DocumentType, ProcessingStatus


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

    def update_processing_status(self, document: Document, status: str) -> Document:
        document.processing_status = status
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document_id: int) -> bool:
        document = self.get(document_id)
        if not document:
            return False
        self.db.delete(document)
        self.db.commit()
        return True
