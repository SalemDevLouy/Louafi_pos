from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QSizePolicy, QLineEdit
from controllers.product_controller import ProductController
import utils.icons as ic
from utils.categories import CATEGORIES
from utils.lang import lang_manager, tr


class ProductsView(QtWidgets.QWidget):
    def __init__(self, product_controller: ProductController):
        super().__init__()
        self.product_controller = product_controller
        self._build_ui()
        self.load_products()
        lang_manager.lang_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, lang=None):
        self.page_title.setText(tr('page_products'))
        self.search_input.setPlaceholderText(tr('search_prod'))
        self.table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_barcode'), tr('col_category'),
            tr('col_buy'), tr('col_sale'), tr('col_margin'), tr('col_qty')
        ])
        self.form_lbl.setText(tr('product_details'))
        self.btn_add.setText(tr('btn_add_product'))
        self.btn_update.setText(tr('btn_update'))
        self.btn_delete.setText(tr('btn_delete'))
        self.btn_clear.setText(tr('btn_clear'))

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # ── Title + search bar ────────────────────────────────────────────────
        top = QtWidgets.QHBoxLayout()
        title_ic = QtWidgets.QLabel()
        title_ic.setPixmap(ic.ic_page_products().pixmap(ic.LG))
        title_ic.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.page_title = QtWidgets.QLabel(tr('page_products'))
        self.page_title.setObjectName('page_title')
        self.page_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        top.addWidget(title_ic)
        top.addWidget(self.page_title)
        top.addStretch()

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText(tr('search_prod'))
        self.search_input.addAction(ic.ic_search(), QLineEdit.LeadingPosition)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        top.addWidget(self.search_input)
        root.addLayout(top)

        # ── Table ─────────────────────────────────────────────────────────────
        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_barcode'), tr('col_category'),
            tr('col_buy'), tr('col_sale'), tr('col_margin'), tr('col_qty')
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.fill_form_from_selection)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # ID
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)           # Name
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Barcode
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Category
        hh.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Buy
        hh.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)  # Sale
        hh.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)  # Margin
        hh.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeToContents)  # Qty
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setStyleSheet(
            'QHeaderView::section { background:#1a73e8; color:white; padding:6px; font-weight:600; }'
        )
        root.addWidget(self.table)

        # ── Form ──────────────────────────────────────────────────────────────
        form_frame = QtWidgets.QFrame()
        form_frame.setStyleSheet(
            'QFrame { background:#f8faff; border:1px solid #d0d7de; border-radius:10px; }'
        )
        form_outer = QtWidgets.QVBoxLayout(form_frame)
        form_outer.setContentsMargins(16, 12, 16, 12)
        form_outer.setSpacing(10)

        self.form_lbl = QtWidgets.QLabel(tr('product_details'))
        self.form_lbl.setObjectName('section_title')
        self.form_lbl.setStyleSheet('border:none; background:transparent;')
        form_outer.addWidget(self.form_lbl)

        form = QtWidgets.QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.f_name     = QtWidgets.QLineEdit()
        self.f_barcode  = QtWidgets.QLineEdit()

        self.f_category = QtWidgets.QComboBox()
        self.f_category.setEditable(True)
        self.f_category.addItem('')          # blank = no category
        self.f_category.addItems(CATEGORIES)
        self.f_category.setCurrentIndex(0)

        self.f_qty      = QtWidgets.QSpinBox()
        self.f_qty.setMaximum(1_000_000)

        # ── Price fields side by side ──────────────────────────────────────
        price_row = QtWidgets.QHBoxLayout()
        price_row.setSpacing(12)

        buy_col = QtWidgets.QVBoxLayout()
        buy_lbl = QtWidgets.QLabel('Buy Price')
        buy_lbl.setStyleSheet('font-weight:600; color:#555; border:none; background:transparent; font-size:14px;')
        self.f_cost_price = QtWidgets.QDoubleSpinBox()
        self.f_cost_price.setRange(0, 9_999_999)
        self.f_cost_price.setDecimals(2)
        self.f_cost_price.setPrefix('  ')
        self.f_cost_price.setFixedHeight(42)
        self.f_cost_price.setStyleSheet('font-size:18px; font-weight:600; color:#e65100;')
        self.f_cost_price.valueChanged.connect(self._update_margin_preview)
        buy_col.addWidget(buy_lbl)
        buy_col.addWidget(self.f_cost_price)

        sale_col = QtWidgets.QVBoxLayout()
        sale_lbl = QtWidgets.QLabel('Sale Price')
        sale_lbl.setStyleSheet('font-weight:600; color:#555; border:none; background:transparent; font-size:14px;')
        self.f_price = QtWidgets.QDoubleSpinBox()
        self.f_price.setRange(0, 9_999_999)
        self.f_price.setDecimals(2)
        self.f_price.setPrefix('  ')
        self.f_price.setFixedHeight(42)
        self.f_price.setStyleSheet('font-size:18px; font-weight:600; color:#1565c0;')
        self.f_price.valueChanged.connect(self._update_margin_preview)
        sale_col.addWidget(sale_lbl)
        sale_col.addWidget(self.f_price)

        margin_col = QtWidgets.QVBoxLayout()
        margin_lbl = QtWidgets.QLabel('Margin')
        margin_lbl.setStyleSheet('font-weight:600; color:#555; border:none; background:transparent; font-size:14px;')
        self.margin_preview = QtWidgets.QLabel('—')
        self.margin_preview.setFixedHeight(42)
        self.margin_preview.setAlignment(Qt.AlignCenter)
        self.margin_preview.setStyleSheet(
            'font-size:18px; font-weight:700; color:#2e7d32;'
            'background:#e8f5e9; border-radius:8px; border:1px solid #a5d6a7;'
        )
        margin_col.addWidget(margin_lbl)
        margin_col.addWidget(self.margin_preview)

        price_row.addLayout(buy_col, 1)
        price_row.addLayout(sale_col, 1)
        price_row.addLayout(margin_col, 1)

        form.addRow('Name *:', self.f_name)
        form.addRow('Barcode:', self.f_barcode)
        form.addRow('Category:', self.f_category)
        form.addRow('Quantity:', self.f_qty)
        form_outer.addLayout(form)
        form_outer.addLayout(price_row)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add    = QtWidgets.QPushButton(tr('btn_add_product'))
        self.btn_add.setIcon(ic.ic_add())
        self.btn_add.setIconSize(ic.SM)
        self.btn_update = QtWidgets.QPushButton(tr('btn_update'))
        self.btn_update.setIcon(ic.ic_edit())
        self.btn_update.setIconSize(ic.SM)
        self.btn_delete = QtWidgets.QPushButton(tr('btn_delete'))
        self.btn_delete.setIcon(ic.ic_delete())
        self.btn_delete.setIconSize(ic.SM)
        self.btn_clear  = QtWidgets.QPushButton(tr('btn_clear'))

        self.btn_delete.setStyleSheet(
            'QPushButton { background:#e53935; color:white; border-radius:8px; padding:8px 16px; }'
            'QPushButton:hover { background:#b71c1c; }'
        )
        self.btn_clear.setStyleSheet(
            'QPushButton { background:#607d8b; color:white; border-radius:8px; padding:8px 16px; }'
            'QPushButton:hover { background:#455a64; }'
        )

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_clear)
        form_outer.addLayout(btn_layout)

        root.addWidget(form_frame)

        # wiring
        self.btn_add.clicked.connect(self.add_product)
        self.btn_update.clicked.connect(self.update_product)
        self.btn_delete.clicked.connect(self.delete_product)
        self.btn_clear.clicked.connect(self.clear_form)

    # ── Margin preview ────────────────────────────────────────────────────────

    def _update_margin_preview(self):
        cost = self.f_cost_price.value()
        sale = self.f_price.value()
        if cost > 0 and sale >= cost:
            margin = sale - cost
            pct = (margin / cost) * 100
            self.margin_preview.setText(f'+{margin:.2f}  ({pct:.0f}%)')
            self.margin_preview.setStyleSheet(
                'font-size:16px; font-weight:700; color:#2e7d32;'
                'background:#e8f5e9; border-radius:8px; border:1px solid #a5d6a7;'
            )
        elif sale > 0 and sale < cost:
            margin = sale - cost
            self.margin_preview.setText(f'{margin:.2f}  (loss)')
            self.margin_preview.setStyleSheet(
                'font-size:16px; font-weight:700; color:#c62828;'
                'background:#ffebee; border-radius:8px; border:1px solid #ef9a9a;'
            )
        else:
            self.margin_preview.setText('—')
            self.margin_preview.setStyleSheet(
                'font-size:18px; font-weight:700; color:#2e7d32;'
                'background:#e8f5e9; border-radius:8px; border:1px solid #a5d6a7;'
            )

    # ── Table loading ─────────────────────────────────────────────────────────

    def _on_search(self, text):
        term = text.strip()
        products = self.product_controller.search(term) if term else self.product_controller.get_all()
        self._populate_table(products)

    def load_products(self):
        self._populate_table(self.product_controller.get_all())

    def _populate_table(self, products):
        self.table.setRowCount(0)
        for p in products:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 44)

            def _item(text, align=Qt.AlignCenter):
                it = QtWidgets.QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                return it

            cost  = getattr(p, 'cost_price', 0) or 0
            sale  = p.price
            margin = sale - cost
            pct    = (margin / cost * 100) if cost > 0 else 0

            self.table.setItem(r, 0, _item(p.id))
            self.table.setItem(r, 1, _item(p.name, Qt.AlignLeft | Qt.AlignVCenter))
            self.table.setItem(r, 2, _item(p.barcode or ''))
            self.table.setItem(r, 3, _item(p.category or ''))

            cost_item = _item(f'{cost:.2f}')
            cost_item.setForeground(QColor('#e65100'))
            self.table.setItem(r, 4, cost_item)

            sale_item = _item(f'{sale:.2f}')
            sale_item.setForeground(QColor('#1565c0'))
            self.table.setItem(r, 5, sale_item)

            if cost > 0:
                margin_text = f'+{margin:.2f} ({pct:.0f}%)' if margin >= 0 else f'{margin:.2f} (loss)'
                margin_item = _item(margin_text)
                margin_item.setForeground(QColor('#2e7d32') if margin >= 0 else QColor('#c62828'))
            else:
                margin_item = _item('—')
            self.table.setItem(r, 6, margin_item)

            qty_item = _item(p.quantity)
            if p.quantity == 0:
                qty_item.setForeground(QColor('#c62828'))
            elif p.quantity <= getattr(p, 'min_level', 5):
                qty_item.setForeground(QColor('#e65100'))
            self.table.setItem(r, 7, qty_item)

    # ── Form actions ──────────────────────────────────────────────────────────

    def add_product(self):
        name = self.f_name.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Name is required.')
            return
        barcode  = self.f_barcode.text().strip() or None
        category = self.f_category.currentText().strip() or None
        qty      = self.f_qty.value()
        sale     = self.f_price.value()
        cost     = self.f_cost_price.value()

        p = self.product_controller.add_product(name, barcode, sale, qty, category)
        self.product_controller.update_product(p.id, cost_price=cost)
        self.load_products()
        self.clear_form()

    def update_product(self):
        sel = self.table.selectedItems()
        if not sel:
            QtWidgets.QMessageBox.information(self, 'Info', 'Select a product first.')
            return
        product_id = int(self.table.item(sel[0].row(), 0).text())
        name = self.f_name.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Name is required.')
            return
        self.product_controller.update_product(
            product_id,
            name=name,
            barcode=self.f_barcode.text().strip() or None,
            price=self.f_price.value(),
            quantity=self.f_qty.value(),
            category=self.f_category.currentText().strip() or None,
            cost_price=self.f_cost_price.value(),
        )
        self.load_products()

    def delete_product(self):
        sel = self.table.selectedItems()
        if not sel:
            return
        product_id = int(self.table.item(sel[0].row(), 0).text())
        name = self.table.item(sel[0].row(), 1).text()
        reply = QtWidgets.QMessageBox.question(
            self, 'Confirm Delete', f'Delete "{name}"?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.product_controller.delete_product(product_id)
            self.load_products()
            self.clear_form()

    def fill_form_from_selection(self):
        sel = self.table.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        pid = int(self.table.item(row, 0).text())
        # fetch fresh product for accurate cost_price
        all_prods = self.product_controller.get_all()
        p = next((x for x in all_prods if x.id == pid), None)
        if not p:
            return
        self.f_name.setText(p.name)
        self.f_barcode.setText(p.barcode or '')
        # set category in the editable combo
        cat = p.category or ''
        idx = self.f_category.findText(cat, QtCore.Qt.MatchFixedString)
        if idx >= 0:
            self.f_category.setCurrentIndex(idx)
        else:
            self.f_category.setCurrentText(cat)
        self.f_qty.setValue(p.quantity)
        self.f_price.setValue(p.price)
        self.f_cost_price.setValue(getattr(p, 'cost_price', 0) or 0)

    def clear_form(self):
        self.f_name.clear()
        self.f_barcode.clear()
        self.f_category.setCurrentIndex(0)   # back to blank
        self.f_qty.setValue(0)
        self.f_price.setValue(0)
        self.f_cost_price.setValue(0)
        self.margin_preview.setText('—')
        self.table.clearSelection()
