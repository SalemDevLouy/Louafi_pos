from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QHeaderView,
    QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox, QSizePolicy, QFrame, QSpacerItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import utils.icons as ic
from utils.lang import lang_manager, tr


class AdjustStockDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Adjust Stock — {product.name}')
        self.setFixedWidth(380)

        outer = QVBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QLabel(f"Adjust: {product.name}")
        header.setObjectName("section_title")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.current_label = QLabel(str(product.quantity))
        self.current_label.setStyleSheet("font-size:16px; font-weight:700; color:#6d28d9;")
        form.addRow('Current Qty:', self.current_label)

        self.new_qty = QSpinBox()
        self.new_qty.setRange(0, 999999)
        self.new_qty.setValue(product.quantity)

        self.min_level = QSpinBox()
        self.min_level.setRange(0, 999999)
        self.min_level.setValue(product.min_level)

        self.cost_price = QDoubleSpinBox()
        self.cost_price.setRange(0, 9999999)
        self.cost_price.setDecimals(2)
        self.cost_price.setPrefix("DA ")
        self.cost_price.setValue(product.cost_price)

        form.addRow('New Quantity:', self.new_qty)
        form.addRow('Min Level:', self.min_level)
        form.addRow('Cost Price:', self.cost_price)
        outer.addLayout(form)

        outer.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Save")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setFixedWidth(100)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        outer.addLayout(btn_row)


class InventoryView(QWidget):
    def __init__(self, product_controller, parent=None):
        super().__init__(parent)
        self.pc = product_controller
        self._build_ui()
        self.refresh()
        lang_manager.lang_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, lang=None):
        self.page_title.setText(tr('page_inventory'))
        self.search_box.setPlaceholderText(tr('search_inv'))
        self.btn_refresh_inv.setText("Refresh")
        self.table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_barcode'), tr('col_category'),
            tr('col_qty'), tr('col_min_level'), tr('col_status'), tr('col_actions')
        ])
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Page header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.page_title = QLabel(tr('page_inventory'))
        self.page_title.setObjectName('page_title')
        subtitle = QLabel("Stock levels, adjustments, and low-stock alerts")
        subtitle.setObjectName("sub_title")
        title_col.addWidget(self.page_title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr('search_inv'))
        self.search_box.setFixedWidth(280)
        self.search_box.setFixedHeight(38)
        self.search_box.textChanged.connect(self._on_search)
        header_row.addWidget(self.search_box)

        self.btn_refresh_inv = QPushButton("Refresh")
        self.btn_refresh_inv.setObjectName("SecondaryButton")
        self.btn_refresh_inv.setFixedHeight(38)
        self.btn_refresh_inv.clicked.connect(self.refresh)
        header_row.addWidget(self.btn_refresh_inv)

        root.addLayout(header_row)

        # Table card
        table_card = QFrame()
        table_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }"
        )
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_barcode'), tr('col_category'),
            tr('col_qty'), tr('col_min_level'), tr('col_status'), tr('col_actions')
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        hh.setDefaultAlignment(Qt.AlignCenter)

        tc_layout.addWidget(self.table)
        root.addWidget(table_card, stretch=1)

        # Summary bar
        self.summary_label = QLabel()
        self.summary_label.setObjectName('sub_title')
        root.addWidget(self.summary_label)

    def refresh(self):
        term = self.search_box.text().strip()
        products = self.pc.search(term) if term else self.pc.get_all()
        self._populate(products)

    def _on_search(self):
        self.refresh()

    def _populate(self, products):
        self.table.setRowCount(0)
        low = out = 0
        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 44)

            def _item(text, align=Qt.AlignCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                return it

            self.table.setItem(row, 0, _item(p.id))
            self.table.setItem(row, 1, _item(p.name, Qt.AlignLeft | Qt.AlignVCenter))
            self.table.setItem(row, 2, _item(p.barcode or ''))
            self.table.setItem(row, 3, _item(p.category or ''))
            self.table.setItem(row, 4, _item(p.quantity))
            self.table.setItem(row, 5, _item(p.min_level))

            if p.quantity == 0:
                status_text, bg, fg = tr('out_of_stock'), '#fde8e8', '#b91c1c'
                out += 1
            elif p.quantity <= p.min_level:
                status_text, bg, fg = tr('low_stock'), '#fef3c7', '#92400e'
                low += 1
            else:
                status_text, bg, fg = tr('in_stock'), '#dcfce7', '#15803d'

            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setBackground(QColor(bg))
            status_item.setForeground(QColor(fg))
            self.table.setItem(row, 6, status_item)

            btn = QPushButton("Adjust")
            btn.setStyleSheet(
                'QPushButton { background:#6d28d9; color:white; border-radius:6px; '
                'padding:4px 14px; font-size:13px; font-weight:600; }'
                'QPushButton:hover { background:#7c3aed; }'
            )
            product = p
            btn.clicked.connect(lambda _, pr=product: self._open_adjust(pr))
            self.table.setCellWidget(row, 7, btn)

        total = len(products)
        self.summary_label.setText(
            f'Total: <b>{total}</b>  |  '
            f'<span style="color:#b91c1c">Out of stock: <b>{out}</b></span>  |  '
            f'<span style="color:#92400e">Low stock: <b>{low}</b></span>'
        )
        self.summary_label.setTextFormat(Qt.RichText)

    def _open_adjust(self, product):
        dlg = AdjustStockDialog(product, self)
        if dlg.exec_() == QDialog.Accepted:
            new_qty = dlg.new_qty.value()
            new_min = dlg.min_level.value()
            new_cost = dlg.cost_price.value()
            try:
                self.pc.update_product(
                    product.id,
                    quantity=new_qty,
                    min_level=new_min,
                    cost_price=new_cost,
                )
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, 'Error', str(e))
