from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QHeaderView,
    QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QMessageBox,
    QDoubleSpinBox, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import utils.icons as ic
from utils.lang import lang_manager, tr


class AdjustStockDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Adjust Stock — {product.name}')
        self.setMinimumWidth(360)

        layout = QFormLayout(self)
        layout.setSpacing(14)

        self.current_label = QLabel(str(product.quantity))
        layout.addRow('Current Quantity:', self.current_label)

        self.new_qty = QSpinBox()
        self.new_qty.setRange(0, 999999)
        self.new_qty.setValue(product.quantity)
        layout.addRow('New Quantity:', self.new_qty)

        self.min_level = QSpinBox()
        self.min_level.setRange(0, 999999)
        self.min_level.setValue(product.min_level)
        layout.addRow('Min Level:', self.min_level)

        self.cost_price = QDoubleSpinBox()
        self.cost_price.setRange(0, 9999999)
        self.cost_price.setDecimals(2)
        self.cost_price.setValue(product.cost_price)
        layout.addRow('Cost Price:', self.cost_price)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


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
        self.btn_refresh_inv.setText(tr('btn_refresh'))
        self.table.setHorizontalHeaderLabels([
            tr('col_id'), tr('col_name'), tr('col_barcode'), tr('col_category'),
            tr('col_qty'), tr('col_min_level'), tr('col_status'), tr('col_actions')
        ])
        self.refresh()   # re-populate status badges in current language

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # ── Top bar ───────────────────────────────────────────────────────────
        top = QHBoxLayout()
        title_ic = QLabel()
        title_ic.setPixmap(ic.ic_page_inventory().pixmap(ic.LG))
        title_ic.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.page_title = QLabel(tr('page_inventory'))
        self.page_title.setObjectName('page_title')
        self.page_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        top.addWidget(title_ic)
        top.addWidget(self.page_title)
        top.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr('search_inv'))
        self.search_box.addAction(ic.ic_search(), QLineEdit.LeadingPosition)
        self.search_box.setFixedWidth(320)
        self.search_box.textChanged.connect(self._on_search)
        top.addWidget(self.search_box)

        self.btn_refresh_inv = QPushButton(tr('btn_refresh'))
        self.btn_refresh_inv.setIcon(ic.ic_refresh())
        self.btn_refresh_inv.setIconSize(ic.SM)
        self.btn_refresh_inv.setObjectName('action_btn')
        self.btn_refresh_inv.clicked.connect(self.refresh)
        top.addWidget(self.btn_refresh_inv)

        root.addLayout(top)

        # ── Table ─────────────────────────────────────────────────────────────
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

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        hh.setSectionResizeMode(1, QHeaderView.Stretch)            # Name
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Barcode
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Category
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Qty
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Min
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Status
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Actions
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setStyleSheet('QHeaderView::section { background:#1a73e8; color:white; padding:6px; font-weight:600; }')

        root.addWidget(self.table)

        # ── Summary bar ───────────────────────────────────────────────────────
        self.summary_label = QLabel()
        self.summary_label.setObjectName('sub_title')
        root.addWidget(self.summary_label)

    # ── Data loading ─────────────────────────────────────────────────────────

    def refresh(self):
        term = self.search_box.text().strip()
        if term:
            products = self.pc.search(term)
        else:
            products = self.pc.get_all()
        self._populate(products)

    def _on_search(self):
        self.refresh()

    def _populate(self, products):
        self.table.setRowCount(0)
        low = out = 0
        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 48)

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

            # Status badge
            if p.quantity == 0:
                status_text, bg, fg = tr('out_of_stock'), '#fde8e8', '#c0392b'
                out += 1
            elif p.quantity <= p.min_level:
                status_text, bg, fg = tr('low_stock'), '#fff3cd', '#856404'
                low += 1
            else:
                status_text, bg, fg = tr('in_stock'), '#e8f5e9', '#1b5e20'

            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setBackground(QColor(bg))
            status_item.setForeground(QColor(fg))
            self.table.setItem(row, 6, status_item)

            # Actions — Adjust button
            btn = QPushButton(tr('btn_adjust'))
            btn.setIcon(ic.ic_adjust())
            btn.setIconSize(ic.SM)
            btn.setObjectName('adjust_btn')
            btn.setStyleSheet(
                'QPushButton { background:#1a73e8; color:white; border-radius:6px; padding:4px 12px; }'
                'QPushButton:hover { background:#1558b0; }'
            )
            product = p  # capture
            btn.clicked.connect(lambda _, pr=product: self._open_adjust(pr))
            self.table.setCellWidget(row, 7, btn)

        total = len(products)
        self.summary_label.setText(
            f'{tr("total_lbl")} <b>{total}</b>  |  '
            f'<span style="color:#c0392b">{tr("out_count")} <b>{out}</b></span>  |  '
            f'<span style="color:#856404">{tr("low_count")} <b>{low}</b></span>'
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
