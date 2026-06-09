"""
Hidden admin system panel — accessible by clicking the sidebar logo.
Shows license status, live database stats, machine info, and app diagnostics.
Admin role required.
"""
import platform
import sys
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView
)

from database.db import get_connection
from utils.auth import require_role
from utils.lang import tr
from utils import license as lic


# ── db helpers ────────────────────────────────────────────────────────────────

def _db_stats() -> dict:
    try:
        con = get_connection()
        cur = con.cursor()

        def scalar(sql, *args):
            cur.execute(sql, args)
            row = cur.fetchone()
            return row[0] if row else 0

        today = datetime.now().date().isoformat()
        month = datetime.now().strftime("%Y-%m")

        stats = {
            "total_products":   scalar("SELECT COUNT(*) FROM products WHERE is_active=1"),
            "total_customers":  scalar("SELECT COUNT(*) FROM customers"),
            "total_users":      scalar("SELECT COUNT(*) FROM users WHERE is_active=1"),
            "total_sales":      scalar("SELECT COUNT(*) FROM sales"),
            "sales_today":      scalar("SELECT COUNT(*) FROM sales WHERE created_at LIKE ?",     f"{today}%"),
            "revenue_today":    scalar("SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE created_at LIKE ?", f"{today}%"),
            "revenue_month":    scalar("SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE created_at LIKE ?", f"{month}%"),
            "low_stock":        scalar("SELECT COUNT(*) FROM products WHERE stock_qty <= stock_alert_threshold AND is_active=1"),
            "total_expenses":   scalar("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE created_at LIKE ?",    f"{month}%"),
            "active_discounts": scalar("SELECT COUNT(*) FROM discounts WHERE is_active=1"),
        }

        cur.execute("""
            SELECT s.id, s.created_at, s.total_amount,
                   COALESCE(u.username, '—') AS cashier
            FROM   sales s
            LEFT JOIN users u ON u.id = s.cashier_id
            ORDER  BY s.id DESC LIMIT 10
        """)
        stats["recent_sales"] = [dict(r) for r in cur.fetchall()]
        con.close()
        return stats
    except Exception:
        return {}


# ── compact stat card ─────────────────────────────────────────────────────────

class _Card(QFrame):
    def __init__(self, label: str, value: str, color: str):
        super().__init__()
        self.setObjectName("hd_card")
        self.setStyleSheet(
            f"QFrame#hd_card {{ background:{color}; border-radius:14px; }}"
        )
        self.setMinimumHeight(90)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            "color:#ffffff; font-size:26px; font-weight:800; background:transparent;"
        )
        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(
            "color:rgba(255,255,255,0.80); font-size:12px; font-weight:600;"
            " background:transparent; letter-spacing:0.4px;"
        )
        lay.addWidget(self._val)
        lay.addWidget(self._lbl)

    def set_value(self, v: str):
        self._val.setText(v)

    def set_label(self, lbl: str):
        self._lbl.setText(lbl)


# ── main view ─────────────────────────────────────────────────────────────────

class HiddenDashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self._cards: dict[str, _Card] = {}
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        root = QVBoxLayout(container)
        root.setContentsMargins(28, 22, 28, 28)
        root.setSpacing(20)

        # ── page header ───────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        self._title_lbl = QLabel(tr("hd_title"))
        self._title_lbl.setObjectName("page_title")
        self._sub_lbl = QLabel(tr("hd_subtitle"))
        self._sub_lbl.setObjectName("sub_title")
        left.addWidget(self._title_lbl)
        left.addWidget(self._sub_lbl)
        hdr.addLayout(left)
        hdr.addStretch()

        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        self._refresh_btn = QPushButton(tr("hd_refresh"))
        self._refresh_btn.setObjectName("SecondaryButton")
        self._refresh_btn.setFixedHeight(38)
        self._refresh_btn.clicked.connect(self.refresh)
        self._ts_lbl = QLabel()
        self._ts_lbl.setStyleSheet(
            "color:#94a3b8; font-size:12px; background:transparent;"
        )
        self._ts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_col.addWidget(self._refresh_btn)
        right_col.addWidget(self._ts_lbl)
        hdr.addLayout(right_col)
        root.addLayout(hdr)

        # ── license block ─────────────────────────────────────────────────────
        lic_card = self._white_card()
        lic_inner = QVBoxLayout(lic_card)
        lic_inner.setContentsMargins(20, 16, 20, 16)
        lic_inner.setSpacing(10)
        self._lic_sec = QLabel(tr("hd_license"))
        self._lic_sec.setObjectName("section_title")
        lic_inner.addWidget(self._lic_sec)
        self._lic_grid = QGridLayout()
        self._lic_grid.setSpacing(8)
        lic_inner.addLayout(self._lic_grid)
        root.addWidget(lic_card)

        # ── stat cards ────────────────────────────────────────────────────────
        self._sales_sec = QLabel(tr("hd_sales_overview"))
        self._sales_sec.setObjectName("section_title")
        root.addWidget(self._sales_sec)

        _DEFS = [
            ("sales_today",      "hd_sales_today",  "#6d28d9"),
            ("revenue_today",    "hd_rev_today",    "#0369a1"),
            ("revenue_month",    "hd_rev_month",    "#0f766e"),
            ("total_expenses",   "hd_exp_month",    "#b45309"),
            ("total_products",   "hd_products",     "#4338ca"),
            ("low_stock",        "hd_low_stock",    "#dc2626"),
            ("total_customers",  "hd_customers",    "#7c3aed"),
            ("active_discounts", "hd_discounts",    "#059669"),
        ]
        grid = QGridLayout()
        grid.setSpacing(12)
        for idx, (key, tr_key, color) in enumerate(_DEFS):
            card = _Card(tr(tr_key), "—", color)
            self._cards[key] = (card, tr_key)
            grid.addWidget(card, idx // 4, idx % 4)
        root.addLayout(grid)

        # ── recent sales table ────────────────────────────────────────────────
        self._recent_sec = QLabel(tr("hd_recent_sales"))
        self._recent_sec.setObjectName("section_title")
        root.addWidget(self._recent_sec)

        tbl_card = self._white_card()
        tbl_inner = QVBoxLayout(tbl_card)
        tbl_inner.setContentsMargins(0, 0, 0, 0)

        self._tbl = QTableWidget()
        self._tbl.setColumnCount(4)
        self._tbl.setHorizontalHeaderLabels([
            tr("hd_col_sale"), tr("hd_col_datetime"),
            tr("hd_col_total"), tr("hd_col_cashier")
        ])
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setShowGrid(False)
        hh = self._tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        tbl_inner.addWidget(self._tbl)
        root.addWidget(tbl_card)

        # ── system info ───────────────────────────────────────────────────────
        sys_card = self._white_card()
        sys_inner = QVBoxLayout(sys_card)
        sys_inner.setContentsMargins(20, 16, 20, 16)
        sys_inner.setSpacing(8)
        self._sys_sec = QLabel(tr("hd_system_info"))
        self._sys_sec.setObjectName("section_title")
        sys_inner.addWidget(self._sys_sec)
        self._sys_grid = QGridLayout()
        self._sys_grid.setSpacing(6)
        sys_inner.addLayout(self._sys_grid)
        root.addWidget(sys_card)

        root.addStretch()

    @staticmethod
    def _white_card() -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0;"
            " border-radius:14px; }"
        )
        return f

    # ── data refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        if not require_role("admin"):
            return

        # re-translate dynamic labels (language may have changed)
        self._title_lbl.setText(tr("hd_title"))
        self._sub_lbl.setText(tr("hd_subtitle"))
        self._refresh_btn.setText(tr("hd_refresh"))
        self._lic_sec.setText(tr("hd_license"))
        self._sales_sec.setText(tr("hd_sales_overview"))
        self._recent_sec.setText(tr("hd_recent_sales"))
        self._sys_sec.setText(tr("hd_system_info"))
        self._tbl.setHorizontalHeaderLabels([
            tr("hd_col_sale"), tr("hd_col_datetime"),
            tr("hd_col_total"), tr("hd_col_cashier")
        ])

        stats = _db_stats()

        # stat cards
        def fmt(v):
            return f"{float(v):,.0f}" if isinstance(v, (int, float)) else str(v)

        for key, (card, tr_key) in self._cards.items():
            card.set_label(tr(tr_key))
            card.set_value(fmt(stats.get(key, 0)))

        # license grid
        self._clear_grid(self._lic_grid)
        lic_st = lic.check()
        rows = [
            (tr("hd_lic_status"), tr("hd_lic_valid") if lic_st["valid"] else tr("hd_lic_invalid"),
             "#16a34a" if lic_st["valid"] else "#dc2626"),
            (tr("hd_lic_store"),  lic_st.get("store_id") or "—",          "#334155"),
            (tr("hd_lic_expiry"), lic_st.get("expiry")   or "—",          "#334155"),
            (tr("hd_lic_days"),   str(lic_st.get("days_left") or "—"),    "#0369a1"),
            (tr("hd_lic_fp"),     lic._hw_fingerprint(),                   "#6d28d9"),
        ]
        for i, (lbl, val, color) in enumerate(rows):
            l = QLabel(lbl + ":")
            l.setStyleSheet(
                "color:#64748b; font-weight:600; font-size:13px; background:transparent;"
            )
            v = QLabel(val)
            v.setStyleSheet(
                f"color:{color}; font-weight:700; font-size:13px; background:transparent;"
            )
            self._lic_grid.addWidget(l, i, 0)
            self._lic_grid.addWidget(v, i, 1)

        # recent sales
        recent = stats.get("recent_sales", [])
        self._tbl.setRowCount(len(recent))
        for r, s in enumerate(recent):
            self._tbl.setRowHeight(r, 40)
            self._tcell(r, 0, f"#{s['id']}", Qt.AlignCenter)
            self._tcell(r, 1, str(s.get("created_at", ""))[:16])
            amt = QTableWidgetItem(f"{float(s.get('total_amount', 0)):,.2f}")
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt.setForeground(QColor("#6d28d9"))
            self._tbl.setItem(r, 2, amt)
            self._tcell(r, 3, s.get("cashier", "—"), Qt.AlignCenter)

        # system info
        self._clear_grid(self._sys_grid)
        sys_rows = [
            (tr("hd_sys_python"),       sys.version.split()[0]),
            (tr("hd_sys_platform"),     platform.system() + " " + platform.release()),
            (tr("hd_sys_machine"),      platform.machine()),
            (tr("hd_sys_db"),           "pos.db"),
            (tr("hd_sys_total_sales"),  str(stats.get("total_sales", 0))),
            (tr("hd_sys_users"),        str(stats.get("total_users", 0))),
        ]
        for i, (lbl, val) in enumerate(sys_rows):
            l = QLabel(lbl + ":")
            l.setStyleSheet(
                "color:#64748b; font-weight:600; font-size:13px; background:transparent;"
            )
            v = QLabel(val)
            v.setStyleSheet("color:#1e293b; font-size:13px; background:transparent;")
            self._sys_grid.addWidget(l, i, 0)
            self._sys_grid.addWidget(v, i, 1)

        self._ts_lbl.setText(tr("hd_updated") + datetime.now().strftime("%H:%M:%S"))

    @staticmethod
    def _clear_grid(grid: QGridLayout):
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _tcell(self, row: int, col: int, text: str,
               align=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        self._tbl.setItem(row, col, item)
