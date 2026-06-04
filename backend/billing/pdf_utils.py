"""
Professional PDF generation utilities for billing documents.

Provides a shared, professional invoice PDF template used by both
the user-facing and admin credit invoice PDF endpoints.

Design principles:
  - Clean, modern layout with brand color accent
  - Proper header/footer with company branding
  - Two-column layout: company info (left) + invoice details (right)
  - Professional line-items table with alternating row shading
  - Summary totals with clear visual hierarchy
  - Payment details and notes sections
"""

from io import BytesIO
from django.conf import settings

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)


# ─── Brand Colors ─────────────────────────────────────────────────────────────
BRAND_PRIMARY = colors.HexColor("#2563EB")   # Blue-600
BRAND_DARK = colors.HexColor("#1E40AF")      # Blue-800
BRAND_LIGHT = colors.HexColor("#EFF6FF")     # Blue-50
BRAND_ACCENT = colors.HexColor("#DBEAFE")    # Blue-100
TEXT_PRIMARY = colors.HexColor("#111827")     # Gray-900
TEXT_SECONDARY = colors.HexColor("#6B7280")  # Gray-500
TEXT_MUTED = colors.HexColor("#9CA3AF")      # Gray-400
BORDER_COLOR = colors.HexColor("#E5E7EB")    # Gray-200
ROW_ALT = colors.HexColor("#F9FAFB")         # Gray-50
STATUS_PAID = colors.HexColor("#059669")     # Green-600
STATUS_ISSUED = colors.HexColor("#2563EB")   # Blue-600
STATUS_PENDING = colors.HexColor("#D97706")  # Amber-600


def _format_cents(cents: int, currency: str) -> str:
    """Format cents amount to a display string like '$99.00'."""
    symbol = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}.get(
        currency.upper(), currency.upper() + " "
    )
    return f"{symbol}{cents / 100:,.2f}"


def _get_status_color(status: str):
    """Get the brand color for an invoice status."""
    s = (status or "").lower()
    if s == "paid":
        return STATUS_PAID
    if s in ("issued", "open", "draft"):
        return STATUS_ISSUED
    return TEXT_SECONDARY


def _build_styles():
    """Build all custom ParagraphStyles for the invoice PDF."""
    base = getSampleStyleSheet()

    styles = {
        # Header
        "company_name": ParagraphStyle(
            "CompanyName", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=22,
            textColor=BRAND_DARK, spaceAfter=2,
        ),
        "company_tagline": ParagraphStyle(
            "CompanyTagline", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            textColor=TEXT_SECONDARY, spaceAfter=12,
        ),
        # Title / Section headings
        "invoice_title": ParagraphStyle(
            "InvoiceTitle", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=28,
            textColor=BRAND_PRIMARY, spaceAfter=4,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=10,
            textColor=TEXT_PRIMARY, spaceBefore=16, spaceAfter=6,
        ),
        # Body text
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            textColor=TEXT_PRIMARY, leading=14,
        ),
        "body_muted": ParagraphStyle(
            "BodyMuted", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=TEXT_SECONDARY, leading=12,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9,
            textColor=TEXT_PRIMARY, leading=14,
        ),
        # Table cell styles
        "table_header": ParagraphStyle(
            "TableHeader", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=8,
            textColor=colors.white, leading=12,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            textColor=TEXT_PRIMARY, leading=13,
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            textColor=TEXT_PRIMARY, leading=13, alignment=TA_RIGHT,
        ),
        "table_cell_bold": ParagraphStyle(
            "TableCellBold", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9,
            textColor=TEXT_PRIMARY, leading=13,
        ),
        "table_cell_bold_right": ParagraphStyle(
            "TableCellBoldRight", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9,
            textColor=TEXT_PRIMARY, leading=13, alignment=TA_RIGHT,
        ),
        # Status badge
        "status_badge": ParagraphStyle(
            "StatusBadge", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=8,
            textColor=STATUS_PAID, leading=10,
        ),
        # Footer
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"],
            fontName="Helvetica", fontSize=7,
            textColor=TEXT_MUTED, alignment=TA_CENTER, leading=10,
        ),
        "footer_link": ParagraphStyle(
            "FooterLink", parent=base["Normal"],
            fontName="Helvetica", fontSize=7,
            textColor=BRAND_PRIMARY, alignment=TA_CENTER, leading=10,
        ),
    }
    return styles


