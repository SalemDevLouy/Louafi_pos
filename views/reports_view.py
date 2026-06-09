import csv
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFrame,
    QSizePolicy, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from database.db import get_connection
import utils.icons as ic
from utils.lang import lang_manager, tr


class _StatCard(QFrame):
    def __init__(self, title: str, icon: str = "", accent: str = "#6d28d9", parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setStyleSheet(f"""
            QFrame {{
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                border-left: 4px solid {accent};
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(100)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        top = QHBoxLayout()
        self._title = QLabel(title)
        self._title.setStyleSheet("font-size:12px; font-weight:600; color:#64748b; letter-spacing:0.4px; background:transparent; border:none;")
        top.addWidget(self._title)
        top.addStretch()
        if icon:
            ic_lbl = QLabel(icon)
            ic_lbl.setStyleSheet(f"font-size:20px; color:{accent}; background:transparent; border:none;")
            top.addWidget(ic_lbl)
        lay.addLayout(top)

        self._value = QLabel("—")
        self._value.setStyleSheet(f"font-size:26px; font-weight:800; color:{accent}; background:transparent; border:none;")
        lay.addWidget(self._value)

    def set_value(self, text: str):
        self._value.setText(text)

    def set_title(self, text: str):
        self._title.setText(text)


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        today = QDate.currentDate()
        self.date_from.setDate(QDate(today.year(), today.month(), 1))
        self.date_to.setDate(today)
        self.generate()
        lang_manager.lang_changed.connect(self.retranslate_ui)

    def retranslate_ui(self, lang=None):
        self.page_title.setText(tr('page_reports'))
        self.lbl_from.setText(tr('from_date'))
        self.lbl_to.setText(tr('to_date'))
        self.btn_gen.setText(tr('btn_generate'))
        self.btn_export.setText(tr('btn_export_csv'))
        self.card_sales_count.set_title(tr('card_total_sales'))
        self.card_revenue.set_title(tr('card_revenue'))
        self.card_profit.set_title(tr('card_profit'))
        self.card_avg.set_title(tr('card_avg'))
        self.table.setHorizontalHeaderLabels([
            tr('col_sale_id'), tr('col_date'), tr('col_customer'),
            tr('col_items'), tr('col_total')
        ])

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Page header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.page_title = QLabel(tr('page_reports'))
        self.page_title.setObjectName('page_title')
        subtitle = QLabel("Sales summaries, profit analysis and CSV exports")
        subtitle.setObjectName("sub_title")
        title_col.addWidget(self.page_title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()
        root.addLayout(header_row)

        # Date range + action bar
        bar_frame = QFrame()
        bar_frame.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; }"
        )
        bar = QHBoxLayout(bar_frame)
        bar.setContentsMargins(16, 12, 16, 12)
        bar.setSpacing(12)

        self.lbl_from = QLabel(tr('from_date'))
        self.lbl_from.setStyleSheet("font-size:13px; color:#64748b; font-weight:500; background:transparent; border:none;")
        bar.addWidget(self.lbl_from)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        self.date_from.setFixedWidth(150)
        bar.addWidget(self.date_from)

        self.lbl_to = QLabel(tr('to_date'))
        self.lbl_to.setStyleSheet("font-size:13px; color:#64748b; font-weight:500; background:transparent; border:none;")
        bar.addWidget(self.lbl_to)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        self.date_to.setFixedWidth(150)
        bar.addWidget(self.date_to)

        bar.addStretch()

        self.btn_gen = QPushButton("⚡  " + tr('btn_generate'))
        self.btn_gen.setObjectName("PrimaryButton")
        self.btn_gen.setFixedHeight(38)
        self.btn_gen.clicked.connect(self.generate)
        bar.addWidget(self.btn_gen)

        self.btn_export = QPushButton("⬇  " + tr('btn_export_csv'))
        self.btn_export.setStyleSheet(
            "QPushButton { background:#15803d; color:#fff; border-radius:8px; "
            "padding:8px 20px; font-size:14px; font-weight:600; min-height:38px; }"
            "QPushButton:hover { background:#166534; }"
            "QPushButton:disabled { background:#e2e8f0; color:#94a3b8; }"
        )
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_csv)
        bar.addWidget(self.btn_export)

        root.addWidget(bar_frame)

        # Summary stat cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self.card_sales_count = _StatCard(tr('card_total_sales'), "🧾", "#6d28d9")
        self.card_revenue     = _StatCard(tr('card_revenue'),     "💰", "#0369a1")
        self.card_profit      = _StatCard(tr('card_profit'),      "📈", "#15803d")
        self.card_avg         = _StatCard(tr('card_avg'),         "⊘",  "#b45309")
        for c in (self.card_sales_count, self.card_revenue, self.card_profit, self.card_avg):
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        # Details table card
        table_card = QFrame()
        table_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }"
        )
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        details_header = QFrame()
        details_header.setStyleSheet(
            "QFrame { background:#f8fafc; border-radius:14px 14px 0 0; "
            "border-bottom:1px solid #e2e8f0; }"
        )
        dh_lay = QHBoxLayout(details_header)
        dh_lay.setContentsMargins(16, 12, 16, 12)
        dh_title = QLabel("Sale Details")
        dh_title.setObjectName("section_title")
        dh_lay.addWidget(dh_title)
        dh_lay.addStretch()
        self._row_count_label = QLabel("0 records")
        self._row_count_label.setStyleSheet("font-size:13px; color:#64748b; background:transparent; border:none;")
        dh_lay.addWidget(self._row_count_label)
        tc_layout.addWidget(details_header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tr('col_sale_id'), tr('col_date'), tr('col_customer'),
            tr('col_items'), tr('col_total')
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setDefaultAlignment(Qt.AlignCenter)

        tc_layout.addWidget(self.table)
        root.addWidget(table_card, stretch=1)

    def generate(self):
        d_from = self.date_from.date().toString('yyyy-MM-dd')
        d_to   = self.date_to.date().toString('yyyy-MM-dd') + ' 23:59:59'

        conn = get_connection()
        cur  = conn.cursor()

        cur.execute(
            '''SELECT COUNT(*) as cnt, COALESCE(SUM(s.total),0) as revenue
               FROM sales s WHERE s.date BETWEEN ? AND ?''',
            (d_from, d_to),
        )
        row = cur.fetchone()
        count   = row['cnt']
        revenue = row['revenue']

        cur.execute(
            '''SELECT COALESCE(SUM((si.price - COALESCE(p.cost_price,0)) * si.quantity), 0) as profit
               FROM sale_items si
               JOIN products p ON p.id = si.product_id
               JOIN sales s ON s.id = si.sale_id
               WHERE s.date BETWEEN ? AND ?''',
            (d_from, d_to),
        )
        profit = cur.fetchone()['profit']
        avg = (revenue / count) if count else 0

        self.card_sales_count.set_value(str(count))
        self.card_revenue.set_value(f'{revenue:,.2f}')
        self.card_profit.set_value(f'{profit:,.2f}')
        self.card_avg.set_value(f'{avg:,.2f}')

        cur.execute(
            '''SELECT s.id, s.date, COALESCE(c.name, '—') as customer,
                      COUNT(si.id) as item_count, s.total
               FROM sales s
               LEFT JOIN customers c ON c.id = s.customer_id
               LEFT JOIN sale_items si ON si.sale_id = s.id
               WHERE s.date BETWEEN ? AND ?
               GROUP BY s.id
               ORDER BY s.date DESC''',
            (d_from, d_to),
        )
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for r in rows:
            ridx = self.table.rowCount()
            self.table.insertRow(ridx)
            self.table.setRowHeight(ridx, 44)

            def _item(text, align=Qt.AlignCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                return it

            self.table.setItem(ridx, 0, _item(r['id']))
            self.table.setItem(ridx, 1, _item(r['date'][:16]))
            self.table.setItem(ridx, 2, _item(r['customer'], Qt.AlignLeft | Qt.AlignVCenter))
            self.table.setItem(ridx, 3, _item(f"{r['item_count']} item(s)"))
            total_item = _item(f"{r['total']:,.2f}")
            total_item.setForeground(QColor("#6d28d9"))
            self.table.setItem(ridx, 4, total_item)

        self._row_count_label.setText(f"{len(rows)} record{'s' if len(rows) != 1 else ''}")
        self._last_rows = rows
        self._last_summary = {
            'from': d_from, 'to': self.date_to.date().toString('yyyy-MM-dd'),
            'count': count, 'revenue': revenue, 'profit': profit,
        }
        self.btn_export.setEnabled(bool(rows))

    def export_csv(self):
        default_name = (
            f"report_{self._last_summary['from']}_to_{self._last_summary['to']}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Report as CSV',
            os.path.join(os.path.expanduser('~'), default_name),
            'CSV Files (*.csv)',
        )
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['LouafiPOS — Sales Report'])
                writer.writerow(['Period', f"{self._last_summary['from']}  →  {self._last_summary['to']}"])
                writer.writerow([])
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Transactions', self._last_summary['count']])
                writer.writerow(['Total Revenue',      f"{self._last_summary['revenue']:,.2f}"])
                writer.writerow(['Total Profit',       f"{self._last_summary['profit']:,.2f}"])
                avg = (self._last_summary['revenue'] / self._last_summary['count']
                       if self._last_summary['count'] else 0)
                writer.writerow(['Avg. Sale Value', f"{avg:,.2f}"])
                writer.writerow([])
                writer.writerow(['Sale ID', 'Date', 'Customer', 'Items', 'Total'])
                for r in self._last_rows:
                    writer.writerow([r['id'], r['date'][:16], r['customer'], r['item_count'], f"{r['total']:.2f}"])
            QMessageBox.information(self, 'Export Successful', f'Report saved to:\n{path}')
        except Exception as exc:
            QMessageBox.critical(self, 'Export Failed', str(exc))
