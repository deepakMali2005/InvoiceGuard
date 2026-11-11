"""Reporting service: PDF and CSV reconciliation reports."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    SimpleDocTemplate,
)
from reportlab.lib import colors

from app.core.exceptions import ReportError
from app.core.logging import logger
from app.models import Discrepancy, ReconciliationResult


class ReportingService:
    """Generates downloadable reconciliation reports (PDF and CSV)."""

    def generate_csv(self, result: ReconciliationResult, discrepancies: List[Discrepancy]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Reconciliation Report"])
        writer.writerow(["Case ID", result.case_id])
        writer.writerow(["Overall Status", result.overall_status])
        writer.writerow(["Findings Count", result.findings_count])
        writer.writerow(["Review Required", result.review_required])
        writer.writerow(["Generated At", datetime.now(timezone.utc).isoformat()])
        writer.writerow([])
        writer.writerow([
            "Discrepancy Type", "Severity", "Description", "Expected Value",
            "Actual Value", "Difference", "Calculation Details", "Evidence References", "Requires Review",
        ])
        for d in discrepancies:
            writer.writerow([
                d.discrepancy_type, d.severity, d.description, d.expected_value,
                d.actual_value, d.difference, d.calculation_details,
                d.evidence_references, d.requires_review,
            ])
        return output.getvalue()

    def generate_pdf(self, result: ReconciliationResult, discrepancies: List[Discrepancy]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="InvoiceGuard Reconciliation Report")
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("InvoiceGuard — Reconciliation Report", styles["Title"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Case ID: {result.case_id}", styles["Normal"]))
        story.append(Paragraph(f"Overall Status: {result.overall_status}", styles["Normal"]))
        story.append(Paragraph(f"Findings Count: {result.findings_count}", styles["Normal"]))
        story.append(Paragraph(f"Review Required: {result.review_required}", styles["Normal"]))
        story.append(Paragraph(f"Generated At: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
        story.append(Spacer(1, 12))

        if discrepancies:
            story.append(Paragraph("Discrepancies", styles["Heading2"]))
            data = [[
                "Type", "Severity", "Description", "Expected", "Actual", "Difference", "Evidence",
            ]]
            for d in discrepancies:
                data.append([
                    str(d.discrepancy_type), str(d.severity), d.description,
                    str(d.expected_value or ""), str(d.actual_value or ""),
                    str(d.difference or ""), str(d.evidence_references or ""),
                ])
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No discrepancies found. Documents match within configured tolerances.", styles["Normal"]))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
