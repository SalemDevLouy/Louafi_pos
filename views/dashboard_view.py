from PyQt5 import QtWidgets, QtCore
import random
from controllers.product_controller import ProductController
from controllers.sales_controller import SalesController
from controllers.customer_controller import CustomerController
import utils.icons as ic
from utils.lang import lang_manager, tr


class DashboardView(QtWidgets.QWidget):
    def __init__(self, sales_controller: SalesController, product_controller: ProductController):
        super().__init__()
        self.sales_controller = sales_controller
        self.product_controller = product_controller
        self.customer_controller = CustomerController()
        self._selected_customer_id = None

        layout = QtWidgets.QHBoxLayout(self)

        # ── Left panel ────────────────────────────────────────────────────────
        left = QtWidgets.QFrame()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setSpacing(6)

        # Search bar
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText(tr('search_placeholder'))
        self.search_input.addAction(ic.ic_search(), QtWidgets.QLineEdit.LeadingPosition)
        self.search_input.setClearButtonEnabled(True)
        left_layout.addWidget(self.search_input)

        # ── Search results section (hidden when search is empty) ──
        self.search_results_frame = QtWidgets.QFrame()
        search_results_layout = QtWidgets.QVBoxLayout(self.search_results_frame)
        search_results_layout.setContentsMargins(0, 0, 0, 0)
        search_results_layout.setSpacing(1)

        self.sr_label = QtWidgets.QLabel(tr('search_results'))
        self.sr_label.setObjectName('section_title')
        search_results_layout.addWidget(self.sr_label)

        sr_scroll = QtWidgets.QScrollArea()
        sr_scroll.setWidgetResizable(True)
        sr_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.search_container = QtWidgets.QWidget()
        self.search_grid = QtWidgets.QGridLayout(self.search_container)
        self.search_grid.setSpacing(1)
        sr_scroll.setWidget(self.search_container)
        search_results_layout.addWidget(sr_scroll)

        self.search_results_frame.setVisible(True)   # always visible

        # ── Speed Sale section (always visible) ───────────────────
        speed_frame = QtWidgets.QFrame()
        speed_frame_layout = QtWidgets.QVBoxLayout(speed_frame)
        speed_frame_layout.setContentsMargins(0, 0, 0, 0)
        speed_frame_layout.setSpacing(4)

        speed_header = QtWidgets.QHBoxLayout()
        self.speed_lbl = QtWidgets.QLabel(tr('speed_sale'))
        self.speed_lbl.setObjectName('section_title')
        self.btn_manage_speed = QtWidgets.QPushButton(tr('btn_manage'))
        self.btn_manage_speed.setIcon(ic.ic_manage())
        self.btn_manage_speed.setIconSize(ic.SM)
        self.btn_manage_speed.setFixedHeight(46)
        self.btn_manage_speed.setToolTip('Add / remove products from the speed list')
        speed_header.addWidget(self.speed_lbl)
        speed_header.addStretch()
        speed_header.addWidget(self.btn_manage_speed)
        speed_frame_layout.addLayout(speed_header)

        speed_scroll = QtWidgets.QScrollArea()
        speed_scroll.setWidgetResizable(True)
        speed_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.speed_container = QtWidgets.QWidget()
        self.speed_grid = QtWidgets.QGridLayout(self.speed_container)
        self.speed_grid.setSpacing(6)
        speed_scroll.setWidget(self.speed_container)
        speed_frame_layout.addWidget(speed_scroll, 1)

        # ── Splitter: search results (top) / speed sale (bottom) ──
        self.left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.addWidget(self.search_results_frame)   # index 0
        self.left_splitter.addWidget(speed_frame)                 # index 1
        # equal initial split
        self.left_splitter.setSizes([300, 300])
        left_layout.addWidget(self.left_splitter, 1)

        self.load_speed()
        self.load_random_suggestions()

        # Middle: cart
        middle = QtWidgets.QFrame()
        middle_layout = QtWidgets.QVBoxLayout(middle)

        # cart header: label + clear button
        cart_header = QtWidgets.QHBoxLayout()
        self.cart_lbl = QtWidgets.QLabel(tr('cart'))
        self.cart_lbl.setObjectName('section_title')
        self.btn_clear_cart = QtWidgets.QPushButton(tr('btn_clear_cart'))
        self.btn_clear_cart.setFixedHeight(46)
        cart_header.addWidget(self.cart_lbl)
        cart_header.addStretch()
        cart_header.addWidget(self.btn_clear_cart)
        middle_layout.addLayout(cart_header)

        self.cart_table = QtWidgets.QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_price'),
            tr('col_qty'), tr('col_total'), tr('col_actions')
        ])
        # stretch Name column; Qty column fills remaining space
        hh = self.cart_table.horizontalHeader()
        hh.setStyleSheet(
            'QHeaderView::section {'
            '  background-color: #1a73e8;'
            '  color: white;'
            '  font-weight: bold;'
            '  font-size: 13px;'
            '  padding: 6px;'
            '  border: none;'
            '}'
        )
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # ID
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)           # Name
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Price
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)             # Qty  ← fixed narrow
        hh.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Total
        hh.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)  # Actions
        self.cart_table.setColumnWidth(3, 80)                               # Qty width
        # taller rows
        self.cart_table.verticalHeader().setDefaultSectionSize(48)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        middle_layout.addWidget(self.cart_table)

        # Right: order summary
        right = QtWidgets.QFrame()
        right.setFixedWidth(350)
        right.setObjectName('orderSummary')
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # ── Order Summary title ───────────────────────────────────────────────
        self.summary_lbl = QtWidgets.QLabel(tr('order_summary'))
        self.summary_lbl.setObjectName('section_title')
        right_layout.addWidget(self.summary_lbl)

        # ── Customer selector ─────────────────────────────────────────────────
        self.cust_lbl = QtWidgets.QLabel(tr('customer'))
        self.cust_lbl.setObjectName('sub_title')
        right_layout.addWidget(self.cust_lbl)

        cust_row = QtWidgets.QHBoxLayout()
        self.cust_combo = QtWidgets.QComboBox()
        self.cust_combo.setFixedHeight(38)
        self.cust_combo.currentIndexChanged.connect(self._on_customer_changed)
        cust_row.addWidget(self.cust_combo, 1)

        btn_refresh_cust = QtWidgets.QPushButton()
        btn_refresh_cust.setIcon(ic.ic_refresh(color='#1a73e8'))
        btn_refresh_cust.setIconSize(ic.SM)
        btn_refresh_cust.setFixedSize(38, 38)
        btn_refresh_cust.setToolTip('Reload customer list')
        btn_refresh_cust.setStyleSheet(
            'QPushButton { background:#e8f0fe; border-radius:8px;'
            ' padding:0; border:none; }'
            'QPushButton:hover { background:#c5d8fc; }'
        )
        btn_refresh_cust.clicked.connect(self._load_customers)
        cust_row.addWidget(btn_refresh_cust)
        right_layout.addLayout(cust_row)

        # selected customer debt badge
        self.cust_debt_lbl = QtWidgets.QLabel('')
        self.cust_debt_lbl.setStyleSheet('color:#c0392b; font-size:13px; font-weight:600;')
        right_layout.addWidget(self.cust_debt_lbl)

        # ── Divider ───────────────────────────────────────────────────────────
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet('background:#e0e0e0;')
        line.setFixedHeight(1)
        right_layout.addWidget(line)

        # ── Total box ─────────────────────────────────────────────────────────
        self.lbl_total = QtWidgets.QLabel('Total\n0.00')
        self.lbl_total.setAlignment(QtCore.Qt.AlignCenter)
        # self.lbl_total.setFixedHeight(90)
        self.lbl_total.setStyleSheet(
            'QLabel {'
            '  font-size: 70px; font-weight: 800; color: #ffffff;'
            '  background: #1a73e8;'
            '  border-radius: 12px;'
            '  padding: 8px 16px;'
            '}'
        )
        right_layout.addWidget(self.lbl_total)

        right_layout.addStretch()

        # ── Action buttons ────────────────────────────────────────────────────
        self.btn_accept = QtWidgets.QPushButton(tr('btn_accept_sale'))
        self.btn_accept.setIcon(ic.ic_accept())
        self.btn_accept.setIconSize(ic.MD)
        self.btn_accept.setFixedHeight(48)
        self.btn_accept.setStyleSheet(
            'QPushButton { background:#1a73e8; color:white; border-radius:10px;'
            ' font-size:16px; font-weight:700; }'
            'QPushButton:hover { background:#1558b0; }'
        )

        self.btn_save_debt = QtWidgets.QPushButton(tr('btn_save_debt'))
        self.btn_save_debt.setIcon(ic.ic_debt())
        self.btn_save_debt.setIconSize(ic.MD)
        self.btn_save_debt.setFixedHeight(44)
        self.btn_save_debt.setEnabled(False)
        self.btn_save_debt.setStyleSheet(
            'QPushButton { background:#e53935; color:white; border-radius:10px;'
            ' font-size:15px; font-weight:600; }'
            'QPushButton:hover { background:#b71c1c; }'
            'QPushButton:disabled { background:#ccc; color:#888; }'
        )

        right_layout.addWidget(self.btn_accept)
        right_layout.addWidget(self.btn_save_debt)

        layout.addWidget(left, 1)
        layout.addWidget(middle, 2)
        layout.addWidget(right)

        # wiring
        self.search_input.textChanged.connect(self.on_search_changed)
        self.btn_accept.clicked.connect(self.accept_sale)
        self.btn_save_debt.clicked.connect(self.save_as_debt)
        self.btn_clear_cart.clicked.connect(self.clear_cart)
        self.btn_manage_speed.clicked.connect(self.open_speed_manager)

        # load customers into combo
        self._load_customers()

        # refresh initial cart view
        self.refresh_cart()

        # language support
        lang_manager.lang_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, lang=None):
        self.search_input.setPlaceholderText(tr('search_placeholder'))
        self.sr_label.setText(tr('search_results'))
        self.speed_lbl.setText(tr('speed_sale'))
        self.btn_manage_speed.setText(tr('btn_manage'))
        self.cart_lbl.setText(tr('cart'))
        self.btn_clear_cart.setText(tr('btn_clear_cart'))
        self.cart_table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_price'),
            tr('col_qty'), tr('col_total'), tr('col_actions')
        ])
        self.summary_lbl.setText(tr('order_summary'))
        self.cust_lbl.setText(tr('customer'))
        self.btn_accept.setText(tr('btn_accept_sale'))
        self.btn_save_debt.setText(tr('btn_save_debt'))

    # ── Grid helpers ──────────────────────────────────────────────────────────

    def _fill_grid(self, grid: QtWidgets.QGridLayout, products, cols: int = 3):
        """Clear a QGridLayout and populate it with product buttons (max 12)."""
        while grid.count():
            child = grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        grid.setSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(0)

        for idx, p in enumerate(products[:12]):
            btn = QtWidgets.QPushButton(p.name)
            btn.setFixedHeight(52)
            btn.setStyleSheet(
                'QPushButton {'
                '  text-align: center;'
                '  font-size: 16px;'
                '  font-weight: 600;'
                '  padding: 2px 4px;'
                '  margin: 0px;'
                '  border-radius: 0px;'
                '  border: 1px solid #b0bec5;'
                '}'
                'QPushButton:hover {'
                '  background: #1558b0;'
                '}'
            )
            btn.clicked.connect(lambda _, bc=p.barcode: self._add_by_barcode(bc))
            row, col = divmod(idx, cols)
            grid.addWidget(btn, row, col)

        # fill remaining slots up to 12 with "+" placeholder buttons
        filled = min(len(products), 12)
        for idx in range(filled, 12):
            plus_btn = QtWidgets.QPushButton('+')
            plus_btn.setFixedHeight(52)
            plus_btn.setStyleSheet(
                'QPushButton {'
                '  color: #aab4be;'
                '  background: transparent;'
                '  border: 2px dashed #d0d7de;'
                '  border-radius: 0px;'
                '  font-size: 22px;'
                '  font-weight: 300;'
                '  padding: 2px;'
                '  margin: 0px;'
                '}'
                'QPushButton:hover {'
                '  border-color: #1a73e8;'
                '  color: #1a73e8;'
                '  background: #f0f6ff;'
                '}'
            )
            plus_btn.clicked.connect(self.open_speed_manager)
            row, col = divmod(idx, cols)
            grid.addWidget(plus_btn, row, col)

    def _add_by_barcode(self, barcode: str):
        try:
            self.sales_controller.add_barcode_to_cart(barcode, 1)
            self.refresh_cart()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))

    # ── Speed Sale ────────────────────────────────────────────────────────────

    def load_speed(self):
        """Load (or reload) the permanent speed-sale grid."""
        prods = self.product_controller.get_all()
        fast = [p for p in prods if (p.category or '').lower() == 'fast']
        self._fill_grid(self.speed_grid, fast if fast else prods, cols=3)

    # ── Live search ───────────────────────────────────────────────────────────

    def load_random_suggestions(self):
        """Fill the search-results grid with 12 random products."""
        prods = self.product_controller.get_all()
        sample = random.sample(prods, min(12, len(prods))) if prods else []
        self._fill_grid(self.search_grid, sample, cols=3)

    def on_search_changed(self, text: str):
        """Called on every keystroke. Shows search results or random products."""
        term = text.strip()
        if not term:
            # no query → show random products in the top half
            self.load_random_suggestions()
            return

        results = self.product_controller.search(term)
        self._fill_grid(self.search_grid, results, cols=3)

    # kept for backward compat
    def do_search(self):
        self.on_search_changed(self.search_input.text())

    def speed_add(self, item):
        self._add_by_barcode(item.data(QtCore.Qt.UserRole))

    def clear_cart(self):
        """Remove every item from the in-memory cart and refresh the view."""
        for item in list(self.sales_controller.cart):
            self.sales_controller.remove_item(item['product'].id)
        self.refresh_cart()

    # ── Speed-list manager ────────────────────────────────────────────────────

    def open_speed_manager(self):
        """Dialog: left = all products, right = current speed products.
        Use ▶ / ◀ arrow buttons to add/remove from speed list."""
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Manage Speed Products')
        dlg.resize(640, 420)

        all_prods = self.product_controller.get_all()
        speed_ids = {p.id for p in all_prods if (p.category or '').lower() == 'fast'}

        lv_layout = QtWidgets.QVBoxLayout()
        lv_layout.addWidget(QtWidgets.QLabel('All Products'))
        left_list = QtWidgets.QListWidget()
        left_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        lv_layout.addWidget(left_list)

        rv_layout = QtWidgets.QVBoxLayout()
        rv_layout.addWidget(QtWidgets.QLabel('Speed Products'))
        right_list = QtWidgets.QListWidget()
        right_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        rv_layout.addWidget(right_list)

        for p in all_prods:
            it = QtWidgets.QListWidgetItem(f"{p.name}  —  {p.price:.2f}")
            it.setData(QtCore.Qt.UserRole, p.id)
            if p.id in speed_ids:
                right_list.addItem(it)
            else:
                left_list.addItem(it)

        btn_add = QtWidgets.QPushButton('▶ Add')
        btn_add.setFixedHeight(32)
        btn_rem = QtWidgets.QPushButton('◀ Remove')
        btn_rem.setFixedHeight(32)
        arrow_layout = QtWidgets.QVBoxLayout()
        arrow_layout.addStretch()
        arrow_layout.addWidget(btn_add)
        arrow_layout.addWidget(btn_rem)
        arrow_layout.addStretch()

        mid_layout = QtWidgets.QHBoxLayout()
        mid_layout.addLayout(lv_layout)
        mid_layout.addLayout(arrow_layout)
        mid_layout.addLayout(rv_layout)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)

        dlg_layout = QtWidgets.QVBoxLayout(dlg)
        dlg_layout.addLayout(mid_layout)
        dlg_layout.addWidget(btn_box)

        def move_to_speed():
            for it in left_list.selectedItems():
                left_list.takeItem(left_list.row(it))
                right_list.addItem(it)

        def move_from_speed():
            for it in right_list.selectedItems():
                right_list.takeItem(right_list.row(it))
                left_list.addItem(it)

        btn_add.clicked.connect(move_to_speed)
        btn_rem.clicked.connect(move_from_speed)

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # collect final speed ids from right_list
            new_speed_ids = set()
            for i in range(right_list.count()):
                new_speed_ids.add(right_list.item(i).data(QtCore.Qt.UserRole))
            self._apply_speed_changes(all_prods, new_speed_ids)
            self.load_speed()

    def _apply_speed_changes(self, all_prods, new_speed_ids: set):
        """Persist category changes: 'fast' for speed products, None for others."""
        for p in all_prods:
            current_fast = (p.category or '').lower() == 'fast'
            should_be_fast = p.id in new_speed_ids
            if current_fast != should_be_fast:
                new_cat = 'fast' if should_be_fast else None
                self.product_controller.update_product(p.id, category=new_cat)

    def refresh_cart(self):
        cart = self.sales_controller.cart
        self.cart_table.setRowCount(0)
        for item in cart:
            p = item['product']
            q = item['quantity']
            r = self.cart_table.rowCount()
            self.cart_table.insertRow(r)
            self.cart_table.setRowHeight(r, 48)
            self.cart_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(p.id)))
            self.cart_table.setItem(r, 1, QtWidgets.QTableWidgetItem(p.name))
            self.cart_table.setItem(r, 2, QtWidgets.QTableWidgetItem(f"{p.price:.2f}"))

            # qty widget
            spin = QtWidgets.QSpinBox()
            spin.setMinimum(0)
            spin.setMaximum(1000000)
            spin.setValue(q)
            spin.valueChanged.connect(lambda val, pid=p.id: self.on_qty_changed(pid, val))
            self.cart_table.setCellWidget(r, 3, spin)

            # total cell (read-only)
            total_item = QtWidgets.QTableWidgetItem(f"{p.price * q:.2f}")
            total_item.setFlags(total_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.cart_table.setItem(r, 4, total_item)

            # delete button
            btn = QtWidgets.QPushButton('Delete')
            btn.clicked.connect(lambda _, pid=p.id: self.on_delete(pid))
            self.cart_table.setCellWidget(r, 5, btn)

        # compute total
        total = self.sales_controller.subtotal()
        self.lbl_total.setText(f'Total\n{total:,.2f}')

    def on_qty_changed(self, product_id: int, value: int):
        # update qty in sales_controller and refresh totals
        self.sales_controller.change_quantity(product_id, value)
        self.refresh_cart()

    def on_delete(self, product_id: int):
        self.sales_controller.remove_item(product_id)
        self.refresh_cart()

    def accept_sale(self):
        try:
            cid = self._selected_customer_id
            sale = self.sales_controller.complete_sale(customer_id=cid)
            cust_name = ''
            if cid:
                cust = self.customer_controller.get_by_id(cid)
                cust_name = f' for {cust.name}' if cust else ''
            QtWidgets.QMessageBox.information(
                self, tr('sale_complete'),
                tr('sale_complete_msg', id=sale['id'], cust=cust_name, total=sale['total'])
            )
            self.refresh_cart()
            self.load_speed()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))

    def save_as_debt(self):
        """Complete the sale and register the total as a debt on the selected customer."""
        cid = self._selected_customer_id
        if not cid:
            QtWidgets.QMessageBox.warning(self, tr('no_customer'), tr('no_customer_msg'))
            return
        if not self.sales_controller.cart:
            QtWidgets.QMessageBox.warning(self, tr('empty_cart'), tr('empty_cart_msg'))
            return
        total = self.sales_controller.total()
        cust = self.customer_controller.get_by_id(cid)
        reply = QtWidgets.QMessageBox.question(
            self, tr('save_as_debt'),
            tr('save_debt_q', total=total, name=cust.name, bal=cust.debt),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        try:
            # complete the sale (records stock reduction + sale record)
            sale = self.sales_controller.complete_sale(customer_id=cid)
            # register as debt entry
            self.customer_controller.add_debt(
                cid, total,
                note=f'Sale #{sale["id"]} — saved as debt'
            )
            QtWidgets.QMessageBox.information(
                self, tr('saved'),
                tr('saved_msg', id=sale['id'], total=total, name=cust.name)
            )
            self.refresh_cart()
            self.load_speed()
            self._load_customers()          # refresh debt badge
            self.cust_combo.setCurrentIndex(
                next((i for i in range(self.cust_combo.count())
                      if self.cust_combo.itemData(i) == cid), 0)
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))

    # ── Customer helpers ──────────────────────────────────────────────────────

    def _load_customers(self):
        self.cust_combo.blockSignals(True)
        prev_id = self._selected_customer_id
        self.cust_combo.clear()
        self.cust_combo.addItem(tr('walkin'), None)
        for c in self.customer_controller.get_all():
            label = f'{c.name}'
            if c.debt > 0:
                label += f'  (owes {c.debt:,.2f})'
            self.cust_combo.addItem(label, c.id)
        # restore previous selection
        if prev_id is not None:
            for i in range(self.cust_combo.count()):
                if self.cust_combo.itemData(i) == prev_id:
                    self.cust_combo.setCurrentIndex(i)
                    break
        self.cust_combo.blockSignals(False)
        self._on_customer_changed(self.cust_combo.currentIndex())

    def _on_customer_changed(self, index):
        cid = self.cust_combo.itemData(index)
        self._selected_customer_id = cid
        if cid:
            cust = self.customer_controller.get_by_id(cid)
            if cust and cust.debt > 0:
                self.cust_debt_lbl.setText(f'Outstanding debt: {cust.debt:,.2f}')
            else:
                self.cust_debt_lbl.setText('')
            self.btn_save_debt.setEnabled(True)
        else:
            self.cust_debt_lbl.setText('')
            self.btn_save_debt.setEnabled(False)
