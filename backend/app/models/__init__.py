"""SQLAlchemy models for InvoiceGuard.

All financial fields use Numeric (decimal-safe) — never binary floating point for currency.
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class CaseStatus(str, enum.Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    READY_FOR_RECONCILIATION = "READY_FOR_RECONCILIATION"
    RECONCILED = "RECONCILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class DocumentType(str, enum.Enum):
    PURCHASE_ORDER = "PURCHASE_ORDER"
    VENDOR_INVOICE = "VENDOR_INVOICE"
    GOODS_RECEIPT_NOTE = "GOODS_RECEIPT_NOTE"


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReconciliationCase(Base):
    __tablename__ = "reconciliation_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_reference = Column(String(100), unique=True, index=True, nullable=False)
    vendor_name = Column(String(255), nullable=True)
    status = Column(Enum(CaseStatus), default=CaseStatus.CREATED, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    extracted_data = relationship("ExtractedDocumentData", back_populates="case", cascade="all, delete-orphan")
    reconciliation_result = relationship(
        "ReconciliationResult", back_populates="case", uselist=False, cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("reconciliation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(Enum(DocumentType), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_checksum = Column(String(128), nullable=True)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("ReconciliationCase", back_populates="documents")
    extracted_data = relationship("ExtractedDocumentData", back_populates="document", uselist=False, cascade="all, delete-orphan")


class ExtractedDocumentData(Base):
    __tablename__ = "extracted_document_data"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("reconciliation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_number = Column(String(100), nullable=True)
    document_date = Column(String(50), nullable=True)
    vendor_name = Column(String(255), nullable=True)
    purchase_order_reference = Column(String(100), nullable=True)
    currency = Column(String(20), nullable=True)
    subtotal = Column(Numeric(18, 6), nullable=True)
    tax_amount = Column(Numeric(18, 6), nullable=True)
    grand_total = Column(Numeric(18, 6), nullable=True)
    extraction_status = Column(Enum(ExtractionStatus), default=ExtractionStatus.PENDING, nullable=False)
    extraction_model = Column(String(100), nullable=True)
    extraction_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="extracted_data")
    case = relationship("ReconciliationCase", back_populates="extracted_data")
    line_items = relationship("ExtractedLineItem", back_populates="extracted_document", cascade="all, delete-orphan")


class ExtractedLineItem(Base):
    __tablename__ = "extracted_line_items"

    id = Column(Integer, primary_key=True, index=True)
    extracted_document_id = Column(
        Integer, ForeignKey("extracted_document_data.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description = Column(Text, nullable=False)
    product_code = Column(String(100), nullable=True)
    quantity = Column(Numeric(18, 6), nullable=True)
    unit_price = Column(Numeric(18, 6), nullable=True)
    line_total = Column(Numeric(18, 6), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_text = Column(Text, nullable=True)

    extracted_document = relationship("ExtractedDocumentData", back_populates="line_items")


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("reconciliation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_status = Column(String(50), nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    review_required = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("ReconciliationCase", back_populates="reconciliation_result")
    discrepancies = relationship("Discrepancy", back_populates="reconciliation_result", cascade="all, delete-orphan")


class DiscrepancyType(str, enum.Enum):
    PRICE_MISMATCH = "PRICE_MISMATCH"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    UNORDERED_ITEM = "UNORDERED_ITEM"
    UNBILLED_RECEIPT = "UNBILLED_RECEIPT"
    MISSING_LINE_ITEM = "MISSING_LINE_ITEM"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    ARITHMETIC_INCONSISTENCY = "ARITHMETIC_INCONSISTENCY"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Discrepancy(Base):
    __tablename__ = "discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    reconciliation_result_id = Column(
        Integer, ForeignKey("reconciliation_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    discrepancy_type = Column(Enum(DiscrepancyType), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    description = Column(Text, nullable=False)
    expected_value = Column(Text, nullable=True)
    actual_value = Column(Text, nullable=True)
    difference = Column(Text, nullable=True)
    calculation_details = Column(Text, nullable=True)
    evidence_references = Column(Text, nullable=True)
    requires_review = Column(Boolean, default=False, nullable=False)
    plain_language_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    reconciliation_result = relationship("ReconciliationResult", back_populates="discrepancies")
