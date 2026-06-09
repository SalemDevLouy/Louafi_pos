import logging
from datetime import date

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QDateEdit, QDialog,
    QFormLayout, QMessageBox, QHeaderView,
    QDoubleSpinBox, QCheckBox, QFrame, QSizePolicy, QSpacerItem
)

from controllers import discount_controller
from utils.auth import current_user_id, require_role
from utils.lang import tr

logger = logging.getLogger(__name__)


class DiscountDialog(QDialog):
    def __init__(self, discount: dict | None = None, parent=None):
        super().__init__(parent)
        self.discount = discount
        self.setWindowTitle(tr("edit_discount") if discount else tr("new_discount"))
        self.setFixedWidth(460)

        outer = QVBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QLabel(tr("edit_discount") if discount else tr("new_discount"))
        header.setObjectName("section_title")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Discount name...")
        self.dtype = QComboBox()
        self.dtype.addItems([tr("percentage"), tr("fixed"), tr("coupon")])
        self.dtype.currentIndexChanged.connect(self._toggle_coupon)
        self.value = QDoubleSpinBox()
        self.value.setRange(0, 100_000)
        self.value.setDecimals(2)
        self.coupon_code = QLineEdit()
        self.coupon_code.setPlaceholderText("Optional coupon code")
        self.min_purchase = QDoubleSpinBox()
        self.min_purchase.setRange(0, 1_000_000)
        self.min_purchase.setDecimals(2)
        self.min_purchase.setPrefix("DA ")
        self.is_active = QCheckBox(tr("active"))
        self.is_active.setChecked(True)
        self.valid_from = QDateEdit(QDate.currentDate())
        self.valid_from.setCalendarPopup(True)
        self.valid_to = QDateEdit(QDate.currentDate().addYears(1))
        self.valid_to.setCalendarPopup(True)

        if discount:
            self.name.setText(discount.get("name", ""))
            type_map = {"percentage": 0, "fixed": 1, "coupon": 2}
            self.dtype.setCurrentIndex(type_map.get(discount.get("type", "percentage"), 0))
            self.value.setValue(float(discount.get("value", 0)))
            self.coupon_code.setText(discount.get("coupon_code") or "")
            self.min_purchase.setValue(float(discount.get("min_purchase") or 0))
            self.is_active.setChecked(bool(discount.get("is_active", True)))
            if discount.get("valid_from"):
                self.valid_from.setDate(QDate.fromString(discount["valid_from"][:10], "yyyy-MM-dd"))
            if discount.get("valid_to"):
                self.valid_to.setDate(QDate.fromString(discount["valid_to"][:10], "yyyy-MM-dd"))

        form.addRow(tr("discount_name"), self.name)
        form.addRow(tr("discount_type"), self.dtype)
        form.addRow(tr("value"), self.value)
        form.addRow(tr("coupon_code"), self.coupon_code)
        form.addRow(tr("min_purchase"), self.min_purchase)
        form.addRow(tr("valid_from"), self.valid_from)
        form.addRow(tr("valid_to"), self.valid_to)
        form.addRow("", self.is_active)
        outer.addLayout(form)

        outer.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(tr("save"))
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)
        self._toggle_coupon()

    def _toggle_coupon(self):
        is_coupon = self.dtype.currentIndex() == 2
        self.coupon_code.setEnabled(is_coupon)

    def get_data(self) -> dict:
        type_vals = ["percentage", "fixed", "coupon"]
        return {
            "name": self.name.text().strip(),
            "type": type_vals[self.dtype.currentIndex()],
            "value": self.value.value(),
            "coupon_code": self.coupon_code.text().strip() or None,
            "min_purchase": self.min_purchase.value() or None,
            "is_active": self.is_active.isChecked(),
            "valid_from": self.valid_from.date().toString("yyyy-MM-dd"),
            "valid_to": self.valid_to.date().toString("yyyy-MM-dd"),
        }


