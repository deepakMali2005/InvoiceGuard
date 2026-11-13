"""End-to-end API tests using FastAPI TestClient.

These exercise create_case -> upload documents -> extract -> reconcile -> report.
External LLM calls are mocked (USE_MOCK_LLM=true).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_pdf_bytes():
    import fitz
    import io
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "PO-100\nVendor: Acme Corp\nIndustrial Motor Qty 100 Rate 50000 Total 5000000")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf.read()


def test_e2e_flow():
    # Create case
    import time
    r = client.post("/api/v1/cases/", params={"case_reference": f"CASE-E2E-{int(time.time())}", "vendor_name": "Acme Corp"})
    assert r.status_code == 201, r.text
    case = r.json()
    case_id = case["id"]

    pdf_bytes = _make_pdf_bytes()

    # Upload PO
    r = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("po.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": "PURCHASE_ORDER"},
    )
    assert r.status_code == 201, r.text
    po_id = r.json()["id"]

    # Upload Invoice
    r = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("inv.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": "VENDOR_INVOICE"},
    )
    assert r.status_code == 201, r.text
    inv_id = r.json()["id"]

    # Upload GRN
    r = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("grn.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": "GOODS_RECEIPT_NOTE"},
    )
    assert r.status_code == 201, r.text
    grn_id = r.json()["id"]

    # Extract PO
    r = client.post(f"/api/v1/documents/{po_id}/extract")
    assert r.status_code == 200, r.text
    assert r.json()["mocked"] is True

    # Extract Invoice
    r = client.post(f"/api/v1/documents/{inv_id}/extract")
    assert r.status_code == 200, r.text

    # Extract GRN
    r = client.post(f"/api/v1/documents/{grn_id}/extract")
    assert r.status_code == 200, r.text

    # Reconcile
    r = client.post(f"/api/v1/cases/{case_id}/reconcile")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "overall_status" in body
    assert "findings_count" in body
    assert "discrepancies" in body

    # Report PDF
    r = client.get(f"/api/v1/cases/{case_id}/report?format=pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"

    # Report CSV
    r = client.get(f"/api/v1/cases/{case_id}/report?format=csv")
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]

    # Health
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["mocked_ai"] is True
