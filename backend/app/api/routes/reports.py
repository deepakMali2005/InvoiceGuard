"""Reports API routes."""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_db, get_reporting_service
from app.models import ReconciliationResult
from io import BytesIO

router = APIRouter(prefix="/api/v1/cases", tags=["reports"])


@router.get("/{case_id}/report")
def report(case_id: int, format: str = "pdf", db = Depends(get_db), svc = Depends(get_reporting_service)):
    rr = db.query(ReconciliationResult).filter(ReconciliationResult.case_id == case_id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    if format == "csv":
        content = svc.generate_csv(rr, rr.discrepancies)
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="reconciliation_case_{case_id}.csv"'},
        )
    if format == "pdf":
        pdf_bytes = svc.generate_pdf(rr, rr.discrepancies)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="reconciliation_case_{case_id}.pdf"'},
        )
    raise HTTPException(status_code=400, detail="Unsupported format. Use 'pdf' or 'csv'.")
