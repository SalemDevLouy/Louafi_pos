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
    # Add subtle shadow for depth
    from PyQt5.QtWidgets import QGraphicsDropShadowEffect
    from PyQt5.QtGui import QColor
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(12)
    shadow.setColor(QColor(15, 23, 42, 25))  # #0f172a with ~10% opacity
    shadow.setOffset(0, 2)
    f.setGraphicsEffect(shadow)
    return f


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName('section_title')
    lbl.setStyleSheet('font-size:18px;font-weight:800;color:#1e293b;')
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
        'QPushButton{background:#f1f5f9;border:1.5px solid #cbd5e1;'
        'color:#374151;font-size:16px;font-weight:800;border-radius:8px;}'
        'QPushButton:hover{background:#dde6f5;color:#1a73e8;border-color:#1a73e8;}'
        'QPushButton:pressed{background:#c7d7f4;}'
    )

    def __init__(self, value: int = 1, parent=None):
        super().__init__(parent)
        self._val = value
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)

        self._btn_m = QPushButton('−')
        self._btn_m.setFixedSize(24, 24)
        self._btn_m.setStyleSheet(self._BTN)
        self._btn_m.clicked.connect(self._dec)

        self._lbl = QLabel(str(value))
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setFixedSize(30, 24)
        self._lbl.setStyleSheet(
            'font-size:13px;font-weight:800;color:#1e293b;background:#fff;'
            'border-top:1.5px solid #cbd5e1;border-bottom:1.5px solid #cbd5e1;'
        )

        self._btn_p = QPushButton('+')
        self._btn_p.setFixedSize(24, 24)
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
# Category filter bar (touch-friendly chips)
# ─────────────────────────────────────────────────────────────────────────────

