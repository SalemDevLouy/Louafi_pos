import logging
from datetime import date

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QDateEdit, QDialog,
    QFormLayout, QMessageBox, QHeaderView, QDoubleSpinBox,
    QFrame, QSizePolicy, QSpacerItem
)

from controllers import expense_controller
from utils.auth import current_user_id, require_role
from utils.lang import tr

logger = logging.getLogger(__name__)


class ExpenseDialog(QDialog):
    def __init__(self, expense: dict | None = None, parent=None):
        super().__init__(parent)
        self.expense = expense
        self.setWindowTitle(tr("edit_expense") if expense else tr("new_expense"))
        self.setFixedWidth(440)

        outer = QVBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QLabel(tr("edit_expense") if expense else tr("new_expense"))
        header.setObjectName("section_title")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        existing_cats = expense_controller.get_categories()
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(existing_cats or [
            "Loyer", "Électricité", "Eau", "Internet",
            "Salaires", "Transport", "Fournitures", "Autre"
        ])
        self.description = QLineEdit()
        self.description.setPlaceholderText("Brief description...")
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1_000_000_000)
        self.amount.setDecimals(2)
        self.amount.setPrefix("DA ")
        self.paid_by = QLineEdit()
        self.paid_by.setPlaceholderText("Who paid...")

        if expense:
            self.category.setCurrentText(expense.get("category", ""))
            self.description.setText(expense.get("description", ""))
            self.amount.setValue(float(expense.get("amount", 0)))
            self.paid_by.setText(expense.get("paid_by", ""))

        form.addRow(tr("expense_category"), self.category)
        form.addRow(tr("description"), self.description)
        form.addRow(tr("amount"), self.amount)
        form.addRow(tr("paid_by"), self.paid_by)
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

    def get_data(self) -> dict:
        return {
            "category": self.category.currentText().strip(),
            "description": self.description.text().strip(),
            "amount": self.amount.value(),
            "paid_by": self.paid_by.text().strip(),
        }


class ExpensesView(QWidget):
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
        page_title = QLabel(tr("expenses"))
        page_title.setObjectName("page_title")
        subtitle = QLabel(tr("expenses_subtitle"))
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
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        filter_layout.addWidget(self._lbl(tr("date_from")))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setFixedWidth(140)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(self._lbl(tr("date_to")))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setFixedWidth(140)
        filter_layout.addWidget(self.date_to)

        filter_layout.addWidget(self._lbl(tr("expense_category")))
        self.cat_filter = QComboBox()
        self.cat_filter.addItem(tr("all"), None)
        self.cat_filter.setFixedWidth(160)
        filter_layout.addWidget(self.cat_filter)

        filter_layout.addStretch()
        filter_btn = QPushButton(tr("filter"))
        filter_btn.setObjectName("SecondaryButton")
        filter_btn.setFixedHeight(36)
        filter_btn.setFixedWidth(90)
        filter_btn.clicked.connect(self.load)
        filter_layout.addWidget(filter_btn)
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "#", tr("expense_category"), tr("description"),
            tr("amount") + " (DA)", tr("paid_by"), tr("col_date")
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._edit)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        table_layout.addWidget(self.table)
        root.addWidget(table_card, stretch=1)

        # Bottom bar
        bottom = QHBoxLayout()
        self.total_label = QLabel()
        self.total_label.setObjectName("section_title")
        bottom.addWidget(self.total_label)
        bottom.addStretch()
        edit_btn = QPushButton(tr("edit"))
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.setFixedHeight(36)
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton(tr("delete"))
        del_btn.setObjectName("DangerButton")
        del_btn.setFixedHeight(36)
        del_btn.clicked.connect(self._delete)
        bottom.addWidget(edit_btn)
        bottom.addWidget(del_btn)
        root.addLayout(bottom)

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size:13px; color:#64748b; font-weight:500; background:transparent; border:none;"
        )
        return lbl

    def load(self):
        filters = {
            "date_from": self.date_from.date().toString("yyyy-MM-dd"),
            "date_to": self.date_to.date().toString("yyyy-MM-dd"),
        }
        cat = self.cat_filter.currentData()
        if cat:
            filters["category"] = cat

        ok, data = expense_controller.get_all(filters)
        if not ok:
            QMessageBox.warning(self, tr("error"), data)
            return

        self._refresh_cat_filter()
        self.table.setRowCount(0)
        total = 0.0
        for row in data:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 44)
            self._cell(r, 0, str(row["id"]), Qt.AlignCenter)
            self._cell(r, 1, row.get("category", ""))
            self._cell(r, 2, row.get("description", ""))
            amt = float(row.get("amount", 0))
            amount_item = QTableWidgetItem(f"{amt:,.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount_item.setForeground(QColor("#ef4444"))
            self.table.setItem(r, 3, amount_item)
            self._cell(r, 4, row.get("paid_by", ""))
            self._cell(r, 5, str(row.get("created_at", ""))[:10], Qt.AlignCenter)
            total += amt

        self.total_label.setText(tr("total") + f":  {total:,.2f} DA")
        self._data = data

    def _cell(self, row: int, col: int, text: str, align=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        self.table.setItem(row, col, item)

    def _refresh_cat_filter(self):
        current = self.cat_filter.currentText()
        self.cat_filter.clear()
        self.cat_filter.addItem(tr("all"), None)
        for cat in expense_controller.get_categories():
            self.cat_filter.addItem(cat, cat)
        idx = self.cat_filter.findText(current)
        if idx >= 0:
            self.cat_filter.setCurrentIndex(idx)

    def _selected_row(self) -> dict | None:
        r = self.table.currentRow()
        return self._data[r] if 0 <= r < len(self._data) else None

    def _add(self):
        dlg = ExpenseDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.get_data()
        ok, msg = expense_controller.create(
            current_user_id(), d["category"], d["description"], d["amount"], d["paid_by"]
        )
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _edit(self):
        row = self._selected_row()
        if not row:
            return
        dlg = ExpenseDialog(expense=row, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.get_data()
        ok, msg = expense_controller.update(
            current_user_id(), row["id"],
            d["category"], d["description"], d["amount"], d["paid_by"]
        )
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _delete(self):
        row = self._selected_row()
        if not row:
            return
        if not require_role("admin", "supervisor"):
            QMessageBox.warning(self, tr("error"), tr("insuf_perms"))
            return
        reply = QMessageBox.question(self, tr("confirm_action"), tr("confirm_delete"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ok, msg = expense_controller.delete(current_user_id(), row["id"])
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)
