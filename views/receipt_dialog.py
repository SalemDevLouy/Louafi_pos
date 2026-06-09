import configparser
import os
import subprocess
import tempfile

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QSizePolicy
)

from utils.pdf import generate_receipt_pdf


def _cfg():
    cfg = configparser.RawConfigParser()
    cfg.read("config.ini")
    return cfg


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #e2e8f0; background: #e2e8f0; border:none; max-height:1px;")
    return line


def _label(text: str, bold=False, size=14, color="#1e293b", align=Qt.AlignLeft) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(align)
    lbl.setWordWrap(True)
    style = f"font-size:{size}px; color:{color}; background:transparent;"
    if bold:
        style += " font-weight:700;"
    lbl.setStyleSheet(style)
    return lbl


class ReceiptDialog(QDialog):
    def __init__(self, sale: dict, parent=None):
        super().__init__(parent)
        self._sale = sale
        self._cfg = _cfg()
        self.setWindowTitle(f"Receipt  —  Sale #{sale['id']}")
        self.setFixedWidth(480)
        self.setMinimumHeight(500)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Scrollable receipt body ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        body_widget = QWidget()
        body_widget.setStyleSheet("background:#ffffff;")
        body = QVBoxLayout(body_widget)
        body.setContentsMargins(32, 28, 32, 28)
        body.setSpacing(8)

        cfg = self._cfg
        store_name    = cfg.get("store", "name",     fallback="My Store")
        store_address = cfg.get("store", "address",  fallback="")
        store_phone   = cfg.get("store", "phone",    fallback="")
        header_text   = cfg.get("receipt", "header", fallback="")
        footer_text   = cfg.get("receipt", "footer", fallback="Thank you for your purchase!")
        currency      = cfg.get("store",   "currency", fallback="DZD")
        tax_rate      = cfg.getfloat("store", "tax_rate", fallback=0.19)
        logo_path     = cfg.get("store", "logo_path", fallback="assets/logo.png")

        # Logo
        pix = QPixmap(logo_path)
        if not pix.isNull():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_lbl.setAlignment(Qt.AlignCenter)
            logo_lbl.setStyleSheet("background:transparent;")
            body.addWidget(logo_lbl)

        # Store header
        body.addWidget(_label(store_name, bold=True, size=18, color="#0f172a", align=Qt.AlignCenter))
        if store_address:
            body.addWidget(_label(store_address, size=13, color="#64748b", align=Qt.AlignCenter))
        if store_phone:
            body.addWidget(_label(store_phone, size=13, color="#64748b", align=Qt.AlignCenter))
        if header_text:
            body.addWidget(_label(header_text, size=13, color="#64748b", align=Qt.AlignCenter))

        body.addSpacing(6)
        body.addWidget(_divider())
        body.addSpacing(6)

        # Sale info
        sale = self._sale
        body.addWidget(_label(f"Sale #:  {sale['id']}", size=13, color="#475569"))
        body.addWidget(_label(f"Date:     {str(sale.get('date', sale.get('created_at', '')))[:16]}", size=13, color="#475569"))
        cashier = sale.get("cashier_name", sale.get("cashier", ""))
        if cashier:
            body.addWidget(_label(f"Cashier: {cashier}", size=13, color="#475569"))

        body.addSpacing(8)
        body.addWidget(_divider())
        body.addSpacing(6)

        # Items header row
        items_hdr = QHBoxLayout()
        items_hdr.addWidget(_label("Product", bold=True, size=13, color="#64748b"))
        items_hdr.addStretch()
        for h in ("Qty", "Unit", "Total"):
            lbl = _label(h, bold=True, size=13, color="#64748b", align=Qt.AlignRight)
            lbl.setFixedWidth(70)
            items_hdr.addWidget(lbl)
        body.addLayout(items_hdr)

        body.addWidget(_divider())

        # Items
        items = sale.get("items", [])
        subtotal = 0.0
        for it in items:
            name     = it.get("product_name") or it.get("name", "")
            qty      = int(it.get("quantity", 1))
            price    = float(it.get("unit_price") or it.get("price", 0))
            line_tot = float(it.get("subtotal", price * qty))
            subtotal += line_tot

            row = QHBoxLayout()
            name_lbl = _label(name, size=14, color="#1e293b")
            name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            row.addWidget(name_lbl)

            for val in (str(qty), f"{price:.2f}", f"{line_tot:.2f}"):
                v = _label(val, size=14, color="#1e293b", align=Qt.AlignRight)
                v.setFixedWidth(70)
                row.addWidget(v)
            body.addLayout(row)

        body.addSpacing(4)
        body.addWidget(_divider())
        body.addSpacing(4)

        # Totals
        discount = float(sale.get("discount_value", 0))
        tax_amt  = float(sale.get("tax_amount", subtotal * tax_rate))
        total    = float(sale.get("total_amount") or sale.get("total", subtotal))
        paid     = float(sale.get("amount_paid", total))
        change   = float(sale.get("amount_change", paid - total))

        def totals_row(label, value, bold=False, color="#1e293b"):
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(_label(label, bold=bold, size=14, color="#64748b", align=Qt.AlignRight))
            v = _label(f"{value:,.2f} {currency}", bold=bold, size=14, color=color, align=Qt.AlignRight)
            v.setFixedWidth(130)
            row.addWidget(v)
            body.addLayout(row)

        totals_row("Subtotal", subtotal)
        if discount:
            totals_row("Discount", -discount, color="#ef4444")
        totals_row(f"Tax ({int(tax_rate*100)}%)", tax_amt, color="#64748b")
        body.addWidget(_divider())
        totals_row("TOTAL", total, bold=True, color="#6d28d9")
        totals_row("Paid", paid)
        totals_row("Change", change, color="#16a34a")

        # Loyalty
        earned   = sale.get("loyalty_earned")
        redeemed = sale.get("loyalty_redeemed")
        if earned or redeemed:
            body.addSpacing(6)
            body.addWidget(_divider())
            if earned:
                body.addWidget(_label(f"⭐  Points earned: {earned}", size=13, color="#6d28d9", align=Qt.AlignCenter))
            if redeemed:
                body.addWidget(_label(f"🎁  Points redeemed: {redeemed}", size=13, color="#0369a1", align=Qt.AlignCenter))

        # Footer
        body.addSpacing(10)
        body.addWidget(_divider())
        body.addSpacing(6)
        body.addWidget(_label(footer_text, size=13, color="#64748b", align=Qt.AlignCenter))

        body.addStretch()
        scroll.setWidget(body_widget)
        outer.addWidget(scroll, stretch=1)

        # ── Bottom action bar ──────────────────────────────────────────────────
        action_bar = QFrame()
        action_bar.setStyleSheet(
            "QFrame { background:#f8fafc; border-top:1px solid #e2e8f0; }"
        )
        ab = QHBoxLayout(action_bar)
        ab.setContentsMargins(20, 14, 20, 14)
        ab.setSpacing(10)

        save_btn = QPushButton("💾  Save PDF")
        save_btn.setObjectName("SecondaryButton")
        save_btn.setFixedHeight(42)
        save_btn.clicked.connect(self._save_pdf)

        print_btn = QPushButton("🖨  Print")
        print_btn.setObjectName("PrimaryButton")
        print_btn.setFixedHeight(42)
        print_btn.clicked.connect(self._print_pdf)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("SecondaryButton")
        close_btn.setFixedHeight(42)
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)

        ab.addWidget(save_btn)
        ab.addWidget(print_btn)
        ab.addStretch()
        ab.addWidget(close_btn)
        outer.addWidget(action_bar)

    def _build_pdf_data(self) -> tuple[dict, list]:
        """Convert sale dict to the format expected by generate_receipt_pdf."""
        sale = self._sale
        items = sale.get("items", [])
        pdf_items = []
        for it in items:
            price = float(it.get("unit_price") or it.get("price", 0))
            qty   = int(it.get("quantity", 1))
            pdf_items.append({
                "product_name": it.get("product_name") or it.get("name", ""),
                "quantity":     qty,
                "unit_price":   price,
                "subtotal":     float(it.get("subtotal", price * qty)),
            })

        cfg = self._cfg
        tax_rate = cfg.getfloat("store", "tax_rate", fallback=0.19)
        subtotal = sum(i["subtotal"] for i in pdf_items)

        pdf_sale = {
            "id":            sale["id"],
            "created_at":    str(sale.get("date", sale.get("created_at", ""))),
            "cashier_name":  sale.get("cashier_name", sale.get("cashier", "")),
            "total_amount":  float(sale.get("total_amount") or sale.get("total", subtotal)),
            "discount_value":float(sale.get("discount_value", 0)),
            "tax_amount":    float(sale.get("tax_amount", subtotal * tax_rate)),
            "amount_paid":   float(sale.get("amount_paid", sale.get("total", subtotal))),
            "amount_change": float(sale.get("amount_change", 0)),
            "loyalty_earned":   sale.get("loyalty_earned"),
            "loyalty_redeemed": sale.get("loyalty_redeemed"),
        }
        return pdf_sale, pdf_items

    def _generate_to(self, path: str) -> bool:
        pdf_sale, pdf_items = self._build_pdf_data()
        ok, msg = generate_receipt_pdf(pdf_sale, pdf_items, path)
        if not ok:
            QMessageBox.warning(self, "Error", f"Could not generate PDF:\n{msg}")
        return ok

    def _save_pdf(self):
        default = os.path.join(
            os.path.expanduser("~"),
            f"receipt_{self._sale['id']}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Receipt", default, "PDF Files (*.pdf)"
        )
        if not path:
            return
        if self._generate_to(path):
            QMessageBox.information(self, "Saved", f"Receipt saved to:\n{path}")

    def _print_pdf(self):
        # Generate to a temp file then open with system viewer / send to printer
        tmp = os.path.join(tempfile.gettempdir(), f"receipt_{self._sale['id']}.pdf")
        if not self._generate_to(tmp):
            return
        try:
            if os.name == "nt":
                os.startfile(tmp)
            else:
                subprocess.Popen(["xdg-open", tmp])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open PDF viewer:\n{e}")
