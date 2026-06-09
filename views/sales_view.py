import configparser
import logging
import traceback

import qtawesome as qta
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QGridLayout, QTableWidget,
    QTableWidgetItem, QSpinBox, QComboBox, QHeaderView,
    QAbstractItemView, QSizePolicy, QMessageBox, QDoubleSpinBox,
)

from controllers.product_controller import ProductController
from controllers.sales_controller import SalesController
from controllers.customer_controller import CustomerController
from controllers import discount_controller
from utils.lang import tr, lang_manager
import utils.icons as ic

logger = logging.getLogger(__name__)

_BLUE   = '#1a73e8'
_GREEN  = '#16a34a'
_AMBER  = '#f59e0b'
_RED    = '#dc2626'
_DARK   = '#0f172a'
_SLATE  = '#475569'
_BORDER = '#e2e8f0'


def _tax_rate() -> float:
    cfg = configparser.RawConfigParser()
    cfg.read('config.ini')
    return cfg.getfloat('store', 'tax_rate', fallback=0.19)


def _currency() -> str:
    cfg = configparser.RawConfigParser()
    cfg.read('config.ini')
    return cfg.get('store', 'currency', fallback='DZD')


def _card_frame(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setStyleSheet(
        'QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }'
    )
    return f


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName('section_title')
    return lbl


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet('background:#e2e8f0; max-height:1px; border:none;')
    return f


# ─────────────────────────────────────────────────────────────────────────────
# Inline ± quantity stepper  (replaces the ugly QSpinBox in cart rows)
# ─────────────────────────────────────────────────────────────────────────────

class _QtyWidget(QWidget):
    changed = pyqtSignal(int)

    _BTN = (
        'QPushButton{background:#f1f5f9;border:1px solid #cbd5e1;'
        'color:#374151;font-size:17px;font-weight:700;border-radius:6px;}'
        'QPushButton:hover{background:#dde6f5;color:#1a73e8;border-color:#1a73e8;}'
        'QPushButton:pressed{background:#c7d7f4;}'
    )

    def __init__(self, value: int = 1, parent=None):
        super().__init__(parent)
        self._val = value
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(0)

        self._btn_m = QPushButton('−')
        self._btn_m.setFixedSize(30, 32)
        self._btn_m.setStyleSheet(self._BTN)
        self._btn_m.clicked.connect(self._dec)

        self._lbl = QLabel(str(value))
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setFixedSize(38, 32)
        self._lbl.setStyleSheet(
            'font-size:14px;font-weight:700;color:#1e293b;background:#fff;'
            'border-top:1px solid #cbd5e1;border-bottom:1px solid #cbd5e1;'
        )

        self._btn_p = QPushButton('+')
        self._btn_p.setFixedSize(30, 32)
        self._btn_p.setStyleSheet(self._BTN)
        self._btn_p.clicked.connect(self._inc)

        lay.addWidget(self._btn_m)
        lay.addWidget(self._lbl)
        lay.addWidget(self._btn_p)

    def value(self) -> int:
        return self._val

    def _inc(self):
        self._val += 1
        self._lbl.setText(str(self._val))
        self.changed.emit(self._val)

    def _dec(self):
        if self._val > 1:
            self._val -= 1
            self._lbl.setText(str(self._val))
            self.changed.emit(self._val)


# ─────────────────────────────────────────────────────────────────────────────
# Product card
# ─────────────────────────────────────────────────────────────────────────────

class _ProductCard(QFrame):
    clicked = pyqtSignal(object)

    _N = 'QFrame#ProductCard{background:#ffffff;border:1.5px solid #e2e8f0;border-radius:10px;}'
    _H = 'QFrame#ProductCard{background:#eff6ff;border:2px solid #1a73e8;border-radius:10px;}'

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setObjectName('ProductCard')
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(self._N)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 8)

        name_lbl = QLabel(product.name or '')
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(
            'font-size:15px;font-weight:700;color:#1e293b;background:transparent;'
        )

        lay.addWidget(name_lbl, 1)

    def enterEvent(self, e):   self.setStyleSheet(self._H)
    def leaveEvent(self, e):   self.setStyleSheet(self._N)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.product)
        super().mousePressEvent(e)


