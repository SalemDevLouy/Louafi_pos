from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox, QSplitter, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QSize
from controllers.customer_controller import CustomerController
import utils.icons as ic
from utils.lang import lang_manager, tr


class _CustomerDialog(QDialog):
    """Add / Edit customer dialog."""
    def __init__(self, customer=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Edit Customer' if customer else 'New Customer')
        self.setMinimumWidth(380)

        layout = QFormLayout(self)
        layout.setSpacing(14)

        self.name_edit = QLineEdit(customer.name if customer else '')
        self.phone_edit = QLineEdit(customer.phone if customer else '')
        self.address_edit = QLineEdit(customer.address if customer else '')

        layout.addRow('Name *:', self.name_edit)
        layout.addRow('Phone:', self.phone_edit)
        layout.addRow('Address:', self.address_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, 'Validation', 'Name is required.')
            return
        self.accept()

    def values(self):
        return (
            self.name_edit.text().strip(),
            self.phone_edit.text().strip(),
            self.address_edit.text().strip(),
        )


class _DebtDialog(QDialog):
    """Add debt / record payment dialog."""
    def __init__(self, title: str, customer_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'{title} — {customer_name}')
        self.setMinimumWidth(340)

        layout = QFormLayout(self)
        layout.setSpacing(14)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0.01, 9_999_999)
        self.amount.setDecimals(2)
        self.amount.setSingleStep(1.0)
        layout.addRow('Amount:', self.amount)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText('Optional note…')
        layout.addRow('Note:', self.note_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def values(self):
        return self.amount.value(), self.note_edit.text().strip()


class CustomersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cc = CustomerController()
        self._selected_customer = None
        self._build_ui()
        self.refresh_customers()
        lang_manager.lang_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, lang=None):
        # page title
        self.title_txt.setText(tr('page_customers'))
        # cards
        custs = getattr(self, '_customers', [])
        total = len(custs)
        total_debt = sum(getattr(c, 'debt', 0) or 0 for c in custs)
        self.card_total.setText(f'{tr("total_customers")}\n {total}')
        self.card_debt.setText(f'{tr("total_outstanding")}\n {total_debt:,.2f}')
        # search
        self.search_box.setPlaceholderText(tr('search_cust'))
        # buttons
        self.btn_add_cust.setText(tr('btn_add'))
        self.btn_edit.setText(tr('btn_edit'))
        self.btn_del.setText(tr('btn_delete'))
        self.btn_add_debt.setText(tr('btn_add_debt'))
        self.btn_pay_debt.setText(tr('btn_record_payment'))
        # table headers
        self.cust_table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_phone'), tr('col_debt')
        ])
        self.debt_table.setHorizontalHeaderLabels([
            tr('col_date'), tr('col_debt'), tr('col_note'), tr('col_balance')
        ])

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6,6,6,6)
        root.setSpacing(14)

        # ── Title ─────────────────────────────────────────────────────────────
        title = QLabel(' Customers')
        title.setObjectName('page_title')
        title.setIcon = None   # not a button — set pixmap inline
        title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # icon + text in one label using pixmap on the left via rich-text is not
        # possible cleanly; use a helper HBox row instead
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setPixmap(ic.ic_page_customers().pixmap(ic.LG))
        ic_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        title_txt = QLabel(tr('page_customers'))
        title_txt.setObjectName('page_title')
        title_txt.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.title_txt = title_txt
        title_row.addWidget(ic_lbl)
        title_row.addWidget(title_txt)
        title_row.addStretch()
        root.addLayout(title_row)

        # ── Main splitter ─────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)

        # summary cards (top of the page)
        cards_row = QHBoxLayout()
        self.card_total = QLabel(f'{tr("total_customers")}\n—')
        self.card_total.setObjectName('summary_card')
        self.card_total.setAlignment(Qt.AlignCenter)
        self.card_total.setFixedHeight(84)
        self.card_debt = QLabel(f'{tr("total_outstanding")}\n—')
        self.card_debt.setObjectName('summary_card')
        self.card_debt.setAlignment(Qt.AlignCenter)
        self.card_debt.setFixedHeight(84)
        cards_row.addWidget(self.card_total)
        cards_row.addWidget(self.card_debt)
        root.addLayout(cards_row)

        # ── LEFT: customer list ───────────────────────────────────────────────
        left = QFrame()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(8)

        # toolbar with search + actions
        toolbar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr('search_cust'))
        self.search_box.addAction(ic.ic_search(), QLineEdit.LeadingPosition)
        self.search_box.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_box, 1)

        self.btn_add_cust = QPushButton(tr('btn_add'))
        self.btn_add_cust.setIcon(ic.ic_add())
        self.btn_add_cust.setIconSize(ic.SM)
        self.btn_add_cust.setObjectName('action_btn')
        self.btn_add_cust.clicked.connect(self._add_customer)
        self.btn_edit = QPushButton(tr('btn_edit'))
        self.btn_edit.setIcon(ic.ic_edit())
        self.btn_edit.setIconSize(ic.SM)
        self.btn_edit.setObjectName('action_btn')
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._edit_customer)
        self.btn_del = QPushButton(tr('btn_delete'))
        self.btn_del.setIcon(ic.ic_delete())
        self.btn_del.setIconSize(ic.SM)
        self.btn_del.setStyleSheet(
            'QPushButton { background:#e53935; color:white; border-radius:8px; padding:6px 14px; }'
            'QPushButton:hover { background:#b71c1c; }'
            'QPushButton:disabled { background:#ccc; }'
        )
        self.btn_del.clicked.connect(self._delete_customer)

        toolbar.addWidget(self.btn_add_cust)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_del)
        left_lay.addLayout(toolbar)

        # table
        self.cust_table = QTableWidget()
        self.cust_table.setColumnCount(4)
        self.cust_table.setHorizontalHeaderLabels([tr('col_id'), tr('col_name'), tr('col_phone'), tr('col_debt')])
        self.cust_table.verticalHeader().setVisible(False)
        self.cust_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cust_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cust_table.setAlternatingRowColors(True)
        self.cust_table.itemSelectionChanged.connect(self._on_customer_selected)

        hh = self.cust_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setStyleSheet(
            'QHeaderView::section { background:#1a73e8; color:white; padding:6px; font-weight:600; }'
        )
        left_lay.addWidget(self.cust_table)

        splitter.addWidget(left)

        # ── RIGHT: selected customer info + debt history ─────────────────────
        right = QFrame()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 0, 0, 0)
        right_lay.setSpacing(10)

        # selected-customer quick info
        self.customer_info = QLabel('No customer selected')
        self.customer_info.setObjectName('sub_title')
        self.customer_info.setStyleSheet('')
        right_lay.addWidget(self.customer_info)

        self.debt_title = QLabel('Debt History')
        self.debt_title.setObjectName('section_title')
        self.debt_title.setStyleSheet('')
        right_lay.addWidget(self.debt_title)

        self.debt_table = QTableWidget()
        self.debt_table.setColumnCount(4)
        self.debt_table.setHorizontalHeaderLabels([tr('col_date'), tr('col_debt'), tr('col_note'), tr('col_balance')])
        self.debt_table.verticalHeader().setVisible(False)
        self.debt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.debt_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.debt_table.setAlternatingRowColors(True)

        dhh = self.debt_table.horizontalHeader()
        dhh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        dhh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        dhh.setSectionResizeMode(2, QHeaderView.Stretch)
        dhh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        dhh.setDefaultAlignment(Qt.AlignCenter)
        dhh.setStyleSheet(
            'QHeaderView::section { background:#1a73e8; color:white; padding:6px; font-weight:600; }'
        )
        right_lay.addWidget(self.debt_table)

        # debt action buttons
        debt_btns = QHBoxLayout()
        self.btn_add_debt = QPushButton(tr('btn_add_debt'))
        self.btn_add_debt.setIcon(ic.ic_credit())
        self.btn_add_debt.setIconSize(ic.SM)
        self.btn_add_debt.setObjectName('action_btn')
        self.btn_add_debt.setEnabled(False)
        self.btn_add_debt.clicked.connect(self._add_debt)

        self.btn_pay_debt = QPushButton(tr('btn_record_payment'))
        self.btn_pay_debt.setIcon(ic.ic_payment())
        self.btn_pay_debt.setIconSize(ic.SM)
        self.btn_pay_debt.setObjectName('action_btn')
        self.btn_pay_debt.setEnabled(False)
        self.btn_pay_debt.clicked.connect(self._pay_debt)

        debt_btns.addWidget(self.btn_add_debt)
        debt_btns.addWidget(self.btn_pay_debt)
        debt_btns.addStretch()
        right_lay.addLayout(debt_btns)

        splitter.addWidget(right)
        splitter.setSizes([420, 580])

        root.addWidget(splitter)

    # ── Customer list ─────────────────────────────────────────────────────────

    def refresh_customers(self):
        term = self.search_box.text().strip()
        customers = self.cc.search(term) if term else self.cc.get_all()
        self._populate_customers(customers)
        # update summary cards
        total = len(customers)
        total_debt = sum(getattr(c, 'debt', 0) or 0 for c in customers)
        self.card_total.setText(f'{tr("total_customers")}\n {total}')
        self.card_debt.setText(f'{tr("total_outstanding")}\n {total_debt:,.2f}')
        # try to restore selection if possible
        if getattr(self, '_selected_customer', None):
            sel_id = self._selected_customer.id
            for idx, c in enumerate(customers):
                if c.id == sel_id:
                    self.cust_table.selectRow(idx)
                    break

    def _populate_customers(self, customers):
        self.cust_table.setRowCount(0)
        self._customers = customers
        for c in customers:
            row = self.cust_table.rowCount()
            self.cust_table.insertRow(row)
            self.cust_table.setRowHeight(row, 44)

            def _item(text, align=Qt.AlignCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                return it

            self.cust_table.setItem(row, 0, _item(c.id))
            self.cust_table.setItem(row, 1, _item(c.name, Qt.AlignLeft | Qt.AlignVCenter))
            self.cust_table.setItem(row, 2, _item(c.phone))

            debt_item = _item(f'{c.debt:,.2f}')
            if c.debt > 0:
                from PyQt5.QtGui import QColor
                debt_item.setForeground(QColor('#c0392b'))
            self.cust_table.setItem(row, 3, debt_item)

    def _on_search(self):
        self.refresh_customers()

    def _on_customer_selected(self):
        rows = self.cust_table.selectedItems()
        if not rows:
            self._selected_customer = None
            self._set_action_enabled(False)
            return

        row_idx = self.cust_table.currentRow()
        if row_idx < 0 or row_idx >= len(self._customers):
            return
        self._selected_customer = self._customers[row_idx]
        self._set_action_enabled(True)
        # update customer info panel
        c = self._selected_customer
        self.customer_info.setText(
            f'<b>{c.name}</b>\nPhone: {c.phone or "—"}\nAddress: {c.address or "—"}\nBalance: <span style="color:{"#c0392b" if c.debt>0 else "#1b5e20"}"><b>{c.debt:,.2f}</b></span>'
        )
        self.customer_info.setTextFormat(Qt.RichText)
        self._load_debt_history(self._selected_customer)

    def _set_action_enabled(self, enabled: bool):
        self.btn_edit.setEnabled(enabled)
        self.btn_del.setEnabled(enabled)
        self.btn_add_debt.setEnabled(enabled)
        self.btn_pay_debt.setEnabled(enabled)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def _add_customer(self):
        dlg = _CustomerDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            name, phone, address = dlg.values()
            self.cc.add_customer(name, phone, address)
            self.refresh_customers()

    def _edit_customer(self):
        if not self._selected_customer:
            return
        cid = self._selected_customer.id
        dlg = _CustomerDialog(self._selected_customer, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            name, phone, address = dlg.values()
            self.cc.update_customer(cid, name=name, phone=phone, address=address)
            self._refresh_and_reload(cid)

    def _delete_customer(self):
        if not self._selected_customer:
            return
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            f'Delete customer "{self._selected_customer.name}"?\nDebt entries will also be removed.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.cc.delete_customer(self._selected_customer.id)
            self._selected_customer = None
            self._set_action_enabled(False)
            self.debt_table.setRowCount(0)
            self.debt_title.setText('Select a customer to view debt history')
            self.refresh_customers()

    # ── Debt history ──────────────────────────────────────────────────────────

    def _load_debt_history(self, customer):
        if customer is None:
            return
        self.debt_title.setText(
            f'Debt History — <b>{customer.name}</b>  '
            f'| Current Balance: <span style="color:{"#c0392b" if customer.debt > 0 else "#1b5e20"}">'
            f'<b>{customer.debt:,.2f}</b></span>'
        )
        self.debt_title.setTextFormat(Qt.RichText)

        entries = self.cc.get_debt_entries(customer.id)
        self.debt_table.setRowCount(0)

        running = 0.0
        # entries are DESC by date; reverse to compute running balance forward
        for e in reversed(entries):
            running += e.amount
            row = self.debt_table.rowCount()
            self.debt_table.insertRow(row)
            self.debt_table.setRowHeight(row, 44)

            def _item(text, align=Qt.AlignCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                return it

            from PyQt5.QtGui import QColor
            self.debt_table.setItem(row, 0, _item(e.date[:16]))
            amt_item = _item(f'{e.amount:+,.2f}')
            amt_item.setForeground(QColor('#c0392b') if e.amount > 0 else QColor('#1b5e20'))
            self.debt_table.setItem(row, 1, amt_item)
            self.debt_table.setItem(row, 2, _item(e.note, Qt.AlignLeft | Qt.AlignVCenter))
            self.debt_table.setItem(row, 3, _item(f'{running:,.2f}'))

        # show newest first
        self.debt_table.scrollToBottom()

    def _add_debt(self):
        if not self._selected_customer:
            return
        cid = self._selected_customer.id
        dlg = _DebtDialog('Add Debt', self._selected_customer.name, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            amount, note = dlg.values()
            self.cc.add_debt(cid, amount, note)
            self._refresh_and_reload(cid)

    def _pay_debt(self):
        if not self._selected_customer:
            return
        cid = self._selected_customer.id
        dlg = _DebtDialog('Record Payment', self._selected_customer.name, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            amount, note = dlg.values()
            self.cc.pay_debt(cid, amount, note or 'Payment')
            self._refresh_and_reload(cid)

    def _refresh_and_reload(self, customer_id: int):
        """Refresh the customer list silently then reload the debt panel."""
        # block signals so repopulating the table doesn't clear _selected_customer
        self.cust_table.blockSignals(True)
        term = self.search_box.text().strip()
        customers = self.cc.search(term) if term else self.cc.get_all()
        self._populate_customers(customers)
        self.cust_table.blockSignals(False)

        # fetch fresh customer object and update panel
        fresh = self.cc.get_by_id(customer_id)
        if fresh:
            self._selected_customer = fresh
            self._load_debt_history(fresh)