class _CategoryBar(QWidget):
    changed = pyqtSignal(str)   # '' = All

    _CHIP = (
        'QPushButton#Chip{background:#ffffff;border:1.5px solid #dbe3ef;'
        'border-radius:16px;padding:4px 16px;color:#475569;'
        'font-size:13px;font-weight:600;}'
        'QPushButton#Chip:hover{background:#f1f5f9;border-color:#cbd5e1;}'
        'QPushButton#Chip:checked{background:#1a73e8;color:#ffffff;'
        'border:1.5px solid #1a73e8;}'
    )

    def __init__(self, categories=None, parent=None):
        super().__init__(parent)
        self._chips: list = []
        self._active = ''
        self.setFixedHeight(46)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(
            'QScrollArea{background:transparent;border:none;}'
        )
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._lay = QHBoxLayout(self._container)
        self._lay.setSpacing(8)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._scroll.setWidget(self._container)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._scroll)

        if categories:
            self.set_categories(categories)

    def active_category(self) -> str:
        return self._active

    def set_categories(self, categories):
        """Rebuild chips from raw product categories (no ``All`` needed)."""
        names = ['All'] + list(
            dict.fromkeys(
                str(c).strip() for c in (categories or [])
                if c and str(c).strip()
            )
        )
        self._clear_chips()
        for name in names:
            btn = QPushButton(name)
            btn.setObjectName('Chip')
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._CHIP)
            btn.setChecked((name == 'All' and not self._active)
                           or name == self._active)
            btn.clicked.connect(lambda _, n=name: self._select(n))
            self._lay.addWidget(btn)
            self._chips.append(btn)
        self._lay.addStretch(1)

    def _clear_chips(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._chips.clear()

    def _select(self, name: str):
        self._active = '' if name == 'All' else name
        for btn in self._chips:
            btn.setChecked(btn.text() == name)
        self.changed.emit(self._active)


# ─────────────────────────────────────────────────────────────────────────────
# Product card
# ─────────────────────────────────────────────────────────────────────────────

class _ProductCard(QFrame):
    clicked = pyqtSignal(object)

    _N = (
        'QFrame#ProductCard{background:#ffffff;border:2px solid #e2e8f0;'
        'border-radius:14px;}'
    )
    _H = (
        'QFrame#ProductCard{background:#eff6ff;border:2.5px solid #1a73e8;'
        'border-radius:14px;}'
    )
    _D = (
        'QFrame#ProductCard{background:#f8fafc;border:1.5px dashed #cbd5e1;'
        'border-radius:14px;}'
    )

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self._qty    = int(getattr(product, 'quantity', 0) or 0)
        self._min    = int(getattr(product, 'min_level', 5) or 5)
        self._in_cart = 0
        self._addable = self._qty > 0

        self.setObjectName('ProductCard')
        self.setMinimumHeight(86)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(self._D if not self._addable else self._N)

        # Add subtle shadow
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        from PyQt5.QtGui import QColor
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(8)
        self._shadow.setColor(QColor(15, 23, 42, 20))
        self._shadow.setOffset(0, 1)
        self.setGraphicsEffect(self._shadow)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(8)

        # Product name (the "button")
        self._name_lbl = QLabel(product.name or '')
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._name_lbl)

        # Stock status circle (green = in stock · amber = low · red = out)
        self._dot = QLabel()
        self._dot.setFixedSize(14, 14)
        self._dot.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._dot)

        self._apply_state()

    # ── public API ──────────────────────────────────────────────────────────
    def set_in_cart(self, qty: int):
        self._in_cart = max(int(qty or 0), 0)
        self._apply_state()

    # ── internals ───────────────────────────────────────────────────────────
    def _apply_state(self):
        remaining = self._qty - self._in_cart
        self._addable = self._qty > 0 and remaining > 0

        if self._qty <= 0:
            dot, card, name_c = '#ef4444', self._D, '#94a3b8'   # red — out of stock
        elif remaining <= 0:
            dot, card, name_c = '#f59e0b', self._N, '#1e293b'   # amber — all in cart
        else:
            dot = '#22c55e' if remaining > self._min else '#f59e0b'
            card, name_c = self._N, '#1e293b'

        self.setStyleSheet(card)
        self.setCursor(
            Qt.PointingHandCursor if self._addable else Qt.ForbiddenCursor
        )

        self._dot.setStyleSheet(
            f'background:{dot};border-radius:7px;border:none;'
        )
        self._name_lbl.setStyleSheet(
            f'font-size:14px;font-weight:700;color:{name_c};background:transparent;'
        )

    def enterEvent(self, e):
        if self._addable:
            self.setStyleSheet(self._H)
            self._shadow.setBlurRadius(16)
            self._shadow.setOffset(0, 4)

    def leaveEvent(self, e):
        if self._addable:
            self.setStyleSheet(self._N)
            self._shadow.setBlurRadius(8)
            self._shadow.setOffset(0, 1)

    def mousePressEvent(self, e):
        if self._addable and e.button() == Qt.LeftButton:
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
        self._grid_cards: dict                  = {}
        self._search_term                       = ''
        self._active_category                   = ''

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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)
        # left (products & search) | middle (customer & cart) | right (checkout)
        root.addWidget(self._build_left(),   1)
        root.addWidget(self._build_middle(), 2)
        root.addWidget(self._build_right(),  1)

    # ── Left: compact product browser ─────────────────────────────────────────

    def _build_left(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(
            'QFrame{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;}'
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Barcode / search + qty
        barcode_row = QHBoxLayout()
        barcode_row.setSpacing(10)
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText('Scan / search…  (F2)')
        self.barcode_input.setFixedHeight(48)
        self.barcode_input.setClearButtonEnabled(True)
        self.barcode_input.setStyleSheet(
            'QLineEdit{border:2px solid #cbd5e1;border-radius:10px;'
            'padding:0 14px;font-size:15px;background:#fff;}'
            'QLineEdit:focus{border:2px solid #1a73e8;background:#f0f9ff;}'
        )
        self.barcode_input.returnPressed.connect(self._on_barcode)
        self.barcode_input.textChanged.connect(self._on_search)

        search_icon = QLabel()
        search_icon.setFixedSize(20, 20)
        search_icon.setPixmap(qta.icon('fa5s.search', color='#94a3b8').pixmap(18, 18))
        barcode_row.addWidget(search_icon)
        barcode_row.addWidget(self.barcode_input, 1)
        lay.addLayout(barcode_row)

        # Category filter chips
        self.category_bar = _CategoryBar()
        self.category_bar.changed.connect(self._on_category_changed)
        lay.addWidget(self.category_bar)

        # Product grid
        prod_scroll = QScrollArea()
        prod_scroll.setWidgetResizable(True)
        prod_scroll.setFrameShape(QFrame.NoFrame)
        prod_scroll.setStyleSheet('QScrollArea{background:transparent;border:none;}')
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        prod_scroll.setWidget(self._grid_container)
        lay.addWidget(prod_scroll, 1)

        return panel

    # ── Middle: customer card + cart table ──────────────────────────────────────

    def _build_middle(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet('QWidget{background:transparent;}')
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(self._build_customer_card())
        lay.addWidget(self._build_cart(), 1)
        return panel

    # ── Right: checkout panel ───────────────────────────────────────────────────

    def _build_right(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet('QWidget{background:transparent;}')
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        lay.addWidget(self._build_checkout())
        return panel

    # ── Customer card ──────────────────────────────────────────────────────────

    def _build_customer_card(self) -> QFrame:
        card = _card_frame()
        card.setFixedHeight(82)

        outer = QHBoxLayout(card)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(12)

        # Avatar
        avatar = QLabel()
        avatar.setPixmap(
            qta.icon("fa5s.user-circle", color=_BLUE).pixmap(48, 48)
        )
        avatar.setFixedSize(56, 56)
        avatar.setAlignment(Qt.AlignCenter)

        avatar.setStyleSheet("""
            QLabel{
                background:#eff6ff;
                border-radius:28px;
            }
        """)

        outer.addWidget(avatar)

        # Customer selector
        self.cust_combo = QComboBox()
        self.cust_combo.setFixedHeight(46)

        self.cust_combo.setStyleSheet(f"""
            QComboBox {{
                background:white;
                border:1px solid #dbe3ef;
                border-radius:12px;
                padding-left:14px;
                font-size:14px;
                font-weight:500;
            }}

            QComboBox:hover {{
                border:1px solid {_BLUE};
            }}

            QComboBox:focus {{
                border:2px solid {_BLUE};
            }}

            QComboBox::drop-down {{
                border:none;
                width:30px;
            }}
        """)

        self.cust_combo.currentIndexChanged.connect(
            self._on_customer_changed
        )

        outer.addWidget(self.cust_combo, 1)

        # Reload button
        self.btn_reload_cust = QPushButton()
        self.btn_reload_cust.setIcon(ic.ic_refresh(color=_BLUE))
        self.btn_reload_cust.setIconSize(QtCore.QSize(18, 18))
        self.btn_reload_cust.setFixedSize(40, 40)

        self.btn_reload_cust.setStyleSheet("""
            QPushButton{
                background:#eff6ff;
                border:none;
                border-radius:10px;
            }

            QPushButton:hover{
                background:#dbeafe;
            }
        """)

        self.btn_reload_cust.clicked.connect(
            self._load_customers
        )

        outer.addWidget(self.btn_reload_cust)

        # Right stats
        stats = QVBoxLayout()
        stats.setSpacing(4)

        self.cust_debt_lbl = QLabel()
        self.cust_debt_lbl.setVisible(False)
        self.cust_debt_lbl.setAlignment(Qt.AlignCenter)

        self.cust_debt_lbl.setStyleSheet("""
            QLabel{
                background:#fef2f2;
                color:#dc2626;
                border:1px solid #fecaca;
                border-radius:12px;
                padding:4px 10px;
                font-size:11px;
                font-weight:700;
            }
        """)

        self.cust_loyalty_lbl = QLabel()
        self.cust_loyalty_lbl.setVisible(False)
        self.cust_loyalty_lbl.setAlignment(Qt.AlignCenter)

        self.cust_loyalty_lbl.setStyleSheet("""
            QLabel{
                background:#eff6ff;
                color:#2563eb;
                border:1px solid #bfdbfe;
                border-radius:12px;
                padding:4px 10px;
                font-size:11px;
                font-weight:700;
            }
        """)

        stats.addWidget(self.cust_debt_lbl)
        stats.addWidget(self.cust_loyalty_lbl)

        outer.addLayout(stats)

        return card

    # ── Cart table ─────────────────────────────────────────────────────────────

    def _build_cart(self) -> QFrame:
        panel = _card_frame()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        self.cart_title = _section_label(tr('cart'))
        self.cart_count_lbl = QLabel('0 items')
        self.cart_count_lbl.setStyleSheet(
            f'background:{_BLUE};color:#fff;border-radius:12px;'
            'padding:6px 16px;font-size:13px;font-weight:700;'
        )
        self.btn_clear = QPushButton('Clear Cart')
        self.btn_clear.setFixedHeight(38)
        self.btn_clear.setStyleSheet(
            'QPushButton{background:transparent;color:#ef4444;'
            'border:2px solid #fca5a5;border-radius:10px;'
            'padding:0 20px;font-size:14px;font-weight:700;}'
            'QPushButton:hover{background:#fef2f2;border-color:#ef4444;}'
        )
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
            'QTableWidget::item{padding:8px 12px;font-size:14px;}'
            'QTableWidget::item:alternate{background:#f8fafc;}'
            'QTableWidget::item:selected{background:#eff6ff;color:#1e293b;}'
            'QHeaderView::section{background:#f1f5f9;border:none;'
            'padding:12px 12px;font-size:13px;font-weight:700;color:#64748b;'
            'text-transform:uppercase;letter-spacing:0.5px;'
            'border-bottom:2px solid #e2e8f0;}'
        )

        hh = self.cart_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(1, 120)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(2, 100)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(3, 120)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(4, 38)
        self.cart_table.verticalHeader().setDefaultSectionSize(40)

        lay.addWidget(self.cart_table, 1)
        return panel

    # ── Checkout panel — Order Summary ─────────────────────────────────────────

    def _build_checkout(self) -> QFrame:
        panel = _card_frame()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        # ── Header: icon tile + title + live item-count pill ──────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        icon_tile = QLabel()
        icon_tile.setPixmap(
            qta.icon('fa5s.file-invoice-dollar', color='#ffffff').pixmap(18, 18)
        )
        icon_tile.setFixedSize(34, 34)
        icon_tile.setAlignment(Qt.AlignCenter)
        icon_tile.setStyleSheet(f'background:{_BLUE};border:none;border-radius:10px;')
        hdr.addWidget(icon_tile)

        self._sum_title = QLabel(tr('order_summary'))
        self._sum_title.setStyleSheet(
            f'color:{_DARK};font-size:17px;font-weight:800;'
            'background:transparent;border:none;'
        )
        hdr.addWidget(self._sum_title)
        hdr.addStretch()

        self._sum_items_lbl = QLabel('0')
        self._sum_items_lbl.setAlignment(Qt.AlignCenter)
        self._sum_items_lbl.setToolTip(tr('cart'))
        self._sum_items_lbl.setStyleSheet(
            f'background:#eff6ff;color:{_BLUE};border:none;'
            'border-radius:12px;padding:5px 14px;font-size:13px;font-weight:800;'
        )
        hdr.addWidget(self._sum_items_lbl)
        outer.addLayout(hdr)

        # ── TOTAL — hero card with blue gradient ──────────────────────────────
        total_card = QFrame()
        total_card.setObjectName('TotalCard')
        total_card.setStyleSheet(
            'QFrame#TotalCard{background:qlineargradient('
            'x1:0,y1:0,x2:1,y2:1,'
            f'stop:0 {_BLUE}, stop:1 #0b5cc4);'
            'border:none;border-radius:16px;}'
        )
        total_lay = QVBoxLayout(total_card)
        total_lay.setContentsMargins(16, 12, 16, 12)
        total_lay.setSpacing(2)

        self._total_caption = QLabel(tr('total').upper())
        self._total_caption.setAlignment(Qt.AlignCenter)
        self._total_caption.setStyleSheet(
            'color:#dbeafe;font-size:11px;font-weight:700;'
            'background:transparent;border:none;'
        )
        total_lay.addWidget(self._total_caption)

        self.lbl_total = QLabel('0.00')
        self.lbl_total.setAlignment(Qt.AlignCenter)
        self.lbl_total.setStyleSheet(
            'color:#ffffff;font-size:36px;font-weight:900;'
            'background:transparent;border:none;'
        )
        total_lay.addWidget(self.lbl_total)

        self._incl_tax_lbl = QLabel(tr('incl_tax'))
        self._incl_tax_lbl.setAlignment(Qt.AlignCenter)
        self._incl_tax_lbl.setStyleSheet(
            'color:#bfdbfe;font-size:10px;font-weight:600;'
            'background:transparent;border:none;'
        )
        total_lay.addWidget(self._incl_tax_lbl)
        outer.addWidget(total_card)

        outer.addWidget(_divider())

        # ── Payment method — segmented icon buttons ────────────────────────────
        self._pm_caption = QLabel(tr('payment_method'))
        self._pm_caption.setStyleSheet(
            f'color:{_DARK};font-size:13px;font-weight:700;'
            'background:transparent;border:none;'
        )
        outer.addWidget(self._pm_caption)

        pm_row = QHBoxLayout()
        pm_row.setSpacing(10)
        self._pay_btns: dict[str, QPushButton] = {}
        for key, label_key, color, tint, icon_name in [
            ('cash', 'cash',           _GREEN, 'rgba(22,163,74,8%)',  'fa5s.money-bill-wave'),
            ('debt', 'debt_on_credit', _AMBER, 'rgba(245,158,11,12%)', 'fa5s.file-invoice-dollar'),
        ]:
            btn = QPushButton(f'  {tr(label_key)}')
            btn.setIcon(qta.icon(icon_name, color=color))
            btn.setIconSize(QtCore.QSize(16, 16))
            btn.setFixedHeight(46)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f'QPushButton{{border:2px solid {color};color:{color};'
                'background:#fff;border-radius:10px;font-size:14px;'
                'font-weight:700;padding:0 12px;}'
                f'QPushButton:hover{{background:{tint};}}'
                f'QPushButton:checked{{background:{color};color:#ffffff;}}'
            )
            # White icon while checked so it stays visible on the colored bg
            btn.toggled.connect(
                lambda checked, b=btn, n=icon_name, c=color:
                    b.setIcon(qta.icon(n, color='#ffffff' if checked else c))
            )
            btn.clicked.connect(lambda _, k=key: self._set_payment(k))
            self._pay_btns[key] = btn
            pm_row.addWidget(btn)
        self._pay_btns['cash'].setChecked(True)
        outer.addLayout(pm_row)

        # ── Amount paid + change / due ─────────────────────────────────────────
        self._paid_caption = QLabel(tr('amount_paid'))
        self._paid_caption.setStyleSheet(
            f'color:{_DARK};font-size:13px;font-weight:700;'
            'background:transparent;border:none;'
        )
        outer.addWidget(self._paid_caption)

        paid_row = QHBoxLayout()
        paid_row.setSpacing(12)
        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 99_999_999)
        self.paid_input.setDecimals(2)
        self.paid_input.setFixedHeight(48)
        self.paid_input.setStyleSheet(
            'QDoubleSpinBox{border:2px solid #cbd5e1;border-radius:10px;'
            'padding:0 14px;font-size:18px;font-weight:700;background:#fff;}'
            'QDoubleSpinBox:focus{border:2px solid #1a73e8;background:#f0f9ff;}'
        )
        self.paid_input.valueChanged.connect(self._update_change)

        change_box = QFrame()
        change_box.setObjectName('ChangeBox')
        change_box.setStyleSheet(
            'QFrame#ChangeBox{background:#f8fafc;'
            'border:1px solid #eef2f7;border-radius:10px;}'
        )
        change_lay = QVBoxLayout(change_box)
        change_lay.setContentsMargins(12, 6, 12, 6)
        change_lay.setSpacing(0)
        self._change_caption = QLabel(tr('change'))
        self._change_caption.setAlignment(Qt.AlignCenter)
        self._change_caption.setStyleSheet(
            f'color:{_SLATE};font-size:10px;font-weight:700;'
            'background:transparent;border:none;'
        )
        self.lbl_change = QLabel('0.00')
        self.lbl_change.setAlignment(Qt.AlignCenter)
        self.lbl_change.setStyleSheet(
            f'font-size:16px;font-weight:800;color:{_GREEN};'
            'background:transparent;border:none;'
        )
        change_lay.addWidget(self._change_caption)
        change_lay.addWidget(self.lbl_change)

        paid_row.addWidget(self.paid_input, 2)
        paid_row.addWidget(change_box, 1)
        outer.addLayout(paid_row)

        outer.addWidget(_divider())

        # ── Discount + Coupon ──────────────────────────────────────────────────
        discount_section = QHBoxLayout()
        discount_section.setSpacing(10)

        disc_col = QVBoxLayout()
        disc_col.setSpacing(5)
        self._disc_caption = QLabel(tr('discount'))
        self._disc_caption.setStyleSheet(
            f'color:{_SLATE};font-size:12px;font-weight:600;'
            'background:transparent;border:none;'
        )
        self.disc_combo = QComboBox()
        self.disc_combo.setFixedHeight(40)
        self.disc_combo.setStyleSheet(
            'QComboBox{border:1.5px solid #e2e8f0;border-radius:8px;'
            'padding:0 12px;font-size:13px;background:#fff;}'
            'QComboBox::drop-down{border:none;width:22px;}'
        )
        self.disc_combo.currentIndexChanged.connect(self._on_discount_changed)
        disc_col.addWidget(self._disc_caption)
        disc_col.addWidget(self.disc_combo)

        coupon_col = QVBoxLayout()
        coupon_col.setSpacing(5)
        self._coupon_caption = QLabel(tr('coupon_code'))
        self._coupon_caption.setStyleSheet(
            f'color:{_SLATE};font-size:12px;font-weight:600;'
            'background:transparent;border:none;'
        )
        coupon_row = QHBoxLayout()
        coupon_row.setSpacing(6)
        self.coupon_input = QLineEdit()
        self.coupon_input.setPlaceholderText(tr('enter_code'))
        self.coupon_input.setFixedHeight(40)
        self.coupon_input.setStyleSheet(
            'QLineEdit{border:1.5px solid #cbd5e1;border-radius:8px;'
            'padding:0 12px;font-size:13px;background:#fff;}'
            'QLineEdit:focus{border:1.5px solid #1a73e8;}'
        )
        self._apply_btn = QPushButton(f'  {tr("apply")}')
        self._apply_btn.setIcon(qta.icon('fa5s.check', color=_BLUE))
        self._apply_btn.setIconSize(QtCore.QSize(14, 14))
        self._apply_btn.setFixedHeight(40)
        self._apply_btn.setCursor(Qt.PointingHandCursor)
        self._apply_btn.setStyleSheet(
            'QPushButton{background:transparent;color:#1a73e8;'
            'border:1.5px solid #1a73e8;border-radius:8px;'
            'padding:0 14px;font-size:13px;font-weight:600;}'
            'QPushButton:hover{background:#eff6ff;}'
        )
        self._apply_btn.clicked.connect(self._apply_coupon)
        coupon_row.addWidget(self.coupon_input, 1)
        coupon_row.addWidget(self._apply_btn)
        coupon_col.addWidget(self._coupon_caption)
        coupon_col.addLayout(coupon_row)

        discount_section.addLayout(disc_col, 1)
        discount_section.addLayout(coupon_col, 1)
        outer.addLayout(discount_section)

        # ── Totals breakdown — inset box with icon rows ────────────────────────
        brk = QFrame()
        brk.setObjectName('SummaryBox')
        brk.setStyleSheet(
            'QFrame#SummaryBox{background:#f8fafc;'
            'border:1px solid #eef2f7;border-radius:12px;}'
        )
        brk_lay = QVBoxLayout(brk)
        brk_lay.setContentsMargins(14, 10, 14, 10)
        brk_lay.setSpacing(8)

        def _brow(icon_name: str, icon_color: str, caption: str):
            row = QHBoxLayout()
            row.setSpacing(8)
            ic_lbl = QLabel()
            ic_lbl.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(13, 13))
            ic_lbl.setFixedSize(15, 15)
            ic_lbl.setStyleSheet('background:transparent;border:none;')
            row.addWidget(ic_lbl)
            lb = QLabel(caption)
            lb.setStyleSheet(
                f'color:{_SLATE};font-size:13px;font-weight:600;'
                'background:transparent;border:none;'
            )
            row.addWidget(lb)
            row.addStretch()
            vl = QLabel('0.00')
            vl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            vl.setStyleSheet(
                f'color:{_DARK};font-size:13px;font-weight:700;'
                'background:transparent;border:none;'
            )
            row.addWidget(vl)
            brk_lay.addLayout(row)
            return vl, lb

        self.lbl_sub,  self._lbl_sub_caption  = _brow(
            'fa5s.shopping-basket', '#64748b', tr('subtotal'))
        self.lbl_disc, self._lbl_disc_caption = _brow(
            'fa5s.tag', '#16a34a', tr('discount'))
        self.lbl_tax,  self._lbl_tax_caption  = _brow(
            'fa5s.percent', '#64748b', tr('tax'))

        # "You save" pill — only visible while a discount is applied
        self._savings_lbl = QLabel()
        self._savings_lbl.setAlignment(Qt.AlignCenter)
        self._savings_lbl.setVisible(False)
        self._savings_lbl.setStyleSheet(
            'background:#ecfdf5;color:#059669;border:1px solid #a7f3d0;'
            'border-radius:10px;padding:5px 10px;font-size:12px;font-weight:700;'
        )
        brk_lay.addWidget(self._savings_lbl)
        outer.addWidget(brk)

        outer.addWidget(_divider())

        # ── Primary action ─────────────────────────────────────────────────────
        self.btn_complete = QPushButton(f'  {tr("complete_sale")}  (F10)')
        self.btn_complete.setIcon(qta.icon('fa5s.check-circle', color='#fff'))
        self.btn_complete.setIconSize(QtCore.QSize(20, 20))
        self.btn_complete.setFixedHeight(56)
        self.btn_complete.setCursor(Qt.PointingHandCursor)
        self.btn_complete.setStyleSheet(
            f'QPushButton{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,'
            f'stop:0 {_GREEN}, stop:1 #15803d);color:#fff;border-radius:12px;'
            'font-size:17px;font-weight:800;border:none;}'
            'QPushButton:hover{background:#15803d;}'
            'QPushButton:pressed{background:#166534;}'
            'QPushButton:disabled{background:#cbd5e1;color:#94a3b8;}'
        )
        self.btn_complete.clicked.connect(self._complete_sale)
        outer.addWidget(self.btn_complete)

        # ── Secondary actions ──────────────────────────────────────────────────
        aux_row = QHBoxLayout()
        aux_row.setSpacing(10)
        self.btn_hold = QPushButton(f'  {tr("hold")}')
        self.btn_hold.setIcon(qta.icon('fa5s.pause-circle', color=_AMBER))
        self.btn_hold.setIconSize(QtCore.QSize(16, 16))
        self.btn_hold.setFixedHeight(44)
        self.btn_hold.setCursor(Qt.PointingHandCursor)
        self.btn_hold.setStyleSheet(
            f'QPushButton{{background:transparent;color:{_AMBER};'
            f'border:2px solid {_AMBER};border-radius:10px;'
            'padding:0 12px;font-size:13px;font-weight:700;}'
            'QPushButton:hover{background:#fffbeb;}'
        )
        self.btn_hold.clicked.connect(self._hold_sale)

        self.btn_new = QPushButton(f'  {tr("new_sale")}')
        self.btn_new.setIcon(qta.icon('fa5s.plus-circle', color=_BLUE))
        self.btn_new.setIconSize(QtCore.QSize(16, 16))
        self.btn_new.setFixedHeight(44)
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.setStyleSheet(
            f'QPushButton{{background:transparent;color:{_BLUE};'
            f'border:2px solid {_BLUE};border-radius:10px;'
            'padding:0 12px;font-size:13px;font-weight:700;}'
            'QPushButton:hover{background:#eff6ff;}'
        )
        self.btn_new.clicked.connect(self._new_sale)

        self.btn_return = QPushButton(f"  {tr('ret_open')}")
        self.btn_return.setIcon(qta.icon('fa5s.undo', color=_RED))
        self.btn_return.setIconSize(QtCore.QSize(16, 16))
        self.btn_return.setFixedHeight(44)
        self.btn_return.setCursor(Qt.PointingHandCursor)
        self.btn_return.setStyleSheet(
            f'QPushButton{{background:transparent;color:{_RED};'
            f'border:2px solid {_RED};border-radius:10px;'
            'padding:0 12px;font-size:13px;font-weight:700;}'
            'QPushButton:hover{background:#fef2f2;}'
        )
        self.btn_return.clicked.connect(self._open_returns)

        aux_row.addWidget(self.btn_hold, 1)
        aux_row.addWidget(self.btn_new, 1)
        aux_row.addWidget(self.btn_return, 2)
        outer.addLayout(aux_row)

        # ── Resume held sale banner ────────────────────────────────────────────
        self.btn_resume = QPushButton(tr('resume_held'))
        self.btn_resume.setFixedHeight(40)
        self.btn_resume.setVisible(False)
        self.btn_resume.setCursor(Qt.PointingHandCursor)
        self.btn_resume.setStyleSheet(
            f'QPushButton{{background:#fef3c7;color:#92400e;border:2px solid {_AMBER};'
            'border-radius:10px;font-size:13px;font-weight:700;}'
            'QPushButton:hover{background:#fde68a;}'
        )
        self.btn_resume.clicked.connect(self._resume_held)
        outer.addWidget(self.btn_resume)

        return panel

    # ─────────────────────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────────────────────

    def _load_products(self, category: str | None = None):
        self._all_products = self.product_controller.get_all()
        cats = list(dict.fromkeys(
            str(p.category or '').strip() for p in self._all_products
            if p.category and str(p.category).strip()
        ))
        self.category_bar.set_categories(cats)
        self._rebuild_grid()

    def _fill_grid(self, products):
        while self._grid_layout.count():
            w = self._grid_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._grid_cards.clear()

        COLS = 3
        for idx, p in enumerate(products):
            card = _ProductCard(p)
            card.clicked.connect(self._add_product)
            self._grid_layout.addWidget(card, idx // COLS, idx % COLS)
            self._grid_cards[p.id] = card
        self._sync_cart_indicators()

        if not products:
            empty_container = QWidget()
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setSpacing(12)
            empty_layout.setContentsMargins(24, 48, 24, 48)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon('fa5s.search', color=_SLATE).pixmap(48, 48))
            icon_lbl.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(icon_lbl)

            empty_title = QLabel('No products found')
            empty_title.setAlignment(Qt.AlignCenter)
            empty_title.setStyleSheet(f'color:{_DARK};font-size:16px;font-weight:700;')
            empty_layout.addWidget(empty_title)

            empty_hint = QLabel('Try a different search term or category')
            empty_hint.setAlignment(Qt.AlignCenter)
            empty_hint.setStyleSheet(f'color:{_SLATE};font-size:13px;')
            empty_layout.addWidget(empty_hint)

            self._grid_layout.addWidget(empty_container, 0, 0, 1, COLS)

    def _rebuild_grid(self):
        """Apply active category + search term, then re-render the grid."""
        prods = self._all_products
        if self._active_category:
            prods = [p for p in prods
                     if (p.category or '').strip() == self._active_category]
        term = self._search_term.lower()
        if term:
            prods = [p for p in prods
                     if term in (p.name or '').lower()
                     or term in (p.barcode or '').lower()]
        self._fill_grid(prods)

    def _on_category_changed(self, category: str):
        self._active_category = '' if category == 'All' else category
        self._rebuild_grid()

    def _sync_cart_indicators(self):
        """Push current cart quantities into the product cards (no grid rebuild)."""
        qtys = {i['product'].id: i['quantity']
                for i in self.sales_controller.cart}
        for pid, card in self._grid_cards.items():
            card.set_in_cart(qtys.get(pid, 0))

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
        self.disc_combo.addItem(tr('no_discount'), None)
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
        qty = 1
        try:
            self.sales_controller.add_barcode_to_cart(product.barcode, qty)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
            return
        self.barcode_input.clear()
        self.refresh_cart()

    def _on_barcode(self):
        code = self.barcode_input.text().strip()
        if not code:
            return
        qty = 1
        try:
            self.sales_controller.add_barcode_to_cart(code, qty)
        except Exception as e:
            QMessageBox.warning(self, 'Error', str(e))
            return
        self.barcode_input.clear()
        self.refresh_cart()

    def _on_search(self, text: str):
        self._search_term = text.strip()
        self._rebuild_grid()

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

    def _open_returns(self):
        from controllers.returns_controller import ReturnsController
        from views.returns_dialog import ReturnDialog
        dlg = ReturnDialog(ReturnsController(), parent=self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._load_products()   # stock indicators changed
            self.refresh_cart()

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
            self.cart_table.setRowHeight(r, 56)

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

            # Col 4: Delete button — fills cell naturally, styled flat
            del_btn = QPushButton()
            del_btn.setIcon(qta.icon('fa5s.times', color='#94a3b8'))
            del_btn.setIconSize(QtCore.QSize(16, 16))
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(
                'QPushButton{background:transparent;border:none;border-radius:6px;}'
                'QPushButton:hover{background:#fee2e2;}'
                'QPushButton:hover QIcon{color:#ef4444;}'
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
        if t['disc_amount'] > 0:
            self.lbl_disc.setText(f'-{t["disc_amount"]:,.2f} {cur}')
            self.lbl_disc.setStyleSheet(
                f'color:{_GREEN};font-size:13px;font-weight:800;'
                'background:transparent;border:none;'
            )
            self._savings_lbl.setText(
                f'{tr("you_save")} {t["disc_amount"]:,.2f} {cur}'
            )
            self._savings_lbl.setVisible(True)
        else:
            self.lbl_disc.setText('—')
            self.lbl_disc.setStyleSheet(
                'color:#94a3b8;font-size:13px;font-weight:700;'
                'background:transparent;border:none;'
            )
            self._savings_lbl.setVisible(False)
        self.lbl_tax.setText(f'{t["tax"]:,.2f} {cur}  ({int(t["tax_rate"]*100)}%)')
        self.lbl_total.setText(f'{t["total"]:,.2f} {cur}')
        self._sum_items_lbl.setText(str(n))

        if self._payment_method == 'cash':
            self.paid_input.blockSignals(True)
            self.paid_input.setValue(t['total'])
            self.paid_input.blockSignals(False)

        self._update_change()
        self.btn_complete.setEnabled(n > 0)
        self._sync_cart_indicators()

    def _update_change(self):
        t    = self._compute_totals()
        paid = self.paid_input.value()
        cur  = _currency()
        if paid < t['total']:
            # Underpaid — show the outstanding balance in red
            self._change_caption.setText(tr('due'))
            self.lbl_change.setText(f'{t["total"] - paid:,.2f} {cur}')
            self.lbl_change.setStyleSheet(
                f'font-size:16px;font-weight:800;color:{_RED};background:transparent;'
            )
        else:
            self._change_caption.setText(tr('change'))
            change = paid - t['total']
            self.lbl_change.setText(f'{change:,.2f} {cur}')
            self.lbl_change.setStyleSheet(
                f'font-size:16px;font-weight:800;color:{_GREEN};background:transparent;'
            )

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
        total = self._compute_totals()['total']
        self.paid_input.blockSignals(True)
        # Debt: default to paying nothing now (rest goes on the customer's
        # account).  Cash: pre-fill with the total as before.
        self.paid_input.setValue(total if method == 'cash' else 0.0)
        self.paid_input.blockSignals(False)
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

            # Debt sales require a registered customer (walk-in can't owe money)
            if self._payment_method == 'debt' and not self._selected_customer_id:
                QMessageBox.warning(
                    self, 'Debt sale',
                    'Debt sales require a registered customer.\n'
                    'Select a customer first, or switch to Cash.'
                )
                return

            # Cash sales must be fully paid; debt sales allow partial payment
            if self._payment_method != 'debt' and paid < t['total']:
                QMessageBox.warning(
                    self, 'Insufficient payment',
                    f'Amount paid ({paid:,.2f}) is less than total ({t["total"]:,.2f}).'
                )
                return

            from utils.auth import current_user_id
            disc = self._selected_discount
            sale = self.sales_controller.complete_sale(
                customer_id=self._selected_customer_id,
                cashier_id=current_user_id(),
                discount_id=disc.get('id') if disc else None,
                discount_value=t['disc_amount'],
                tax_amount=t['tax'],
                amount_paid=paid,
                amount_change=max(paid - t['total'], 0),
                payment_method=self._payment_method,
            )

            from utils.auth import get_session
            sess = get_session()
            sale['cashier_name'] = (sess or {}).get('full_name') or (sess or {}).get('username', '')

            # ── Record the unpaid balance as customer debt ─────────────────────
            remaining = round(t['total'] - paid, 2)
            if self._payment_method == 'debt' and remaining > 0:
                try:
                    self.customer_controller.add_debt(
                        self._selected_customer_id, remaining,
                        note=f'Sale #{sale.get("id", "")}',
                    )
                except Exception:
                    logger.error('add_debt failed\n%s', traceback.format_exc())
                    QMessageBox.warning(
                        self, 'Debt',
                        f'Sale saved, but the debt of {remaining:,.2f} '
                        f'could not be recorded for this customer.'
                    )

            self._clear_cart()
            self.cust_combo.setCurrentIndex(0)
            self._load_products()
            self._load_customers()   # refresh "owes" amounts after a debt sale

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

        # ── Order summary panel ──────────────────────────────────────────────
        self._sum_title.setText(tr('order_summary'))
        self._sum_items_lbl.setToolTip(tr('cart'))
        self._total_caption.setText(tr('total').upper())
        self._incl_tax_lbl.setText(tr('incl_tax'))
        self._lbl_sub_caption.setText(tr('subtotal'))
        self._lbl_disc_caption.setText(tr('discount'))
        self._lbl_tax_caption.setText(tr('tax'))
        self._pm_caption.setText(tr('payment_method'))
        self._pay_btns['cash'].setText(f"  {tr('cash')}")
        self._pay_btns['debt'].setText(f"  {tr('debt_on_credit')}")
        self._paid_caption.setText(tr('amount_paid'))
        self._disc_caption.setText(tr('discount'))
        self.disc_combo.setItemText(0, tr('no_discount'))
        self._coupon_caption.setText(tr('coupon_code'))
        self.coupon_input.setPlaceholderText(tr('enter_code'))
        self._apply_btn.setText(f"  {tr('apply')}")
        self.btn_complete.setText(f"  {tr('complete_sale')}  (F10)")
        self.btn_hold.setText(f"  {tr('hold')}")
        self.btn_new.setText(f"  {tr('new_sale')}")
        self.btn_return.setText(f"  {tr('ret_open')}")
        self.btn_resume.setText(tr('resume_held'))
        # Refresh dynamic texts (discount row, savings pill, change/due)
        self.refresh_cart()
