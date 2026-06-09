import configparser
import logging
import os
import traceback
from datetime import datetime

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
)

logger = logging.getLogger(__name__)

_FONT_REGISTERED = False


def _register_arabic_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    candidates = [
        "/usr/share/fonts/truetype/arabic/amiri/Amiri-Regular.ttf",
        "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf",
        os.path.join("assets", "Amiri-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("Arabic", path))
            _FONT_REGISTERED = True
            return
    _FONT_REGISTERED = False


def _ar(text: str) -> str:
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def _cfg():
    cfg = configparser.ConfigParser()
    cfg.read("config.ini")
    return cfg


def generate_receipt_pdf(sale: dict, items: list[dict], output_path: str) -> tuple[bool, str]:
    try:
        _register_arabic_font()
        cfg = _cfg()
        store_name = cfg.get("store", "name", fallback="POS Store")
        store_address = cfg.get("store", "address", fallback="")
        store_phone = cfg.get("store", "phone", fallback="")
        logo_path = cfg.get("store", "logo_path", fallback="assets/logo.png")
        currency = cfg.get("store", "currency", fallback="DZD")
        header_text = cfg.get("receipt", "header", fallback="")
        footer_text = cfg.get("receipt", "footer", fallback="Thank you!")
        tax_rate = cfg.getfloat("store", "tax_rate", fallback=0.19)

        font = "Arabic" if _FONT_REGISTERED else "Helvetica"

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )
        styles = getSampleStyleSheet()
        normal = ParagraphStyle("n", fontName=font, fontSize=10, leading=14)
        small = ParagraphStyle("s", fontName=font, fontSize=8, leading=11)
        bold = ParagraphStyle("b", fontName=font, fontSize=12, leading=16, spaceAfter=4)
        right = ParagraphStyle("r", fontName=font, fontSize=10, alignment=2)

        story = []

        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=40 * mm, height=20 * mm))
            story.append(Spacer(1, 4 * mm))

        story.append(Paragraph(_ar(store_name), bold))
        story.append(Paragraph(_ar(store_address), small))
        story.append(Paragraph(_ar(store_phone), small))
        if header_text:
            story.append(Paragraph(_ar(header_text % {"name": store_name}), small))
        story.append(HRFlowable(width="100%", thickness=0.5))
        story.append(Spacer(1, 3 * mm))

        story.append(Paragraph(f"#{sale['id']}  —  {sale.get('created_at','')[:16]}", small))
        story.append(Paragraph(_ar(f"Cashier: {sale.get('cashier_name', '')}"), small))
        story.append(Spacer(1, 3 * mm))

        col_widths = [70 * mm, 20 * mm, 25 * mm, 30 * mm]
        header_row = [_ar("Product"), _ar("Qty"), _ar("Unit"), _ar("Total")]
        table_data = [header_row]
        for it in items:
            table_data.append([
                _ar(it.get("product_name", "")),
                str(it.get("quantity", "")),
                f"{it.get('unit_price', 0):.2f} {currency}",
                f"{it.get('subtotal', 0):.2f} {currency}",
            ])
        tbl = Table(table_data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4 * mm))

        def totals_row(label, value):
            return [Paragraph(_ar(label), right),
                    Paragraph(f"{value:.2f} {currency}", normal)]

        totals_data = [
            totals_row("Subtotal", sale.get("total_amount", 0) + sale.get("discount_value", 0)),
        ]
        if sale.get("discount_value", 0):
            totals_data.append(totals_row("Discount", -sale["discount_value"]))
        if tax_rate:
            totals_data.append(totals_row(f"Tax ({int(tax_rate*100)}%)", sale.get("tax_amount", 0)))
        totals_data.append(totals_row("TOTAL", sale.get("total_amount", 0)))
        totals_data.append(totals_row("Paid", sale.get("amount_paid", 0)))
        totals_data.append(totals_row("Change", sale.get("amount_change", 0)))

        totals_tbl = Table(totals_data, colWidths=[100 * mm, 45 * mm])
        totals_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ("FONTSIZE", (0, -3), (-1, -3), 12),
        ]))
        story.append(totals_tbl)

        if sale.get("loyalty_earned") or sale.get("loyalty_redeemed"):
            story.append(Spacer(1, 3 * mm))
            if sale.get("loyalty_earned"):
                story.append(Paragraph(_ar(f"Points earned: {sale['loyalty_earned']}"), small))
            if sale.get("loyalty_redeemed"):
                story.append(Paragraph(_ar(f"Points redeemed: {sale['loyalty_redeemed']}"), small))

        story.append(Spacer(1, 5 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5))
        story.append(Paragraph(_ar(footer_text), small))

        doc.build(story)
        return True, output_path
    except Exception:
        logger.error("pdf.generate_receipt_pdf\n%s", traceback.format_exc())
        return False, "Failed to generate PDF receipt"


def generate_report_pdf(title: str, data: list[dict], output_path: str,
                        columns: list[str] | None = None) -> tuple[bool, str]:
    try:
        _register_arabic_font()
        cfg = _cfg()
        currency = cfg.get("store", "currency", fallback="DZD")
        font = "Arabic" if _FONT_REGISTERED else "Helvetica"

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=15 * mm, leftMargin=15 * mm,
                                topMargin=15 * mm, bottomMargin=15 * mm)
        styles = getSampleStyleSheet()
        bold = ParagraphStyle("b", fontName=font, fontSize=14, spaceAfter=6)

        if not data:
            return False, "No data to export"
        keys = columns or list(data[0].keys())
        header = [_ar(k.replace("_", " ").title()) for k in keys]
        rows = [header]
        for row in data:
            rows.append([_ar(str(row.get(k, ""))) for k in keys])

        col_w = (A4[0] - 30 * mm) / len(keys)
        tbl = Table(rows, colWidths=[col_w] * len(keys))
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        story = [
            Paragraph(_ar(title), bold),
            Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), styles["Normal"]),
            Spacer(1, 5 * mm),
            tbl,
        ]
        doc.build(story)
        return True, output_path
    except Exception:
        logger.error("pdf.generate_report_pdf\n%s", traceback.format_exc())
        return False, "Failed to generate report PDF"