def generate_credit_invoice_pdf(inv) -> bytes:
    """Generate a professional credit invoice PDF and return the raw bytes.

    Args:
        inv: CreditInvoice model instance with select_related(
            "user", "product", "plan", "credit_pool"
        )

    Returns:
        bytes: The raw PDF file content.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = _build_styles()
    story = []

    company_name = getattr(settings, "COMPANY_NAME", "SattaBase")
    company_domain = getattr(settings, "STRIPE_APP_DOMAIN", "")
    # Strip protocol for display
    if company_domain.startswith("https://"):
        company_domain = company_domain[8:]
    elif company_domain.startswith("http://"):
        company_domain = company_domain[7:]

    # ─── HEADER: Company + Invoice Title ────────────────────────────────────────
    header_data = [
        [
            # Left: Company branding
            Paragraph(company_name, styles["company_name"]),
            # Right: INVOICE title
            Paragraph("INVOICE", styles["invoice_title"]),
        ],
        [
            Paragraph("Billing & Subscription Platform", styles["company_tagline"]),
            Paragraph("", styles["body_muted"]),
        ],
    ]
    header_table = Table(header_data, colWidths=[3.8 * inch, 3.8 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("ALIGN", (1, 1), (1, 1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)

    # Accent line
    story.append(Spacer(1, 6))
    story.append(HRFlowable(
        width="100%", thickness=2, color=BRAND_PRIMARY,
        spaceAfter=16, spaceBefore=0,
    ))

    # ─── ROW: Invoice Details + Billed To ──────────────────────────────────────
    issued_at_str = inv.issued_at.strftime("%B %d, %Y") if inv.issued_at else "N/A"
    status_display = (inv.status or "").upper()
    status_color = _get_status_color(inv.status)

    # Status badge: colored rectangle around the status text
    status_style = ParagraphStyle(
        "StatusBadgeCustom", parent=styles["body_bold"],
        textColor=status_color, fontSize=9,
    )

    left_info = [
        [Paragraph("<b>Invoice Number</b>", styles["body_muted"]),
         Paragraph(inv.invoice_number, styles["body_bold"])],
        [Paragraph("<b>Issue Date</b>", styles["body_muted"]),
         Paragraph(issued_at_str, styles["body"])],
        [Paragraph("<b>Payment Method</b>", styles["body_muted"]),
         Paragraph("Bank Transfer", styles["body"])],
        [Paragraph("<b>Currency</b>", styles["body_muted"]),
         Paragraph(inv.currency.upper(), styles["body"])],
    ]
    left_table = Table(left_info, colWidths=[1.5 * inch, 2.2 * inch])
    left_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    right_info = [
        [Paragraph("<b>Status</b>", styles["body_muted"]),
         Paragraph(status_display, status_style)],
        [Paragraph("<b>Billed To</b>", styles["body_muted"]),
         Paragraph(inv.user.email, styles["body"])],
    ]
    # Add user name if available
    user_name = getattr(inv.user, "first_name", None)
    if user_name:
        right_info.insert(1, [
            Paragraph("", styles["body_muted"]),
            Paragraph(user_name, styles["body"]),
        ])

    right_table = Table(right_info, colWidths=[1.2 * inch, 2.5 * inch])
    right_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    detail_row = Table(
        [[left_table, right_table]],
        colWidths=[3.8 * inch, 3.8 * inch],
    )
    detail_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(detail_row)

    story.append(Spacer(1, 20))

    # ─── LINE ITEMS TABLE ──────────────────────────────────────────────────────
    story.append(Paragraph("Line Items", styles["section_heading"]))

    # Build line items
    col_widths = [4.3 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch]
    line_items_data = [
        [
            Paragraph("Description", styles["table_header"]),
            Paragraph("Qty", styles["table_header"]),
            Paragraph("Unit Price", styles["table_header"]),
            Paragraph("Amount", styles["table_header"]),
        ],
        [
            Paragraph(
                f"{inv.product.name} &mdash; {inv.plan.name}",
                styles["table_cell"],
            ),
            Paragraph("1", styles["table_cell_right"]),
            Paragraph(
                _format_cents(inv.amount_cents, inv.currency),
                styles["table_cell_right"],
            ),
            Paragraph(
                _format_cents(inv.amount_cents, inv.currency),
                styles["table_cell_right"],
            ),
        ],
    ]

    # Tax row if applicable
    if inv.tax_cents > 0:
        line_items_data.append([
            Paragraph("Tax", styles["table_cell"]),
            Paragraph("", styles["table_cell_right"]),
            Paragraph("", styles["table_cell_right"]),
            Paragraph(
                _format_cents(inv.tax_cents, inv.currency),
                styles["table_cell_right"],
            ),
        ])

    items_table = Table(line_items_data, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        # Alternating row shading
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        # Grid lines
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND_PRIMARY),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, BORDER_COLOR),
        ("LINEBELOW", (0, -1), (-1, -1), 1, BORDER_COLOR),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        # Alignment
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(items_table)

    # ─── TOTALS SECTION ────────────────────────────────────────────────────────
    story.append(Spacer(1, 4))

    subtotal = inv.amount_cents
    tax = inv.tax_cents
    total = inv.total_cents

    totals_data = [
        [
            Paragraph("", styles["body"]),
            Paragraph("<b>Subtotal</b>", styles["body_bold"]),
            Paragraph(_format_cents(subtotal, inv.currency), styles["table_cell_right"]),
        ],
    ]
    if tax > 0:
        totals_data.append([
            Paragraph("", styles["body"]),
            Paragraph("<b>Tax</b>", styles["body_bold"]),
            Paragraph(_format_cents(tax, inv.currency), styles["table_cell_right"]),
        ])
    totals_data.append([
        Paragraph("", styles["body"]),
        Paragraph("<b>Total</b>", ParagraphStyle(
            "TotalLabel", parent=styles["body_bold"], fontSize=11,
            textColor=BRAND_DARK,
        )),
        Paragraph(
            _format_cents(total, inv.currency),
            ParagraphStyle(
                "TotalValue", parent=styles["table_cell_bold_right"],
                fontSize=11, textColor=BRAND_DARK,
            ),
        ),
    ])

    totals_table = Table(totals_data, colWidths=[4.3 * inch, 1.5 * inch, 1.8 * inch])
    totals_table.setStyle(TableStyle([
        # Total row background
        ("BACKGROUND", (0, -1), (-1, -1), BRAND_LIGHT),
        # Top border for total
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, BRAND_PRIMARY),
        # Separator between subtotal/tax/total
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_COLOR),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(totals_table)

    # ─── PAYMENT DETAILS ───────────────────────────────────────────────────────
    story.append(Spacer(1, 20))

    payment_details = []
    if inv.payment_reference:
        payment_details.append(
            [Paragraph("<b>Payment Reference</b>", styles["body_muted"]),
             Paragraph(inv.payment_reference, styles["body"])]
        )

    # Credit period info
    if inv.credit_pool and inv.credit_pool.credit_periods:
        pool = inv.credit_pool
        billing_cycle = getattr(pool.plan, "billing_cycle", "monthly")
        period_label = "month" if billing_cycle == "monthly" else "year"
        payment_details.append(
            [Paragraph("<b>Credit Periods</b>", styles["body_muted"]),
             Paragraph(
                 f"{pool.credit_periods} {period_label}(s)",
                 styles["body"],
             )]
        )
        if pool.current_period_end:
            payment_details.append(
                [Paragraph("<b>Valid Until</b>", styles["body_muted"]),
                 Paragraph(
                     pool.current_period_end.strftime("%B %d, %Y"),
                     styles["body"],
                 )]
            )

    if payment_details:
        story.append(Paragraph("Payment Details", styles["section_heading"]))
        pay_table = Table(payment_details, colWidths=[1.8 * inch, 5.0 * inch])
        pay_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_COLOR),
        ]))
        story.append(pay_table)

    # ─── NOTES ─────────────────────────────────────────────────────────────────
    if inv.notes:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Notes", styles["section_heading"]))
        story.append(Paragraph(inv.notes, styles["body"]))

    # ─── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 50))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=BORDER_COLOR,
        spaceAfter=8, spaceBefore=0,
    ))

    footer_text = (
        f"Thank you for your business. This invoice was generated by {company_name}."
    )
    story.append(Paragraph(footer_text, styles["footer"]))

    if company_domain:
        story.append(Paragraph(
            f"{company_domain} | Support: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sattabase.com')}",
            styles["footer"],
        ))

    # Build the PDF
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()