# ─────────────────────────────────────────────────────────────────────────────
# Main SalesView
# ─────────────────────────────────────────────────────────────────────────────

class SalesView(QWidget):
    def __init__(self, sales_controller: SalesController,
                 product_controller: ProductController):
        super().__init__()
        self.sales_controller    = sales_controller
        self.product_controller  = product_controller
        self.customer_controller = CustomerController()

        self._selected_customer_id              = None
        self._selected_discount: dict | None    = None
        self._payment_method                    = 'cash'
        self._all_products: list                = []
        self._held_cart: list                   = []

        self._build_ui()
        self._load_customers()
        self._load_discounts()
        self._load_products()
        self.refresh_cart()

        lang_manager.lang_changed.connect(self.retranslate_ui)

    # ─────────────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        # left (product browser) = 1 part  |  right (cart + checkout) = 3 parts
        root.addWidget(self._build_left(),  1)
        root.addWidget(self._build_right(), 3)

    # ── Left: compact product browser ─────────────────────────────────────────

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(
            'QFrame{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;}'
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # Barcode / search + qty
        barcode_row = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText('Scan / search…  (F2)')
        self.barcode_input.setFixedHeight(40)
        self.barcode_input.setClearButtonEnabled(True)
        self.barcode_input.setStyleSheet(
            'QLineEdit{border:1.5px solid #cbd5e1;border-radius:8px;'
            'padding:0 10px;font-size:13px;background:#fff;}'
            'QLineEdit:focus{border:1.5px solid #1a73e8;}'
        )
        self.barcode_input.returnPressed.connect(self._on_barcode)
        self.barcode_input.textChanged.connect(self._on_search)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)
        self.qty_spin.setFixedSize(60, 40)
        self.qty_spin.setStyleSheet(
            'QSpinBox{border:1.5px solid #cbd5e1;border-radius:8px;'
            'padding:0 4px;font-size:13px;background:#fff;}'
        )
        barcode_row.addWidget(self.barcode_input, 1)
        barcode_row.addWidget(QLabel('×'))
        barcode_row.addWidget(self.qty_spin)
        lay.addLayout(barcode_row)

        # Category chips
        cat_scroll = QScrollArea()
        cat_scroll.setFixedHeight(44)
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._cat_container = QWidget()
        self._cat_layout    = QHBoxLayout(self._cat_container)
        self._cat_layout.setContentsMargins(0, 0, 0, 0)
        self._cat_layout.setSpacing(6)
        self._cat_buttons: list[QPushButton] = []
        cat_scroll.setWidget(self._cat_container)
        lay.addWidget(cat_scroll)

        # Product grid
        prod_scroll = QScrollArea()
        prod_scroll.setWidgetResizable(True)
        prod_scroll.setFrameShape(QFrame.NoFrame)
        self._grid_container = QWidget()
        self._grid_layout    = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(6)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        prod_scroll.setWidget(self._grid_container)
        lay.addWidget(prod_scroll, 1)

        return panel

    # ── Right: customer card + cart table + checkout ───────────────────────────

    def _build_right(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet('QWidget{background:transparent;}')
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self._build_customer_card())
        lay.addWidget(self._build_cart(), 1)
        lay.addWidget(self._build_checkout())
        return panel

    # ── Customer card ──────────────────────────────────────────────────────────

    def _build_customer_card(self) -> QFrame:
        card = _card_frame()
        card.setFixedHeight(82)
        outer = QHBoxLayout(card)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(14)

        avatar = QLabel()
        avatar.setPixmap(qta.icon('fa5s.user-circle', color=_BLUE).pixmap(36, 36))
        avatar.setFixedSize(36, 36)
        outer.addWidget(avatar)

        col = QVBoxLayout()
        col.setSpacing(4)
        col.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        lbl = QLabel('Customer')
        lbl.setStyleSheet(
            f'font-size:10px;font-weight:700;color:{_SLATE};'
        )
        top.addWidget(lbl)
        top.addStretch()

        self.btn_reload_cust = QPushButton()
        self.btn_reload_cust.setIcon(ic.ic_refresh(color=_BLUE))
        self.btn_reload_cust.setIconSize(ic.SM)
        self.btn_reload_cust.setFixedSize(26, 26)
        self.btn_reload_cust.setToolTip('Reload customers')
        self.btn_reload_cust.setStyleSheet(
            'QPushButton{background:#e8f0fe;border-radius:6px;border:none;}'
            'QPushButton:hover{background:#c5d8fc;}'
        )
        self.btn_reload_cust.clicked.connect(self._load_customers)
        top.addWidget(self.btn_reload_cust)
        col.addLayout(top)

        self.cust_combo = QComboBox()
        self.cust_combo.setFixedHeight(34)
        self.cust_combo.setStyleSheet(
            'QComboBox{border:1.5px solid #e2e8f0;border-radius:8px;'
            'padding:0 10px;font-size:13px;background:#fff;}'
            'QComboBox:focus{border:1.5px solid #1a73e8;}'
            'QComboBox::drop-down{border:none;width:20px;}'
        )
        self.cust_combo.currentIndexChanged.connect(self._on_customer_changed)
        col.addWidget(self.cust_combo)
        outer.addLayout(col, 1)

        # Debt / loyalty badges
        stats = QVBoxLayout()
        stats.setSpacing(4)
        stats.setAlignment(Qt.AlignVCenter)

        self.cust_debt_lbl = QLabel('')
        self.cust_debt_lbl.setStyleSheet(
            f'background:#fee2e2;color:{_RED};border-radius:8px;'
            'padding:3px 10px;font-size:12px;font-weight:600;'
        )
        self.cust_debt_lbl.setVisible(False)

        self.cust_loyalty_lbl = QLabel('')
        self.cust_loyalty_lbl.setStyleSheet(
            f'background:#eff6ff;color:{_BLUE};border-radius:8px;'
            'padding:3px 10px;font-size:12px;font-weight:600;'
        )
        self.cust_loyalty_lbl.setVisible(False)

        stats.addWidget(self.cust_debt_lbl)
        stats.addWidget(self.cust_loyalty_lbl)
        outer.addLayout(stats)

        return card

    # ── Cart table ─────────────────────────────────────────────────────────────

    def _build_cart(self) -> QFrame:
        panel = _card_frame()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 12, 14, 10)
        lay.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        self.cart_title = _section_label(tr('cart'))
        self.cart_count_lbl = QLabel('0 items')
        self.cart_count_lbl.setStyleSheet(
            f'background:{_BLUE};color:#fff;border-radius:10px;'
            'padding:2px 10px;font-size:11px;font-weight:600;'
        )
        self.btn_clear = QPushButton('Clear')
        self.btn_clear.setObjectName('SecondaryButton')
        self.btn_clear.setFixedHeight(34)
        self.btn_clear.clicked.connect(self._clear_cart)
        hdr.addWidget(self.cart_title)
        hdr.addWidget(self.cart_count_lbl)
        hdr.addStretch()
        hdr.addWidget(self.btn_clear)
        lay.addLayout(hdr)

        # 5 columns: Product | Unit Price | Qty (±) | Total | ×
        self.cart_table = QTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(
            ['Product', 'Unit Price', 'Qty', 'Total', '']
        )
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setShowGrid(False)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setStyleSheet(
            'QTableWidget{border:none;background:#fff;outline:none;}'
            'QTableWidget::item{padding:0 10px;}'
            'QTableWidget::item:alternate{background:#f8fafc;}'
            'QTableWidget::item:selected{background:#eff6ff;color:#1e293b;}'
            'QHeaderView::section{background:#f1f5f9;border:none;'
            'padding:8px 10px;font-size:12px;font-weight:600;color:#64748b;'
            'border-bottom:1px solid #e2e8f0;}'
        )

        hh = self.cart_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(1, 108)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(2, 106)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(3, 108)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(4, 44)
        self.cart_table.verticalHeader().setDefaultSectionSize(50)

        lay.addWidget(self.cart_table, 1)
        return panel

    # ── Checkout panel (two-column horizontal) ─────────────────────────────────

    def _build_checkout(self) -> QFrame:
        panel = _card_frame()
        outer = QHBoxLayout(panel)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(20)

        # ── Left col: discount + totals breakdown ──────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(6)

        disc_row = QHBoxLayout()
        disc_row.addWidget(QLabel('Discount'))
        self.disc_combo = QComboBox()
        self.disc_combo.setFixedHeight(32)
        self.disc_combo.setStyleSheet(
            'QComboBox{border:1.5px solid #e2e8f0;border-radius:8px;'
            'padding:0 8px;font-size:12px;background:#fff;}'
            'QComboBox::drop-down{border:none;width:18px;}'
        )
        self.disc_combo.currentIndexChanged.connect(self._on_discount_changed)
        disc_row.addWidget(self.disc_combo, 1)
        left.addLayout(disc_row)

        coupon_row = QHBoxLayout()
        coupon_row.setSpacing(6)
        self.coupon_input = QLineEdit()
        self.coupon_input.setPlaceholderText('Coupon code…')
        self.coupon_input.setFixedHeight(32)
        self.coupon_input.setStyleSheet(
            'QLineEdit{border:1.5px solid #cbd5e1;border-radius:8px;'
            'padding:0 8px;font-size:12px;background:#fff;}'
            'QLineEdit:focus{border:1.5px solid #1a73e8;}'
        )
        apply_btn = QPushButton('Apply')
        apply_btn.setFixedHeight(32)
        apply_btn.setObjectName('SecondaryButton')
        apply_btn.clicked.connect(self._apply_coupon)
        coupon_row.addWidget(self.coupon_input, 1)
        coupon_row.addWidget(apply_btn)
        left.addLayout(coupon_row)

        left.addWidget(_divider())

        def _trow(label: str, bold: bool = False):
            row = QHBoxLayout()
            fs = '13px' if not bold else '15px'
            fw = '600'  if not bold else '800'
            lb = QLabel(label)
            lb.setStyleSheet(f'color:{_SLATE};font-size:{fs};')
            vl = QLabel('0.00')
            vl.setStyleSheet(f'color:{_DARK};font-size:{fs};font-weight:{fw};')
            vl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(lb)
            row.addStretch()
            row.addWidget(vl)
            return row, vl

        sub_row,   self.lbl_sub  = _trow('Subtotal')
        disc_row2, self.lbl_disc = _trow('Discount')
        tax_row,   self.lbl_tax  = _trow('Tax')
        for r in (sub_row, disc_row2, tax_row):
            left.addLayout(r)

        outer.addLayout(left, 1)

        # Vertical separator
        vdiv = QFrame()
        vdiv.setFrameShape(QFrame.VLine)
        vdiv.setStyleSheet('background:#e2e8f0;max-width:1px;border:none;')
        outer.addWidget(vdiv)

        # ── Right col: total + payment + buttons ───────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        self.lbl_total = QLabel('0.00')
        self.lbl_total.setAlignment(Qt.AlignCenter)
        self.lbl_total.setFixedHeight(60)
        self.lbl_total.setStyleSheet(
            f'font-size:30px;font-weight:900;color:#ffffff;'
            f'background:{_BLUE};border-radius:12px;'
        )
        right.addWidget(self.lbl_total)

        # Payment method
        pm_row = QHBoxLayout()
        pm_row.setSpacing(6)
        self._pay_btns: dict[str, QPushButton] = {}
        for key, label, color in [
            ('cash',    'Cash',    _GREEN),
            ('card',    'Card',    _BLUE),
            ('partial', 'Partial', _AMBER),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCheckable(True)
            btn.setStyleSheet(
                f'QPushButton{{border:1.5px solid {color};color:{color};'
                'background:#fff;border-radius:8px;font-size:12px;font-weight:600;}}'
                f'QPushButton:checked{{background:{color};color:#fff;}}'
            )
            btn.clicked.connect(lambda _, k=key: self._set_payment(k))
            self._pay_btns[key] = btn
            pm_row.addWidget(btn)
        self._pay_btns['cash'].setChecked(True)
        right.addLayout(pm_row)

        # Amount paid + change
        paid_row = QHBoxLayout()
        paid_row.setSpacing(8)
        paid_lbl = QLabel('Paid')
        paid_lbl.setStyleSheet(f'color:{_SLATE};font-size:12px;')
        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 99_999_999)
        self.paid_input.setDecimals(2)
        self.paid_input.setFixedHeight(34)
        self.paid_input.setStyleSheet(
            'QDoubleSpinBox{border:1.5px solid #cbd5e1;border-radius:8px;'
            'padding:0 6px;font-size:13px;}'
        )
        self.paid_input.valueChanged.connect(self._update_change)
        self.lbl_change = QLabel('← 0.00')
        self.lbl_change.setStyleSheet(f'font-size:13px;font-weight:700;color:{_GREEN};')
        paid_row.addWidget(paid_lbl)
        paid_row.addWidget(self.paid_input, 1)
        paid_row.addWidget(self.lbl_change)
        right.addLayout(paid_row)

        self.btn_complete = QPushButton('  Complete Sale  (F10)')
        self.btn_complete.setIcon(qta.icon('fa5s.check-circle', color='#fff'))
        self.btn_complete.setIconSize(QtCore.QSize(18, 18))
        self.btn_complete.setFixedHeight(46)
        self.btn_complete.setStyleSheet(
            f'QPushButton{{background:{_GREEN};color:#fff;border-radius:12px;'
            'font-size:15px;font-weight:700;border:none;}}'
            f'QPushButton:hover{{background:#15803d;}}'
            'QPushButton:disabled{background:#94a3b8;}'
        )
        self.btn_complete.clicked.connect(self._complete_sale)
        right.addWidget(self.btn_complete)

        aux_row = QHBoxLayout()
        aux_row.setSpacing(6)
        self.btn_hold = QPushButton('Hold')
        self.btn_hold.setIcon(qta.icon('fa5s.pause-circle', color=_AMBER))
        self.btn_hold.setIconSize(QtCore.QSize(14, 14))
        self.btn_hold.setFixedHeight(34)
        self.btn_hold.setObjectName('SecondaryButton')
        self.btn_hold.clicked.connect(self._hold_sale)

        self.btn_new = QPushButton('New Sale')
        self.btn_new.setIcon(qta.icon('fa5s.plus-circle', color=_BLUE))
        self.btn_new.setIconSize(QtCore.QSize(14, 14))
        self.btn_new.setFixedHeight(34)
        self.btn_new.setObjectName('SecondaryButton')
        self.btn_new.clicked.connect(self._new_sale)

        aux_row.addWidget(self.btn_hold)
        aux_row.addWidget(self.btn_new)
        right.addLayout(aux_row)

        self.btn_resume = QPushButton('Resume Held Sale')
        self.btn_resume.setFixedHeight(32)
        self.btn_resume.setVisible(False)
        self.btn_resume.setStyleSheet(
            f'QPushButton{{background:#fef3c7;color:#92400e;border:1.5px solid {_AMBER};'
            'border-radius:8px;font-size:12px;font-weight:600;}}'
        )
        self.btn_resume.clicked.connect(self._resume_held)
        right.addWidget(self.btn_resume)

        outer.addLayout(right, 1)
        return panel

    # ─────────────────────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────────────────────

    def _load_products(self, category: str | None = None):
        self._all_products = self.product_controller.get_all()
        self._build_category_chips()
        self._fill_grid(
            self._all_products if category is None
            else [p for p in self._all_products if (p.category or '') == category]
        )

    def _build_category_chips(self):
        while self._cat_layout.count():
            w = self._cat_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._cat_buttons.clear()

        categories = ['All'] + sorted({
            p.category for p in self._all_products if p.category
        })
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f'QPushButton{{border:1.5px solid {_BLUE};color:{_BLUE};'
                'background:#fff;border-radius:14px;padding:0 12px;font-size:11px;}}'
                f'QPushButton:checked{{background:{_BLUE};color:#fff;}}'
            )
            btn.clicked.connect(lambda _, c=cat: self._on_category(c))
            self._cat_layout.addWidget(btn)
            self._cat_buttons.append(btn)
        self._cat_layout.addStretch()
        if self._cat_buttons:
            self._cat_buttons[0].setChecked(True)

    def _on_category(self, category: str):
        for btn in self._cat_buttons:
            btn.setChecked(btn.text() == category)
        products = (self._all_products if category == 'All'
                    else [p for p in self._all_products if (p.category or '') == category])
        self.barcode_input.clear()
        self._fill_grid(products)

    def _fill_grid(self, products):
        while self._grid_layout.count():
            w = self._grid_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        COLS = 2
        for idx, p in enumerate(products):
            card = _ProductCard(p)
            card.clicked.connect(self._add_product)
            self._grid_layout.addWidget(card, idx // COLS, idx % COLS)
        if not products:
            empty = QLabel('No products found')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f'color:{_SLATE};font-size:13px;')
            self._grid_layout.addWidget(empty, 0, 0, 1, COLS)

    def _load_customers(self):
        self.cust_combo.blockSignals(True)
        prev = self._selected_customer_id
        self.cust_combo.clear()
        self.cust_combo.addItem('Walk-in customer', None)
        for c in self.customer_controller.get_all():
            label = c.name
            if getattr(c, 'debt', 0) > 0:
                label += f'  (owes {c.debt:,.2f})'
            self.cust_combo.addItem(label, c.id)
        if prev is not None:
            for i in range(self.cust_combo.count()):
                if self.cust_combo.itemData(i) == prev:
                    self.cust_combo.setCurrentIndex(i)
                    break
        self.cust_combo.blockSignals(False)
        self._on_customer_changed(self.cust_combo.currentIndex())

    def _load_discounts(self):
        self.disc_combo.blockSignals(True)
        self.disc_combo.clear()
        self.disc_combo.addItem('No discount', None)
        ok, data = discount_controller.get_all(active_only=True)
        if ok:
            for d in data:
                label = f'{d["name"]}  ({d["type"]} {d["value"]})'
                self.disc_combo.addItem(label, d)
        self.disc_combo.blockSignals(False)

    # ─────────────────────────────────────────────────────────────────────────
    # Cart management
    # ─────────────────────────────────────────────────────────────────────────

    def _add_product(self, product):
        qty = self.qty_spin.value()
        try:
            self.sales_controller.add_barcode_to_cart(product.barcode, qty)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
            return
        self.qty_spin.setValue(1)
        self.barcode_input.clear()
        self.refresh_cart()

    def _on_barcode(self):
        code = self.barcode_input.text().strip()
        if not code:
            return
        qty = self.qty_spin.value()
        try:
            self.sales_controller.add_barcode_to_cart(code, qty)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
            return
        self.barcode_input.clear()
        self.qty_spin.setValue(1)
        self.refresh_cart()

    def _on_search(self, text: str):
        term = text.strip()
        if not term:
            self._fill_grid(self._all_products)
            return
        results = self.product_controller.search(term)
        self._fill_grid(results)
        for btn in self._cat_buttons:
            btn.setChecked(btn.text() == 'All')

    def _clear_cart(self):
        for item in list(self.sales_controller.cart):
            self.sales_controller.remove_item(item['product'].id)
        self._selected_discount = None
        self.disc_combo.setCurrentIndex(0)
        self.coupon_input.clear()
        self.refresh_cart()

    def _new_sale(self):
        self._clear_cart()
        self.cust_combo.setCurrentIndex(0)

    # ─────────────────────────────────────────────────────────────────────────
    # Hold / Resume
    # ─────────────────────────────────────────────────────────────────────────

    def _hold_sale(self):
        if not self.sales_controller.cart:
            return
        self._held_cart = [(item['product'], item['quantity'])
                           for item in self.sales_controller.cart]
        self._clear_cart()
        self.btn_resume.setVisible(True)
        self.btn_resume.setText(f'Resume ({len(self._held_cart)} items)')

    def _resume_held(self):
        self._clear_cart()
        for product, qty in self._held_cart:
            try:
                self.sales_controller.add_barcode_to_cart(product.barcode, qty)
            except Exception:
                pass
        self._held_cart = []
        self.btn_resume.setVisible(False)
        self.refresh_cart()

    # ─────────────────────────────────────────────────────────────────────────
    # Totals & payment
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_totals(self) -> dict:
        tax_rate    = _tax_rate()
        subtotal    = self.sales_controller.subtotal()
        disc_amount = 0.0
        if self._selected_discount:
            disc_amount = discount_controller.apply_discount(
                self._selected_discount, subtotal
            )
        taxable = max(subtotal - disc_amount, 0)
        tax     = round(taxable * tax_rate, 2)
        total   = round(taxable + tax, 2)
        return {
            'subtotal':    subtotal,
            'disc_amount': disc_amount,
            'tax':         tax,
            'total':       total,
            'tax_rate':    tax_rate,
        }

    def refresh_cart(self):
        cart = self.sales_controller.cart
        self.cart_table.setRowCount(0)

        for item in cart:
            p   = item['product']
            qty = item['quantity']
            r   = self.cart_table.rowCount()
            self.cart_table.insertRow(r)
            self.cart_table.setRowHeight(r, 50)

            # Col 0: Product name
            name_item = QTableWidgetItem(p.name)
            name_item.setData(Qt.UserRole, p.id)
            self.cart_table.setItem(r, 0, name_item)

            # Col 1: Unit price
            price = float(getattr(p, 'price', 0) or 0)
            price_item = QTableWidgetItem(f'{price:,.2f}')
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.cart_table.setItem(r, 1, price_item)

            # Col 2: ± qty stepper
            qty_w = _QtyWidget(qty)
            qty_w.changed.connect(
                lambda val, pid=p.id: self._on_qty_change(pid, val)
            )
            self.cart_table.setCellWidget(r, 2, qty_w)

            # Col 3: Row subtotal
            sub_item = QTableWidgetItem(f'{price * qty:,.2f}')
            sub_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.cart_table.setItem(r, 3, sub_item)

            # Col 4: Delete button
            del_btn = QPushButton()
            del_btn.setIcon(qta.icon('fa5s.times', color=_RED))
            del_btn.setIconSize(QtCore.QSize(13, 13))
            del_btn.setFixedSize(36, 36)
            del_btn.setStyleSheet(
                'QPushButton{background:#fff0f0;border:none;border-radius:6px;}'
                'QPushButton:hover{background:#fee2e2;}'
            )
            del_btn.clicked.connect(
                lambda _, pid=p.id: self._on_delete(pid)
            )
            self.cart_table.setCellWidget(r, 4, del_btn)

        # Count badge
        n = len(cart)
        self.cart_count_lbl.setText(f'{n} item{"s" if n != 1 else ""}')

        # Totals
        t   = self._compute_totals()
        cur = _currency()
        self.lbl_sub.setText(f'{t["subtotal"]:,.2f} {cur}')
        self.lbl_disc.setText(f'-{t["disc_amount"]:,.2f} {cur}')
        self.lbl_tax.setText(f'{t["tax"]:,.2f} {cur}  ({int(t["tax_rate"]*100)}%)')
        self.lbl_total.setText(f'{t["total"]:,.2f}')

        if self._payment_method == 'cash':
            self.paid_input.blockSignals(True)
            self.paid_input.setValue(t['total'])
            self.paid_input.blockSignals(False)

        self._update_change()
        self.btn_complete.setEnabled(n > 0)

    def _update_change(self):
        t      = self._compute_totals()
        paid   = self.paid_input.value()
        change = max(paid - t['total'], 0)
        cur    = _currency()
        self.lbl_change.setText(f'← {change:,.2f} {cur}')
        color = _GREEN if change >= 0 else _RED
        self.lbl_change.setStyleSheet(f'font-size:13px;font-weight:700;color:{color};')

    # ─────────────────────────────────────────────────────────────────────────
    # Event handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _on_qty_change(self, product_id: int, value: int):
        try:
            self.sales_controller.change_quantity(product_id, value)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
        self.refresh_cart()

    def _on_delete(self, product_id: int):
        self.sales_controller.remove_item(product_id)
        self.refresh_cart()

    def _on_customer_changed(self, index: int):
        cid = self.cust_combo.itemData(index)
        self._selected_customer_id = cid
        if cid:
            cust = self.customer_controller.get_by_id(cid)
            debt = getattr(cust, 'debt', 0) if cust else 0
            pts  = getattr(cust, 'loyalty_points', 0) if cust else 0
            if debt:
                self.cust_debt_lbl.setText(f'Debt: {debt:,.2f}')
                self.cust_debt_lbl.setVisible(True)
            else:
                self.cust_debt_lbl.setVisible(False)
            if pts:
                self.cust_loyalty_lbl.setText(f'★ {pts} pts')
                self.cust_loyalty_lbl.setVisible(True)
            else:
                self.cust_loyalty_lbl.setVisible(False)
        else:
            self.cust_debt_lbl.setVisible(False)
            self.cust_loyalty_lbl.setVisible(False)

    def _on_discount_changed(self, index: int):
        self._selected_discount = self.disc_combo.itemData(index)
        self.refresh_cart()

    def _apply_coupon(self):
        code = self.coupon_input.text().strip()
        if not code:
            return
        ok, result = discount_controller.get_by_coupon(code)
        if ok:
            self._selected_discount = result
            self.coupon_input.setStyleSheet(
                'QLineEdit{border:1.5px solid #16a34a;border-radius:8px;'
                'padding:0 8px;font-size:12px;background:#f0fdf4;}'
            )
            self.refresh_cart()
        else:
            self.coupon_input.setStyleSheet(
                'QLineEdit{border:1.5px solid #dc2626;border-radius:8px;'
                'padding:0 8px;font-size:12px;background:#fff;}'
            )
            QMessageBox.warning(self, 'Coupon', result)

    def _set_payment(self, method: str):
        self._payment_method = method
        for k, btn in self._pay_btns.items():
            btn.setChecked(k == method)
        t = self._compute_totals()
        if method == 'cash':
            self.paid_input.setValue(t['total'])
        self._update_change()

    # ─────────────────────────────────────────────────────────────────────────
    # Complete sale
    # ─────────────────────────────────────────────────────────────────────────

    def _complete_sale(self):
        if not self.sales_controller.cart:
            QMessageBox.warning(self, 'Empty cart', 'Add items before completing a sale.')
            return
        try:
            t    = self._compute_totals()
            paid = self.paid_input.value()

            if self._payment_method != 'partial' and paid < t['total']:
                QMessageBox.warning(
                    self, 'Insufficient payment',
                    f'Amount paid ({paid:,.2f}) is less than total ({t["total"]:,.2f}).'
                )
                return

            sale = self.sales_controller.complete_sale(
                customer_id=self._selected_customer_id
            )

            from utils.auth import get_session
            sess = get_session()
            sale['cashier_name']   = (sess or {}).get('full_name') or (sess or {}).get('username', '')
            sale['total_amount']   = t['total']
            sale['discount_value'] = t['disc_amount']
            sale['tax_amount']     = t['tax']
            sale['amount_paid']    = paid
            sale['amount_change']  = max(paid - t['total'], 0)
            sale['payment_method'] = self._payment_method

            self._clear_cart()
            self.cust_combo.setCurrentIndex(0)
            self._load_products()

            try:
                from views.receipt_dialog import ReceiptDialog
                dlg = ReceiptDialog(sale, parent=self)
                dlg.exec_()
            except Exception:
                QMessageBox.information(
                    self, 'Sale Complete',
                    f'Sale #{sale.get("id", "")} completed.\n'
                    f'Total: {t["total"]:,.2f}  Change: {sale["amount_change"]:,.2f}'
                )
        except Exception:
            logger.error('SalesView._complete_sale\n%s', traceback.format_exc())
            QMessageBox.warning(self, 'Error', 'Could not complete the sale.')

    # ─────────────────────────────────────────────────────────────────────────
    # Qt events
    # ─────────────────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(80, lambda: self.barcode_input.setFocus())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F10:
            self._complete_sale()
        elif event.key() == Qt.Key_F2:
            self.barcode_input.setFocus()
        elif event.key() == Qt.Key_F5:
            self._new_sale()
        else:
            super().keyPressEvent(event)

    def retranslate_ui(self, lang=None):
        self.cart_title.setText(tr('cart'))
