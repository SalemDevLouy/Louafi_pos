from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QSplitter, QFrame, QSizePolicy, QDateEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QColor

from controllers.supplier_controller import SupplierController
from controllers.product_controller import ProductController
import utils.icons as ic
from utils.categories import CATEGORIES
from utils.barcode import generate_barcode
from utils.lang import lang_manager, tr


# ─────────────────────────────────────────────────────────────────────────────
#  Dialogs
# ─────────────────────────────────────────────────────────────────────────────

class _SupplierDialog(QDialog):
    """Add / Edit supplier dialog."""
    def __init__(self, supplier=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Edit Supplier' if supplier else 'New Supplier')
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setSpacing(14)

        self.name_edit     = QLineEdit(supplier.name     if supplier else '')
        self.phone_edit    = QLineEdit(supplier.phone    if supplier else '')

        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.addItems(CATEGORIES)
        if supplier and supplier.category:
            idx = self.cat_combo.findText(supplier.category, Qt.MatchFixedString)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
            else:
                self.cat_combo.setCurrentText(supplier.category)

        layout.addRow('Full Name *:', self.name_edit)
        layout.addRow('Phone:',       self.phone_edit)
        layout.addRow('Category:',    self.cat_combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, 'Validation', 'Supplier name is required.')
            return
        self.accept()

    def values(self):
        return (
            self.name_edit.text().strip(),
            self.phone_edit.text().strip(),
            self.cat_combo.currentText().strip(),
        )


class _BillingOrderDialog(QDialog):
    """Create / Edit a billing order (header only — items added separately)."""
    def __init__(self, order=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Edit Billing' if order else 'New Billing')
        self.setMinimumWidth(380)

        layout = QFormLayout(self)
        layout.setSpacing(14)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        if order:
            try:
                self.date_edit.setDate(QDate.fromString(order.date[:10], 'yyyy-MM-dd'))
            except Exception:
                self.date_edit.setDate(QDate.currentDate())
        else:
            self.date_edit.setDate(QDate.currentDate())

        self.note_edit = QLineEdit(order.note if order else '')
        self.note_edit.setPlaceholderText('Optional note…')

        layout.addRow('Date:', self.date_edit)
        layout.addRow('Note:', self.note_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def values(self):
        return (
            self.date_edit.date().toString('yyyy-MM-dd'),
            self.note_edit.text().strip(),
        )


class _BillingItemDialog(QDialog):
    """Add / Edit a single line inside a billing order.
    Includes an inline 'New Product' form so unknown products can be created on the spot.
    """
    def __init__(self, product_controller: ProductController, item=None, parent=None):
        super().__init__(parent)
        self.pc = product_controller
        self._item = item
        self.setWindowTitle('Edit Item' if item else 'Add Item to Billing')
        self.setMinimumWidth(460)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setSpacing(10)

        # ── Product selector row ──────────────────────────────────────────────
        prod_row = QHBoxLayout()
        self.prod_combo = QComboBox()
        self.prod_combo.setEditable(True)
        self.prod_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._products = []
        self._reload_products(select_id=item.product_id if item else None)

        if item:
            self.prod_combo.setEnabled(False)

        self.btn_new_prod = QPushButton()
        self.btn_new_prod.setIcon(ic.ic_add(color='#1b5e20'))
        self.btn_new_prod.setIconSize(ic.SM)
        self.btn_new_prod.setFixedSize(32, 32)
        self.btn_new_prod.setToolTip('Create a new product')
        self.btn_new_prod.setStyleSheet(
            'QPushButton { background:#e8f5e9; border:1px solid #a5d6a7; border-radius:6px; }'
            'QPushButton:hover { background:#c8e6c9; }'
        )
        self.btn_new_prod.clicked.connect(self._toggle_new_product_form)
        prod_row.addWidget(self.prod_combo, 1)
        prod_row.addWidget(self.btn_new_prod)

        prod_label_row = QFormLayout()
        prod_label_row.addRow('Product *:', prod_row)
        self._main_layout.addLayout(prod_label_row)

        # ── Inline new-product form (hidden by default) ───────────────────────
        self._new_prod_frame = QFrame()
        self._new_prod_frame.setStyleSheet(
            'QFrame { background:#f1f8e9; border:1px solid #aed581; border-radius:8px; padding:4px; }'
        )
        np_layout = QFormLayout(self._new_prod_frame)
        np_layout.setSpacing(8)
        np_layout.setContentsMargins(10, 8, 10, 8)

        np_title = QLabel('New Product')
        np_title.setStyleSheet('font-weight:700; color:#33691e; font-size:13px;')
        np_layout.addRow(np_title)

        self.np_name     = QLineEdit()
        self.np_name.setPlaceholderText('Product name *')
        self.np_barcode  = QLineEdit()
        self.np_barcode.setPlaceholderText('Barcode (leave blank to auto-generate)')
        self.np_category = QComboBox()
        self.np_category.setEditable(True)
        self.np_category.addItem('')
        self.np_category.addItems(CATEGORIES)

        self.btn_create_prod = QPushButton(' Create & Select')
        self.btn_create_prod.setIcon(ic.ic_add())
        self.btn_create_prod.setIconSize(ic.SM)
        self.btn_create_prod.setStyleSheet(
            'QPushButton { background:#558b2f; color:white; border-radius:6px; padding:5px 12px; }'
            'QPushButton:hover { background:#33691e; }'
        )
        self.btn_create_prod.clicked.connect(self._create_product)

        np_layout.addRow('Name *:', self.np_name)
        np_layout.addRow('Barcode:', self.np_barcode)
        np_layout.addRow('Category:', self.np_category)
        np_layout.addRow('', self.btn_create_prod)

        self._new_prod_frame.setVisible(False)
        self._main_layout.addWidget(self._new_prod_frame)

        # ── Quantity / prices ─────────────────────────────────────────────────
        fields_layout = QFormLayout()
        fields_layout.setSpacing(10)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 999_999)
        self.qty_spin.setValue(item.quantity if item else 1)

        self.buy_spin = QDoubleSpinBox()
        self.buy_spin.setRange(0, 9_999_999)
        self.buy_spin.setDecimals(2)
        self.buy_spin.setValue(item.buy_price if item else 0.0)

        self.sale_spin = QDoubleSpinBox()
        self.sale_spin.setRange(0, 9_999_999)
        self.sale_spin.setDecimals(2)
        self.sale_spin.setValue(item.sale_price if item else 0.0)

        fields_layout.addRow('Quantity:',   self.qty_spin)
        fields_layout.addRow('Buy Price:',  self.buy_spin)
        fields_layout.addRow('Sale Price:', self.sale_spin)
        self._main_layout.addLayout(fields_layout)

        # auto-fill prices when product changes
        self.prod_combo.currentIndexChanged.connect(self._fill_prices)

        # ── Dialog buttons ────────────────────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        self._main_layout.addWidget(btns)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _reload_products(self, select_id=None):
        self.prod_combo.blockSignals(True)
        self.prod_combo.clear()
        self._products = self.pc.get_all()
        for p in self._products:
            self.prod_combo.addItem(f'{p.name}  [{p.barcode or "—"}]', p.id)
        if select_id is not None:
            idx = next((i for i, p in enumerate(self._products) if p.id == select_id), 0)
            self.prod_combo.setCurrentIndex(idx)
        self.prod_combo.blockSignals(False)

    def _toggle_new_product_form(self):
        visible = not self._new_prod_frame.isVisible()
        self._new_prod_frame.setVisible(visible)
        self.btn_new_prod.setToolTip('Hide new product form' if visible else 'Create a new product')
        self.adjustSize()

    def _create_product(self):
        name = self.np_name.text().strip()
        if not name:
            QMessageBox.warning(self, 'Validation', 'Product name is required.')
            return
        barcode  = self.np_barcode.text().strip() or None
        category = self.np_category.currentText().strip() or None
        try:
            new_prod = self.pc.add_product(name, barcode, 0.0, 0, category)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
            return
        self._reload_products(select_id=new_prod.id)
        # pre-fill barcode field for reference
        self.np_name.clear()
        self.np_barcode.clear()
        self.np_category.setCurrentIndex(0)
        self._new_prod_frame.setVisible(False)
        self.adjustSize()

    def _fill_prices(self, idx: int):
        if idx < 0 or idx >= len(self._products):
            return
        p = self._products[idx]
        if self.buy_spin.value() == 0:
            self.buy_spin.setValue(p.cost_price or 0.0)
        if self.sale_spin.value() == 0:
            self.sale_spin.setValue(p.price or 0.0)

    def _on_accept(self):
        if self.prod_combo.currentData() is None:
            QMessageBox.warning(self, 'Validation', 'Please select a product.')
            return
        if self.qty_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation', 'Quantity must be at least 1.')
            return
        self.accept()

    def values(self):
        product_id = self.prod_combo.currentData()
        return (
            product_id,
            self.qty_spin.value(),
            self.buy_spin.value(),
            self.sale_spin.value(),
        )



# ─────────────────────────────────────────────────────────────────────────────
#  Billing Items panel (right side when an order is selected)
# ─────────────────────────────────────────────────────────────────────────────

class _BillingItemsPanel(QWidget):
    """Shows line items for the selected billing order."""
    def __init__(self, sc: SupplierController, pc: ProductController, parent=None):
        super().__init__(parent)
        self.sc = sc
        self.pc = pc
        self._order_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # header row
        hdr = QHBoxLayout()
        self.title_lbl = QLabel('Items')
        self.title_lbl.setObjectName('section_title')
        hdr.addWidget(self.title_lbl)
        hdr.addStretch()

        self.btn_add = QPushButton(' Add Item')
        self.btn_add.setIcon(ic.ic_add())
        self.btn_add.setIconSize(ic.SM)
        self.btn_add.setEnabled(False)
        self.btn_add.setStyleSheet(
            'QPushButton { background:#1a73e8; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#1558b0; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_add.clicked.connect(self._add_item)
        hdr.addWidget(self.btn_add)

        self.btn_edit_item = QPushButton(' Edit')
        self.btn_edit_item.setIcon(ic.ic_edit())
        self.btn_edit_item.setIconSize(ic.SM)
        self.btn_edit_item.setEnabled(False)
        self.btn_edit_item.setStyleSheet(
            'QPushButton { background:#f57c00; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#e65100; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_edit_item.clicked.connect(self._edit_item)
        hdr.addWidget(self.btn_edit_item)

        self.btn_del_item = QPushButton(' Delete')
        self.btn_del_item.setIcon(ic.ic_delete())
        self.btn_del_item.setIconSize(ic.SM)
        self.btn_del_item.setEnabled(False)
        self.btn_del_item.setStyleSheet(
            'QPushButton { background:#e53935; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#b71c1c; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_del_item.clicked.connect(self._delete_item)
        hdr.addWidget(self.btn_del_item)

        layout.addLayout(hdr)

        # items table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ['#', 'Product', 'Qty', 'Buy Price', 'Sale Price', 'Total Cost']
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self.table)

        # total cost footer
        self.cost_lbl = QLabel('Total Cost: 0.00')
        self.cost_lbl.setStyleSheet('font-size:15px; font-weight:700; color:#0d47a1; padding:4px;')
        layout.addWidget(self.cost_lbl)

    # ── public API ────────────────────────────────────────────────────────────

    def load_order(self, order_id: int | None):
        self._order_id = order_id
        self.btn_add.setEnabled(order_id is not None)
        self._refresh()
        if order_id:
            self.title_lbl.setText(f'Items — Billing #{order_id}')
        else:
            self.title_lbl.setText('Items')

    # ── internal ──────────────────────────────────────────────────────────────

    def _refresh(self):
        self.table.setRowCount(0)
        self.btn_edit_item.setEnabled(False)
        self.btn_del_item.setEnabled(False)
        if not self._order_id:
            self.cost_lbl.setText('Total Cost: 0.00')
            return
        items = self.sc.get_items_for_order(self._order_id)
        for item in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            line_cost = item.quantity * item.buy_price
            vals = [
                str(item.id),
                item.product_name,
                str(item.quantity),
                f'{item.buy_price:,.2f}',
                f'{item.sale_price:,.2f}',
                f'{line_cost:,.2f}',
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setData(Qt.UserRole, item.id)
                if c in (2, 3, 4, 5):
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, cell)
        total = self.sc.order_total_cost(self._order_id)
        self.cost_lbl.setText(f'Total Cost: {total:,.2f}')

    def _on_selection(self):
        has = bool(self.table.selectedItems())
        self.btn_edit_item.setEnabled(has and self._order_id is not None)
        self.btn_del_item.setEnabled(has and self._order_id is not None)

    def _selected_item_id(self) -> int | None:
        rows = self.table.selectedItems()
        if not rows:
            return None
        return rows[0].data(Qt.UserRole)

    def _add_item(self):
        dlg = _BillingItemDialog(self.pc, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        product_id, qty, buy, sale = dlg.values()
        if product_id is None:
            return
        self.sc.add_billing_item(self._order_id, product_id, qty, buy, sale)
        self._refresh()

    def _edit_item(self):
        item_id = self._selected_item_id()
        if item_id is None:
            return
        # find the BillingItem object
        items = self.sc.get_items_for_order(self._order_id)
        item = next((i for i in items if i.id == item_id), None)
        if not item:
            return
        dlg = _BillingItemDialog(self.pc, item=item, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        _, qty, buy, sale = dlg.values()
        self.sc.update_billing_item(item_id, qty, buy, sale)
        self._refresh()

    def _delete_item(self):
        item_id = self._selected_item_id()
        if item_id is None:
            return
        reply = QMessageBox.question(
            self, 'Delete Item',
            'Remove this item? Stock will be reversed.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.sc.delete_billing_item(item_id)
            self._refresh()


# ─────────────────────────────────────────────────────────────────────────────
#  Billing Orders panel (middle column)
# ─────────────────────────────────────────────────────────────────────────────

class _BillingOrdersPanel(QWidget):
    """Lists billing orders for the selected supplier."""
    def __init__(
        self,
        sc: SupplierController,
        pc: ProductController,
        items_panel: _BillingItemsPanel,
        parent=None,
    ):
        super().__init__(parent)
        self.sc = sc
        self.pc = pc
        self.items_panel = items_panel
        self._supplier_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # header
        hdr = QHBoxLayout()
        self.title_lbl = QLabel('Billings')
        self.title_lbl.setObjectName('section_title')
        hdr.addWidget(self.title_lbl)
        hdr.addStretch()

        self.btn_new_order = QPushButton(' New Billing')
        self.btn_new_order.setIcon(ic.ic_add_billing())
        self.btn_new_order.setIconSize(ic.SM)
        self.btn_new_order.setEnabled(False)
        self.btn_new_order.setStyleSheet(
            'QPushButton { background:#1a73e8; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#1558b0; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_new_order.clicked.connect(self._new_order)
        hdr.addWidget(self.btn_new_order)

        self.btn_edit_order = QPushButton(' Edit')
        self.btn_edit_order.setIcon(ic.ic_edit())
        self.btn_edit_order.setIconSize(ic.SM)
        self.btn_edit_order.setEnabled(False)
        self.btn_edit_order.setStyleSheet(
            'QPushButton { background:#f57c00; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#e65100; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_edit_order.clicked.connect(self._edit_order)
        hdr.addWidget(self.btn_edit_order)

        self.btn_del_order = QPushButton(' Delete')
        self.btn_del_order.setIcon(ic.ic_delete())
        self.btn_del_order.setIconSize(ic.SM)
        self.btn_del_order.setEnabled(False)
        self.btn_del_order.setStyleSheet(
            'QPushButton { background:#e53935; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#b71c1c; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_del_order.clicked.connect(self._delete_order)
        hdr.addWidget(self.btn_del_order)

        layout.addLayout(hdr)

        # orders table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['#', 'Date', 'Total Cost', 'Note'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self.table)

    # ── public API ────────────────────────────────────────────────────────────

    def load_supplier(self, supplier_id: int | None):
        self._supplier_id = supplier_id
        self.btn_new_order.setEnabled(supplier_id is not None)
        self._refresh()
        if supplier_id:
            self.title_lbl.setText(f'Billings')
        else:
            self.title_lbl.setText('Billings')
        self.items_panel.load_order(None)

    # ── internal ──────────────────────────────────────────────────────────────

    def _refresh(self):
        self.table.setRowCount(0)
        self.btn_edit_order.setEnabled(False)
        self.btn_del_order.setEnabled(False)
        if not self._supplier_id:
            return
        orders = self.sc.get_orders_for_supplier(self._supplier_id)
        for order in orders:
            r = self.table.rowCount()
            self.table.insertRow(r)
            total_cost = self.sc.order_total_cost(order.id)
            vals = [str(order.id), order.date[:10], f'{total_cost:,.2f}', order.note]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setData(Qt.UserRole, order.id)
                if c == 2:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, cell)

    def _on_selection(self):
        rows = self.table.selectedItems()
        has = bool(rows)
        self.btn_edit_order.setEnabled(has)
        self.btn_del_order.setEnabled(has)
        if has:
            order_id = rows[0].data(Qt.UserRole)
            self.items_panel.load_order(order_id)
        else:
            self.items_panel.load_order(None)

    def _selected_order_id(self) -> int | None:
        rows = self.table.selectedItems()
        return rows[0].data(Qt.UserRole) if rows else None

    def _new_order(self):
        dlg = _BillingOrderDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        date, note = dlg.values()
        self.sc.add_billing_order(self._supplier_id, note, date)
        self._refresh()

    def _edit_order(self):
        order_id = self._selected_order_id()
        if order_id is None:
            return
        order = self.sc.get_order_by_id(order_id)
        if not order:
            return
        dlg = _BillingOrderDialog(order=order, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        date, note = dlg.values()
        self.sc.update_billing_order(order_id, note, date)
        self._refresh()

    def _delete_order(self):
        order_id = self._selected_order_id()
        if order_id is None:
            return
        reply = QMessageBox.question(
            self, 'Delete Billing',
            'Delete this billing order and all its items?\nStock will be reversed.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.sc.delete_billing_order(order_id)
            self.items_panel.load_order(None)
            self._refresh()


# ─────────────────────────────────────────────────────────────────────────────
#  Main SuppliersView
# ─────────────────────────────────────────────────────────────────────────────

class SuppliersView(QWidget):
    def __init__(self, product_controller: ProductController, parent=None):
        super().__init__(parent)
        self.sc = SupplierController()
        self.pc = product_controller
        self._build_ui()
        self.refresh()
        lang_manager.lang_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, lang=None):
        self.page_title_lbl.setText(tr('page_suppliers'))
        self.search.setPlaceholderText(tr('search_sup'))
        self.btn_add.setText(tr('btn_add'))
        self.btn_edit.setText(tr('btn_edit'))
        self.btn_del.setText(tr('btn_delete'))
        self.sup_table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_phone'), tr('col_category')
        ])

    def refresh(self):
        self._load_suppliers()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(12)

        # ── Title ─────────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(ic.ic_page_suppliers().pixmap(ic.LG))
        icon_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.page_title_lbl = QLabel(tr('page_suppliers'))
        self.page_title_lbl.setObjectName('page_title')
        self.page_title_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        title_row.addWidget(icon_lbl)
        title_row.addWidget(self.page_title_lbl)
        title_row.addStretch()
        root.addLayout(title_row)

        # ── 3-pane splitter ───────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left pane — supplier list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # toolbar
        toolbar = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('search_sup'))
        self.search.addAction(ic.ic_search(), QLineEdit.LeadingPosition)
        self.search.setFixedHeight(36)
        self.search.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search, 1)

        self.btn_add = QPushButton(tr('btn_add'))
        self.btn_add.setIcon(ic.ic_add())
        self.btn_add.setIconSize(ic.SM)
        self.btn_add.setStyleSheet(
            'QPushButton { background:#1b5e20; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#145218; }'
        )
        self.btn_add.clicked.connect(self._add_supplier)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QPushButton(tr('btn_edit'))
        self.btn_edit.setIcon(ic.ic_edit())
        self.btn_edit.setIconSize(ic.SM)
        self.btn_edit.setEnabled(False)
        self.btn_edit.setStyleSheet(
            'QPushButton { background:#f57c00; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#e65100; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_edit.clicked.connect(self._edit_supplier)
        toolbar.addWidget(self.btn_edit)

        self.btn_del = QPushButton(tr('btn_delete'))
        self.btn_del.setIcon(ic.ic_delete())
        self.btn_del.setIconSize(ic.SM)
        self.btn_del.setEnabled(False)
        self.btn_del.setStyleSheet(
            'QPushButton { background:#c0392b; color:white; border-radius:6px; padding:6px 14px; }'
            'QPushButton:hover { background:#96281b; }'
            'QPushButton:disabled { background:#b0bec5; }'
        )
        self.btn_del.clicked.connect(self._delete_supplier)
        toolbar.addWidget(self.btn_del)

        left_layout.addLayout(toolbar)

        # supplier table
        self.sup_table = QTableWidget(0, 4)
        self.sup_table.setHorizontalHeaderLabels([tr('col_id'), tr('col_name'), tr('col_phone'), tr('col_category')])
        self.sup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.sup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sup_table.setAlternatingRowColors(True)
        self.sup_table.verticalHeader().setVisible(False)
        self.sup_table.itemSelectionChanged.connect(self._on_supplier_selected)
        left_layout.addWidget(self.sup_table)

        # Middle + Right panes
        self._items_panel   = _BillingItemsPanel(self.sc, self.pc)
        self._orders_panel  = _BillingOrdersPanel(self.sc, self.pc, self._items_panel)

        # wrap each pane in a frame with padding
        mid_frame  = self._wrap(self._orders_panel)
        right_frame = self._wrap(self._items_panel)

        splitter.addWidget(left)
        splitter.addWidget(mid_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([280, 340, 420])

        root.addWidget(splitter, 1)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _wrap(widget: QWidget) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(widget)
        return frame

    def _load_suppliers(self, term: str = ''):
        self.sup_table.setRowCount(0)
        self.btn_edit.setEnabled(False)
        self.btn_del.setEnabled(False)
        suppliers = self.sc.search_suppliers(term) if term else self.sc.get_all_suppliers()
        for s in suppliers:
            r = self.sup_table.rowCount()
            self.sup_table.insertRow(r)
            vals = [str(s.id), s.name, s.phone, s.category]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setData(Qt.UserRole, s.id)
                self.sup_table.setItem(r, c, cell)
        self._orders_panel.load_supplier(None)

    def _on_search(self, text: str):
        self._load_suppliers(text.strip())

    def _on_supplier_selected(self):
        rows = self.sup_table.selectedItems()
        has = bool(rows)
        self.btn_edit.setEnabled(has)
        self.btn_del.setEnabled(has)
        if has:
            sid = rows[0].data(Qt.UserRole)
            self._orders_panel.load_supplier(sid)
        else:
            self._orders_panel.load_supplier(None)

    def _selected_supplier_id(self) -> int | None:
        rows = self.sup_table.selectedItems()
        return rows[0].data(Qt.UserRole) if rows else None

    def _add_supplier(self):
        dlg = _SupplierDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        name, phone, cat = dlg.values()
        self.sc.add_supplier(name, phone, cat)
        self._load_suppliers(self.search.text().strip())

    def _edit_supplier(self):
        sid = self._selected_supplier_id()
        if sid is None:
            return
        sup = self.sc.get_supplier_by_id(sid)
        if not sup:
            return
        dlg = _SupplierDialog(supplier=sup, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        name, phone, cat = dlg.values()
        self.sc.update_supplier(sid, name, phone, cat)
        self._load_suppliers(self.search.text().strip())

    def _delete_supplier(self):
        sid = self._selected_supplier_id()
        if sid is None:
            return
        sup = self.sc.get_supplier_by_id(sid)
        reply = QMessageBox.question(
            self, 'Delete Supplier',
            f'Delete supplier "{sup.name}" and all their billing data?\nThis cannot be undone.',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.sc.delete_supplier(sid)
            self._load_suppliers(self.search.text().strip())
