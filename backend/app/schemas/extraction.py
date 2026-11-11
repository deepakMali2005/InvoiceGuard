"""Pydantic schemas for AI extraction output."""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ExtractedLineItem(BaseModel):
    """A single line item extracted from a document."""

    description: str = Field(..., description="Item description as it appears on the document.")
    product_code: Optional[str] = Field(None, description="SKU/product code, when available.")
    quantity: Optional[str] = Field(None, description="Quantity as a decimal string.")
    unit_price: Optional[str] = Field(None, description="Unit price as a decimal string.")
    line_total: Optional[str] = Field(None, description="Line total as a decimal string.")
    source_page: Optional[int] = Field(None, description="Page number where this item appears.")
    source_text: Optional[str] = Field(None, description="Relevant source text from the document.")

    @field_validator("quantity", "unit_price", "line_total", mode="before")
    @classmethod
    def _strip_commas(cls, v):
        if isinstance(v, str):
            return v.replace(",", "")
        return v

    @model_validator(mode="after")
    def _validate_numeric_strings(self):
        for field_name in ("quantity", "unit_price", "line_total"):
            value = getattr(self, field_name)
            if value is not None and value != "":
                try:
                    Decimal(value)
                except Exception as exc:
                    raise ValueError(f"{field_name} must be a decimal string, got {value!r}") from exc
        return self


class ExtractionResult(BaseModel):
    """Structured extraction result matching the Nemotron response schema."""

    document_type: str = Field(..., description="Document type: PURCHASE_ORDER, VENDOR_INVOICE, GOODS_RECEIPT_NOTE.")
    document_number: Optional[str] = Field(None, description="Document number.")
    document_date: Optional[str] = Field(None, description="Document date (ISO format).")
    vendor_name: Optional[str] = Field(None, description="Vendor name.")
    purchase_order_reference: Optional[str] = Field(None, description="Referenced purchase order number.")
    currency: Optional[str] = Field(None, description="Currency code, e.g. INR, USD.")
    line_items: List[ExtractedLineItem] = Field(default_factory=list, description="Line items extracted from the document.")
    subtotal: Optional[str] = Field(None, description="Subtotal as a decimal string.")
    tax_amount: Optional[str] = Field(None, description="Tax amount as a decimal string.")
    grand_total: Optional[str] = Field(None, description="Grand total as a decimal string.")

    @field_validator("subtotal", "tax_amount", "grand_total", mode="before")
    @classmethod
    def _strip_commas_financial(cls, v):
        if isinstance(v, str):
            return v.replace(",", "")
        return v

    @model_validator(mode="after")
    def _validate_financial_strings(self):
        for field_name in ("subtotal", "tax_amount", "grand_total"):
            value = getattr(self, field_name)
            if value is not None and value != "":
                try:
                    Decimal(value)
                except Exception as exc:
                    raise ValueError(f"{field_name} must be a decimal string, got {value!r}") from exc
        return self
