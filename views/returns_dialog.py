"""Returns & Refunds dialog.

Opened from the main POS screen.  Lets the user find a past invoice, pick the
lines to return and the quantities, enter an optional reason, then records the
return (restocking the products automatically).
"""
import configparser

import qtawesome as qta
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSpinBox, QFrame, QMessageBox,
)

from controllers.returns_controller import ReturnsController
from utils.lang import tr
from utils.auth import current_user_id

_BLUE   = '#1a73e8'
_RED    = '#dc2626'
_SLATE  = '#475569'
_DARK   = '#0f172a'


def _currency() -> str:
    cfg = configparser.RawConfigParser()
    cfg.read('config.ini')
    return cfg.get('store', 'currency', fallback='DZD')


def _status_text(status: str, refunded: float) -> str:
    if status == 'returned':
        return tr('ret_fully_returned')
    if refunded and refunded > 0:
        return tr('st_partial')
    return tr('st_completed')


class ReturnDialog(QDialog):
    def __init__(self, controller: ReturnsController | None = None, parent=None):
        super().__init__(parent)
        self.rc = controller or ReturnsController()
        self._selected_sale_id: int | None = None
        self._sale_header: dict | None = None
        self._spin_rows: list = []   # (sale_item_id, QSpinBox, unit_price)

        self.setWindowTitle(tr('ret_title'))
        self.setMinimumSize(920, 660)
        self.resize(980, 700)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # ── Search row ────────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr('ret_search_ph'))
        self.search_edit.setFixedHeight(40)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.returnPressed.connect(self._search)
        search_row.addWidget(self.search_edit, 1)

        self.btn_search = QPushButton(f"  {tr('search')}")
        self.btn_search.setIcon(qta.icon('fa5s.search', color='#fff'))
        self.btn_search.setIconSize(QSize(16, 16))
        self.btn_search.setFixedHeight(40)
        self.btn_search.setStyleSheet(
            f"QPushButton {{ background:{_BLUE}; color:#fff; border-radius:8px;"
            " padding:0 18px; font-size:14px; font-weight:600; }"
            "QPushButton:hover { background:#1558b0; }"
        )
        self.btn_search.clicked.connect(self._search)
        search_row.addWidget(self.btn_search)
        root.addLayout(search_row)

        # ── Sales results table ───────────────────────────────────────────────
        self.results_table = QTableWidget(0, 7)
        self.results_table.setHorizontalHeaderLabels([
            tr('col_invoice'), tr('col_date'), tr('col_customer'),
            tr('col_payment'), tr('col_total'), tr('ret_refunded_total'), tr('col_status'),
        ])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setShowGrid(False)
        self.results_table.setMaximumHeight(220)
        hh = self.results_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.itemSelectionChanged.connect(self._on_sale_selected)
        root.addWidget(self.results_table)

        # ── Detail panel ──────────────────────────────────────────────────────
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0;"
            " border-radius:12px; }"
        )
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(14, 12, 14, 12)
        pl.setSpacing(10)

        # selected-sale header line
        self.detail_header = QLabel(tr('ret_select_sale'))
        self.detail_header.setStyleSheet(
            f"color:{_DARK}; font-size:14px; font-weight:700; background:transparent;"
        )
        pl.addWidget(self.detail_header)

        # items table
        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels([
            tr('col_product'), tr('col_barcode'), tr('col_sold'),
            tr('col_returned'), tr('col_return_qty'), tr('col_unit_price'),
            tr('col_refund'),
        ])
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setShowGrid(False)
        ihh = self.items_table.horizontalHeader()
        ihh.setSectionResizeMode(0, QHeaderView.Stretch)
        ihh.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.items_table.setMinimumHeight(180)
        pl.addWidget(self.items_table, 1)

        # reason
        reason_row = QHBoxLayout()
        reason_row.setSpacing(8)
        reason_lbl = QLabel(tr('ret_reason'))
        reason_lbl.setStyleSheet(f"color:{_SLATE}; font-size:13px; background:transparent;")
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText(tr('ret_reason_ph'))
        self.reason_edit.setFixedHeight(36)
        reason_row.addWidget(reason_lbl)
        reason_row.addWidget(self.reason_edit, 1)
        pl.addLayout(reason_row)

        # refund total + buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.refund_total_lbl = QLabel(f"{tr('ret_total_refund')}:  0.00 {_currency()}")
        self.refund_total_lbl.setStyleSheet(
            f"color:{_RED}; font-size:20px; font-weight:800; background:transparent;"
        )
        action_row.addWidget(self.refund_total_lbl)
        action_row.addStretch()

        self.btn_cancel = QPushButton(tr('cancel'))
        self.btn_cancel.setFixedHeight(42)
        self.btn_cancel.setStyleSheet(
            "QPushButton { background:#e2e8f0; color:#334155; border-radius:8px;"
            " padding:0 22px; font-size:14px; font-weight:600; }"
            "QPushButton:hover { background:#cbd5e1; }"
        )
        self.btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton(f"  {tr('ret_confirm')}")
        self.btn_confirm.setIcon(qta.icon('fa5s.undo-alt', color='#fff'))
        self.btn_confirm.setFixedHeight(42)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setStyleSheet(
            f"QPushButton {{ background:{_RED}; color:#fff; border-radius:8px;"
            " padding:0 22px; font-size:14px; font-weight:700; }"
            "QPushButton:hover { background:#b91c1c; }"
            "QPushButton:disabled { background:#fca5a5; color:#fee2e2; }"
        )
        self.btn_confirm.clicked.connect(self._confirm)
        action_row.addWidget(self.btn_confirm)
        pl.addLayout(action_row)

        root.addWidget(panel, 1)

        self._search()

    # ── helpers ────────────────────────────────────────────────────────────────

    def _search(self):
        term = self.search_edit.text().strip()
        try:
            rows = self.rc.search_sales(term)
        except Exception as exc:
            QMessageBox.warning(self, tr('warning'), str(exc))
            return

        # A fresh search invalidates whatever sale was being inspected.
        self._selected_sale_id = None
        self._sale_header = None
        self._spin_rows = []
        self.items_table.setRowCount(0)
        self.btn_confirm.setEnabled(False)
        self.refund_total_lbl.setText(
            f"{tr('ret_total_refund')}:  0.00 {_currency()}"
        )

        self.results_table.setRowCount(0)
        cur = _currency()
        for s in rows:
            r = self.results_table.rowCount()
            self.results_table.insertRow(r)
            self.results_table.setRowHeight(r, 38)
            vals = [
                f"#{s['id']}",
                str(s.get('created_at', ''))[:16],
                s.get('customer_name', '—'),
                s.get('payment_method', '—'),
                f"{float(s.get('total_effective', 0)):,.2f} {cur}",
                f"{float(s.get('refunded', 0)):,.2f}",
                _status_text(s.get('status', ''), float(s.get('refunded', 0))),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setData(Qt.UserRole, s['id'])
                if c >= 4:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(r, c, item)
        if not rows:
            self.detail_header.setText(tr('ret_no_results'))
        else:
            self.detail_header.setText(tr('ret_select_sale'))

    def _on_sale_selected(self):
        rows = self.results_table.selectedItems()
        if not rows:
            return
        sale_id = rows[0].data(Qt.UserRole)
        if sale_id == self._selected_sale_id:
            return
        self._selected_sale_id = sale_id
        try:
            self._sale_header = self.rc.get_sale_detail(sale_id)
        except Exception as exc:
            QMessageBox.warning(self, tr('warning'), str(exc))
            return
        self._load_items()

    def _load_items(self):
        hdr = self._sale_header or {}
        self.detail_header.setText(
            f"Sale #{hdr.get('id', '')}   ·   {hdr.get('customer_name', '—')}"
            f"   ·   {str(hdr.get('created_at', ''))[:16]}"
            f"   ·   {hdr.get('payment_method', '—')}"
        )

        self.items_table.setRowCount(0)
        self._spin_rows = []
        cur = _currency()
        any_returnable = False
        for it in hdr.get('items', []):
            remaining = int(it.get('qty_sold', 0)) - int(it.get('qty_returned', 0))
            any_returnable = any_returnable or remaining > 0
            r = self.items_table.rowCount()
            self.items_table.insertRow(r)
            self.items_table.setRowHeight(r, 42)

            name_item = QTableWidgetItem(it.get('product_name', '—'))
            name_item.setData(Qt.UserRole, it.get('sale_item_id'))
            self.items_table.setItem(r, 0, name_item)
            self.items_table.setItem(r, 1, QTableWidgetItem(it.get('barcode') or '—'))

            for c, val in ((2, it.get('qty_sold')), (3, it.get('qty_returned'))):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.items_table.setItem(r, c, item)

            spin = QSpinBox()
            spin.setRange(0, max(remaining, 0))
            spin.setEnabled(remaining > 0)
            spin.setAlignment(Qt.AlignCenter)
            spin.setStyleSheet('QSpinBox { padding: 2px 4px; }')
            spin.valueChanged.connect(lambda _v: self._recalc())
            self.items_table.setCellWidget(r, 4, spin)
            self._spin_rows.append((it.get('sale_item_id'), spin,
                                    float(it.get('unit_price', 0))))

            price_item = QTableWidgetItem(f"{float(it.get('unit_price', 0)):,.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(r, 5, price_item)

            refund_item = QTableWidgetItem(f"0.00 {cur}")
            refund_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(r, 6, refund_item)

        if not any_returnable:
            QMessageBox.information(self, tr('ret_title'), tr('ret_no_items'))
        self._recalc()

    def _recalc(self):
        cur = _currency()
        total = 0.0
        for sale_item_id, spin, unit_price in self._spin_rows:
            qty = spin.value()
            # find row index to update the Refund cell
            for row in range(self.items_table.rowCount()):
                if self.items_table.item(row, 0).data(Qt.UserRole) == sale_item_id:
                    cell = self.items_table.item(row, 6)
                    if cell is None:
                        cell = QTableWidgetItem('')
                        self.items_table.setItem(row, 6, cell)
                    if qty > 0:
                        cell.setText(f"{qty * unit_price:,.2f} {cur}")
                    else:
                        cell.setText(f"0.00 {cur}")
                    break
            total += qty * unit_price
        self.refund_total_lbl.setText(
            f"{tr('ret_total_refund')}:  {total:,.2f} {cur}"
        )
        has_items = any(spin.value() > 0 for _sid, spin, _up in self._spin_rows)
        self.btn_confirm.setEnabled(has_items)

    def _confirm(self):
        items = [(sid, spin.value()) for sid, spin, _up in self._spin_rows
                 if spin.value() > 0]
        if not items:
            QMessageBox.warning(self, tr('warning'), tr('ret_no_items'))
            return
        if self._selected_sale_id is None:
            QMessageBox.warning(self, tr('warning'), tr('ret_select_sale'))
            return

        reason = self.reason_edit.text().strip()
        try:
            ret = self.rc.create_return(
                self._selected_sale_id, reason, items,
                actor_id=current_user_id(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, tr('warning'), str(exc))
            return
        except Exception as exc:
            QMessageBox.warning(self, tr('warning'), str(exc))
            return

        cur = _currency()
        QMessageBox.information(
            self,
            tr('ret_success_title'),
            tr('ret_success_msg').format(
                id=ret['id'], amount=f"{ret['total_refund']:,.2f}", cur=cur,
            ),
        )
        self.accept()
