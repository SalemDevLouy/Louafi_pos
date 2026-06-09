import csv
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFrame,
    QSizePolicy, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, QDate
from database.db import get_connection
import utils.icons as ic
from utils.lang import lang_manager, tr


class _Card(QFrame):
    """Small summary card widget."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName('report_card')
        self.setStyleSheet(
            '#report_card { background:#f0f4ff; border:1px solid #c3d1f0; border-radius:10px; }'
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(100)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(4)

        self._title = QLabel(title)
        self._title.setStyleSheet('color:#5f6368; font-size:15px;')
        lay.addWidget(self._title)

        self._value = QLabel('—')
        self._value.setStyleSheet('font-size:28px; font-weight:700; color:#1a73e8;')
        lay.addWidget(self._value)

    def set_value(self, text: str):
        self._value.setText(text)


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        # default: current month
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
        self.card_sales_count._title.setText(tr('card_total_sales'))
        self.card_revenue._title.setText(tr('card_revenue'))
        self.card_profit._title.setText(tr('card_profit'))
        self.card_avg._title.setText(tr('card_avg'))
        self.table.setHorizontalHeaderLabels([
            tr('col_sale_id'), tr('col_date'), tr('col_customer'),
            tr('col_items'), tr('col_total')
        ])

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        # ── Title ─────────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_ic = QLabel()
        title_ic.setPixmap(ic.ic_page_reports().pixmap(ic.LG))
        title_ic.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.page_title = QLabel(tr('page_reports'))
        self.page_title.setObjectName('page_title')
        self.page_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        title_row.addWidget(title_ic)
        title_row.addWidget(self.page_title)
        title_row.addStretch()
        root.addLayout(title_row)

        # ── Date range bar ────────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.lbl_from = QLabel(tr('from_date'))
        bar.addWidget(self.lbl_from)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        self.date_from.setFixedWidth(160)
        bar.addWidget(self.date_from)

        self.lbl_to = QLabel(tr('to_date'))
        bar.addWidget(self.lbl_to)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        self.date_to.setFixedWidth(160)
        bar.addWidget(self.date_to)

        self.btn_gen = QPushButton(tr('btn_generate'))
        self.btn_gen.setIcon(ic.ic_generate())
        self.btn_gen.setIconSize(ic.SM)
        self.btn_gen.setObjectName('action_btn')
        self.btn_gen.setFixedHeight(40)
        self.btn_gen.clicked.connect(self.generate)
        bar.addWidget(self.btn_gen)

        self.btn_export = QPushButton(tr('btn_export_csv'))
        self.btn_export.setObjectName('action_btn')
        self.btn_export.setFixedHeight(40)
        self.btn_export.setStyleSheet(
            'QPushButton { background:#2e7d32; color:white; border-radius:8px; padding:6px 18px; }'
            'QPushButton:hover { background:#1b5e20; }'
            'QPushButton:disabled { background:#ccc; }'
        )
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_csv)
        bar.addWidget(self.btn_export)

        bar.addStretch()
        root.addLayout(bar)

        # ── Summary cards ─────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.card_sales_count = _Card(tr('card_total_sales'))
        self.card_revenue     = _Card(tr('card_revenue'))
        self.card_profit      = _Card(tr('card_profit'))
        self.card_avg         = _Card(tr('card_avg'))
        for c in (self.card_sales_count, self.card_revenue, self.card_profit, self.card_avg):
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        # ── Details table ─────────────────────────────────────────────────────
        details_label = QLabel('Sale Details')
        details_label.setObjectName('section_title')
        root.addWidget(details_label)

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

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setStyleSheet(
            'QHeaderView::section { background:#1a73e8; color:white; padding:6px; font-weight:600; }'
        )
        root.addWidget(self.table)

    # ── Data ─────────────────────────────────────────────────────────────────

    def generate(self):
        d_from = self.date_from.date().toString('yyyy-MM-dd')
        d_to   = self.date_to.date().toString('yyyy-MM-dd') + ' 23:59:59'

        conn = get_connection()
        cur  = conn.cursor()

        # Summary totals
        cur.execute(
            '''SELECT COUNT(*) as cnt, COALESCE(SUM(s.total),0) as revenue
               FROM sales s
               WHERE s.date BETWEEN ? AND ?''',
            (d_from, d_to),
        )
        row = cur.fetchone()
        count    = row['cnt']
        revenue  = row['revenue']

        # Profit = SUM((sale_price - cost_price) * qty)
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

        # Detail rows
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
            self.table.setItem(ridx, 4, _item(f"{r['total']:,.2f}"))

        self._last_rows = rows          # keep for CSV export
        self._last_summary = {          # summary metadata for CSV header
            'from': d_from,
            'to':   self.date_to.date().toString('yyyy-MM-dd'),
            'count': count,
            'revenue': revenue,
            'profit': profit,
        }
        self.btn_export.setEnabled(bool(rows))

    # ── Export ────────────────────────────────────────────────────────────────

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

                # ── Summary block ──────────────────────────────────────────
                writer.writerow(['louafiPOS — Sales Report'])
                writer.writerow([
                    'Period',
                    f"{self._last_summary['from']}  →  {self._last_summary['to']}"
                ])
                writer.writerow([])
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Transactions', self._last_summary['count']])
                writer.writerow(['Total Revenue',      f"{self._last_summary['revenue']:,.2f}"])
                writer.writerow(['Total Profit',       f"{self._last_summary['profit']:,.2f}"])
                avg = (self._last_summary['revenue'] / self._last_summary['count']
                       if self._last_summary['count'] else 0)
                writer.writerow(['Avg. Sale Value',    f"{avg:,.2f}"])
                writer.writerow([])

                # ── Detail rows ────────────────────────────────────────────
                writer.writerow(['Sale ID', 'Date', 'Customer', 'Items', 'Total'])
                for r in self._last_rows:
                    writer.writerow([
                        r['id'],
                        r['date'][:16],
                        r['customer'],
                        r['item_count'],
                        f"{r['total']:.2f}",
                    ])

            QMessageBox.information(
                self, 'Export Successful',
                f'Report saved to:\n{path}',
            )
        except Exception as exc:
            QMessageBox.critical(self, 'Export Failed', str(exc))