class DiscountsView(QWidget):
    def __init__(self):
        super().__init__()
        self._data: list[dict] = []
        self._build_ui()
        self.load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Page header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        page_title = QLabel(tr("discounts"))
        page_title.setObjectName("page_title")
        subtitle = QLabel(tr("discounts_subtitle"))
        subtitle.setObjectName("sub_title")
        title_col.addWidget(page_title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()
        add_btn = QPushButton("＋  " + tr("add"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._add)
        header_row.addWidget(add_btn)
        root.addLayout(header_row)

        # Filter toolbar
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; }"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        self.active_only = QCheckBox(tr("active_only"))
        self.active_only.setChecked(False)
        self.active_only.toggled.connect(self.load)
        fl.addWidget(self.active_only)
        fl.addStretch()

        refresh_btn = QPushButton(tr("refresh"))
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(self.load)
        fl.addWidget(refresh_btn)
        root.addWidget(filter_frame)

        # Table card
        table_card = QFrame()
        table_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }"
        )
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#", tr("discount_name"), tr("discount_type"),
            tr("value"), tr("coupon_code"), tr("min_purchase"),
            tr("valid_to"), tr("status")
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._edit)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        table_layout.addWidget(self.table)
        root.addWidget(table_card, stretch=1)

        # Bottom action bar
        btns = QHBoxLayout()
        btns.addStretch()
        edit_btn = QPushButton(tr("edit"))
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.setFixedHeight(36)
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton(tr("delete"))
        del_btn.setObjectName("DangerButton")
        del_btn.setFixedHeight(36)
        del_btn.clicked.connect(self._delete)
        btns.addWidget(edit_btn)
        btns.addWidget(del_btn)
        root.addLayout(btns)

    def load(self):
        active_only = self.active_only.isChecked()
        ok, data = discount_controller.get_all(active_only=active_only)
        if not ok:
            QMessageBox.warning(self, tr("error"), data)
            return
        self._data = data
        self.table.setRowCount(0)
        for row in data:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 44)

            self._cell(r, 0, str(row["id"]), Qt.AlignCenter)
            self._cell(r, 1, row.get("name", ""))
            self._cell(r, 2, row.get("type", "").capitalize(), Qt.AlignCenter)

            val = float(row.get("value", 0))
            suffix = "%" if row.get("type") == "percentage" else " DA"
            val_item = QTableWidgetItem(f"{val:,.2f}{suffix}")
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_item.setForeground(QColor("#6d28d9"))
            self.table.setItem(r, 3, val_item)

            self._cell(r, 4, row.get("coupon_code") or "—", Qt.AlignCenter)
            mp = row.get("min_purchase")
            self._cell(r, 5, f"{float(mp):,.0f} DA" if mp else "—", Qt.AlignCenter)
            self._cell(r, 6, str(row.get("valid_to") or "—"), Qt.AlignCenter)

            is_active = bool(row.get("is_active"))
            status_text = tr("active") if is_active else tr("inactive")
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor("#16a34a") if is_active else QColor("#dc2626"))
            self.table.setItem(r, 7, status_item)

    def _cell(self, row: int, col: int, text: str, align=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        self.table.setItem(row, col, item)

    def _selected(self) -> dict | None:
        r = self.table.currentRow()
        return self._data[r] if 0 <= r < len(self._data) else None

    def _add(self):
        dlg = DiscountDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.get_data()
        ok, msg = discount_controller.create(
            current_user_id(), d["name"], d["type"], d["value"],
            d["coupon_code"], d["min_purchase"], d["valid_from"], d["valid_to"]
        )
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _edit(self):
        row = self._selected()
        if not row:
            return
        dlg = DiscountDialog(discount=row, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.get_data()
        ok, msg = discount_controller.update(
            current_user_id(), row["id"], d["name"], d["type"], d["value"],
            d["coupon_code"], d["min_purchase"], d["is_active"], d["valid_from"], d["valid_to"]
        )
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _delete(self):
        row = self._selected()
        if not row:
            return
        if not require_role("admin"):
            QMessageBox.warning(self, tr("error"), tr("admin_only"))
            return
        reply = QMessageBox.question(self, tr("confirm_action"), tr("confirm_delete"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ok, msg = discount_controller.delete(current_user_id(), row["id"])
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)
