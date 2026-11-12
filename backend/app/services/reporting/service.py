"""Reporting service: PDF and CSV reconciliation reports."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    SimpleDocTemplate,
    HRFlowable,
    KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents

from app.core.exceptions import ReportError
from app.core.logging import logger
from app.models import Discrepancy, ReconciliationResult

# InvoiceGuard brand colors
INK = colors.HexColor("#0f172a")        # deep slate
PRIMARY = colors.HexColor("#2563eb")    # brand blue
PRIMARY_LIGHT = colors.HexColor("#dbeafe")  # light blue tint
ACCENT = colors.HexColor("#059669")     # green accent
ACCENT_LIGHT = colors.HexColor("#d1fae5")
WARNING = colors.HexColor("#d97706")    # amber
WARNING_LIGHT = colors.HexColor("#fef3c7")
DANGER = colors.HexColor("#dc2626")     # red
DANGER_LIGHT = colors.HexColor("#fee2e2")
GREY_BG = colors.HexColor("#f8fafc")    # light grey background
BORDER = colors.HexColor("#cbd5e1")     # light border
TEXT_MUTED = colors.HexColor("#64748b") # muted text


def _status_color(status: str) -> colors.Color:
    s = (status or "").upper()
    if s in ("MATCHED", "CLEAN"):
        return ACCENT
    if s in ("DISCREPANCIES_FOUND", "NEEDS_REVIEW"):
        return WARNING
    if s in ("ERROR", "FAILED"):
        return DANGER
    return PRIMARY


def _severity_color(severity: str) -> colors.Color:
    s = (severity or "").upper()
    if s == "HIGH":
        return DANGER
    if s == "MEDIUM":
        return WARNING
    if s == "LOW":
        return ACCENT
    return TEXT_MUTED


def _color_hex(c: colors.Color) -> str:
    """Convert a reportlab Color to a hex string for Paragraph markup."""
    return "#{:02x}{:02x}{:02x}".format(int(c.red * 255), int(c.green * 255), int(c.blue * 255))


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
            "Plain Language Explanation",
        ])
        for d in discrepancies:
            writer.writerow([
                d.discrepancy_type, d.severity, d.description, d.expected_value,
                d.actual_value, d.difference, d.calculation_details,
                d.evidence_references, d.requires_review,
                getattr(d, "plain_language_explanation", "") or "",
            ])
        return output.getvalue()

    def generate_pdf(self, result: ReconciliationResult, discrepancies: List[Discrepancy]) -> bytes:
        buffer = io.BytesIO()

        # Landscape A4 gives ample width for the 7-column table without clipping.
        page_w, page_h = landscape(A4)
        margin = 40  # points on each side — safe margin, no clipping
        content_w = page_w - 2 * margin

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=margin,
            rightMargin=margin,
            topMargin=46,
            bottomMargin=46,
            title="InvoiceGuard Reconciliation Report",
            author="InvoiceGuard",
        )

        styles = getSampleStyleSheet()

        # Custom paragraph styles
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=INK,
            spaceAfter=2,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            textColor=TEXT_MUTED,
            spaceAfter=0,
        )
        section_style = ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=PRIMARY,
            spaceBefore=16,
            spaceAfter=6,
        )
        label_style = ParagraphStyle(
            "Label",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=TEXT_MUTED,
        )
        value_style = ParagraphStyle(
            "Value",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=INK,
        )
        cell_style = ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            textColor=INK,
            leading=10.5,
        )
        cell_header_style = ParagraphStyle(
            "CellHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.white,
            leading=11,
        )
        plain_style = ParagraphStyle(
            "Plain",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=INK,
            leading=12,
            spaceAfter=4,
        )
        plain_label_style = ParagraphStyle(
            "PlainLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=ACCENT,
        )

        story = []

        # ---- Title bar ----
        title_table = Table(
            [[
                Paragraph("InvoiceGuard", ParagraphStyle(
                    "brand", parent=styles["Normal"],
                    fontName="Helvetica-Bold", fontSize=16, textColor=colors.white,
                )),
                Paragraph("Reconciliation Report", ParagraphStyle(
                    "rtitle", parent=styles["Normal"],
                    fontName="Helvetica-Bold", fontSize=16, textColor=colors.white,
                    alignment=2,  # right
                )),
            ]],
            colWidths=[content_w * 0.5, content_w * 0.5],
        )
        title_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(title_table)
        story.append(Spacer(1, 2))
        story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
        story.append(Spacer(1, 10))

        # ---- Case summary ----
        story.append(Paragraph("Case Summary", section_style))

        status_color = _status_color(result.overall_status)
        summary_data = [
            [
                Paragraph("Case ID", label_style),
                Paragraph(str(result.case_id), value_style),
                Paragraph("Overall Status", label_style),
                Paragraph(
                    f'<font color="{_color_hex(status_color)}"><b>{result.overall_status}</b></font>',
                    value_style,
                ),
            ],
            [
                Paragraph("Findings Count", label_style),
                Paragraph(str(result.findings_count), value_style),
                Paragraph("Review Required", label_style),
                Paragraph(str(result.review_required), value_style),
            ],
            [
                Paragraph("Generated At", label_style),
                Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), value_style),
                Paragraph("Document", label_style),
                Paragraph("PO + Invoice + GRN", value_style),
            ],
        ]
        summary_table = Table(summary_data, colWidths=[content_w * 0.17, content_w * 0.33, content_w * 0.17, content_w * 0.33])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREY_BG),
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # ---- Discrepancies ----
        story.append(Paragraph("Discrepancy Findings", section_style))

        if discrepancies:
            # Column widths that sum to content_w and wrap text safely.
            col_widths = [
                content_w * 0.135,   # Type
                content_w * 0.095,   # Severity
                content_w * 0.27,    # Description
                content_w * 0.135,   # Expected
                content_w * 0.135,   # Actual
                content_w * 0.105,   # Difference
                content_w * 0.125,   # Evidence
            ]

            header = [
                Paragraph("Type", cell_header_style),
                Paragraph("Severity", cell_header_style),
                Paragraph("Description", cell_header_style),
                Paragraph("Expected Value", cell_header_style),
                Paragraph("Actual Value", cell_header_style),
                Paragraph("Difference", cell_header_style),
                Paragraph("Evidence References", cell_header_style),
            ]

            rows = [header]
            for d in discrepancies:
                sev_color = _severity_color(d.severity)
                rows.append([
                    Paragraph(str(d.discrepancy_type or ""), cell_style),
                    Paragraph(
                        f'<font color="{_color_hex(sev_color)}"><b>{d.severity}</b></font>',
                        cell_style,
                    ),
                    Paragraph(d.description or "", cell_style),
                    Paragraph(str(d.expected_value or "—"), cell_style),
                    Paragraph(str(d.actual_value or "—"), cell_style),
                    Paragraph(str(d.difference or "—"), cell_style),
                    Paragraph(str(d.evidence_references or "—"), cell_style),
                ])

            table = Table(rows, colWidths=col_widths, repeatRows=1)
            table_style = [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
            # Alternating row shading
            for i in range(1, len(rows)):
                if i % 2 == 0:
                    table_style.append(("BACKGROUND", (0, i), (-1, i), GREY_BG))
            table.setStyle(TableStyle(table_style))
            story.append(table)
        else:
            no_findings = Table(
                [[Paragraph(
                    "No discrepancies found. All documents match within configured tolerances.",
                    ParagraphStyle(
                        "nofindings",
                        parent=plain_style,
                        alignment=1,
                        textColor=ACCENT,
                        fontName="Helvetica-Bold",
                    ),
                )]],
                colWidths=[content_w],
            )
            no_findings.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), ACCENT_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.75, ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]))
            story.append(no_findings)

        story.append(Spacer(1, 16))

        # ---- Plain language explanations ----
        story.append(Paragraph("What This Means (Plain Language)", section_style))

        if discrepancies:
            for idx, d in enumerate(discrepancies, start=1):
                explanation = getattr(d, "plain_language_explanation", None) or ""
                sev_color = _severity_color(d.severity)
                block = Table(
                    [[
                        Paragraph(f"Finding {idx} — {d.discrepancy_type}", ParagraphStyle(
                            f"f{idx}t", parent=plain_label_style,
                            textColor=sev_color,
                        )),
                    ],
                    [Paragraph(explanation or "No explanation available.", plain_style)]],
                    colWidths=[content_w],
                )
                block.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, 0), PRIMARY_LIGHT),
                    ("BACKGROUND", (0, 1), (0, 1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]))
                story.append(KeepTogether(block))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(
                "All documents matched — no discrepancies to explain.",
                ParagraphStyle("emptyplain", parent=plain_style, textColor=TEXT_MUTED),
            ))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.75, color=BORDER))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Generated by InvoiceGuard — AI-Assisted Invoice Reconciliation and Verification System.",
            ParagraphStyle("footer", parent=styles["Normal"], fontSize=8, textColor=TEXT_MUTED, alignment=1),
        ))

        def _footer(canvas, doc_obj):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(TEXT_MUTED)
            canvas.drawString(margin, 18, "InvoiceGuard — Confidential")
            canvas.drawRightString(page_w - margin, 18, f"Page {doc_obj.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
