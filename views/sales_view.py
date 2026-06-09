from PyQt5 import QtWidgets, QtCore
from controllers.product_controller import ProductController
from controllers.sales_controller import SalesController


class SalesView(QtWidgets.QWidget):
    def __init__(self, sales_controller: SalesController, product_controller: ProductController):
        super().__init__()
        self.sales_controller = sales_controller
        self.product_controller = product_controller

        layout = QtWidgets.QVBoxLayout(self)

        # barcode input - simulate scanner
        inp_layout = QtWidgets.QHBoxLayout()
        self.barcode_input = QtWidgets.QLineEdit()
        self.barcode_input.setPlaceholderText('Scan or type barcode and press Enter')
        try:
            self.barcode_input.setClearButtonEnabled(True)
        except Exception:
            pass
        self.qty_input = QtWidgets.QSpinBox()
        self.qty_input.setMinimum(1)
        self.qty_input.setMaximum(1000)
        inp_layout.addWidget(self.barcode_input)
        inp_layout.addWidget(QtWidgets.QLabel('Qty'))
        inp_layout.addWidget(self.qty_input)
        layout.addLayout(inp_layout)

        # cart table (add Actions column)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['ID', 'Name', 'Price', 'Qty', 'Total', 'Actions'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        btns = QtWidgets.QHBoxLayout()
        self.btn_remove = QtWidgets.QPushButton('Remove')
        self.btn_clear = QtWidgets.QPushButton('Clear')
        self.btn_complete = QtWidgets.QPushButton('Complete Sale')
        btns.addWidget(self.btn_remove)
        btns.addWidget(self.btn_clear)
        btns.addStretch()
        btns.addWidget(self.btn_complete)
        layout.addLayout(btns)

        # totals
        totals_layout = QtWidgets.QHBoxLayout()
        self.lbl_sub = QtWidgets.QLabel('Subtotal: 0.00')
        self.lbl_tax = QtWidgets.QLabel('Tax: 0.00')
        self.lbl_total = QtWidgets.QLabel('Total: 0.00')
        # make totals more prominent
        self.lbl_total.setStyleSheet('font-size:18px; font-weight:700; color:#0D47A1')
        self.lbl_sub.setStyleSheet('font-size:13px; color:#37474F')
        self.lbl_tax.setStyleSheet('font-size:13px; color:#37474F')
        totals_layout.addWidget(self.lbl_sub)
        totals_layout.addWidget(self.lbl_tax)
        totals_layout.addWidget(self.lbl_total)
        totals_layout.addStretch()
        layout.addLayout(totals_layout)

        # wire
        self.barcode_input.returnPressed.connect(self.on_scan)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_cart)
        self.btn_complete.clicked.connect(self.complete_sale)

        # keyboard shortcut to focus barcode
        QtWidgets.QShortcut(QtCore.Qt.Key_F4, self, activated=lambda: self.barcode_input.setFocus())

    def showEvent(self, ev):
        super().showEvent(ev)
        # autofocus barcode field when the sales view is shown
        QtCore.QTimer.singleShot(100, lambda: self.barcode_input.setFocus())

    def on_scan(self):
        code = self.barcode_input.text().strip()
        if not code:
            return
        qty = int(self.qty_input.value())
        try:
            self.sales_controller.add_barcode_to_cart(code, qty)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Scan error', str(e))
        self.barcode_input.clear()
        self.qty_input.setValue(1)
        self.refresh_cart()

    def refresh_cart(self):
        cart = self.sales_controller.cart
        self.table.setRowCount(0)
        for item in cart:
            p = item['product']
            q = item['quantity']
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(p.id)))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(p.name))
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(f"{p.price:.2f}"))

            # qty widget
            spin = QtWidgets.QSpinBox()
            spin.setMinimum(0)
            spin.setMaximum(1000000)
            spin.setValue(q)
            spin.valueChanged.connect(lambda val, pid=p.id: self.on_qty_changed(pid, val))
            self.table.setCellWidget(r, 3, spin)

            # total cell (read-only)
            total_item = QtWidgets.QTableWidgetItem(f"{p.price * q:.2f}")
            total_item.setFlags(total_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(r, 4, total_item)

            # actions (delete)
            btn = QtWidgets.QPushButton('Delete')
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda _, pid=p.id: self.remove_and_refresh(pid))
            self.table.setCellWidget(r, 5, btn)

        self.lbl_sub.setText(f"Subtotal: {self.sales_controller.subtotal():.2f}")
        tax_amt = self.sales_controller.tax(0.05)
        self.lbl_tax.setText(f"Tax: {tax_amt:.2f}")
        self.lbl_total.setText(f"Total: {self.sales_controller.total(0.05):.2f}")

    def remove_selected(self):
        sel = self.table.selectedItems()
        if not sel:
            return
        product_id = int(self.table.item(sel[0].row(), 0).text())
        self.sales_controller.remove_item(product_id)
        self.refresh_cart()

    def clear_cart(self):
        self.sales_controller.clear_cart()
        self.refresh_cart()

    def complete_sale(self):
        try:
            sale = self.sales_controller.complete_sale(0.05)
            QtWidgets.QMessageBox.information(self, 'Sale complete', f"Sale #{sale['id']} completed. Total {sale['total']:.2f}")
            self.refresh_cart()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
