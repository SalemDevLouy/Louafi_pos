import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QDialog, QFormLayout,
    QMessageBox, QHeaderView, QCheckBox,
    QFrame, QSizePolicy, QSpacerItem
)

from controllers import auth_controller
from utils.auth import current_user_id, require_role
from utils.lang import tr

logger = logging.getLogger(__name__)

_ROLE_COLORS = {
    "admin":      ("#7c3aed", "#f5f3ff"),
    "supervisor": ("#0369a1", "#e0f2fe"),
    "cashier":    ("#15803d", "#dcfce7"),
}


class UserDialog(QDialog):
    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.is_edit = user is not None
        self.setWindowTitle(tr("edit_user") if self.is_edit else tr("create_user"))
        self.setFixedWidth(420)

        outer = QVBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QLabel(tr("edit_user") if self.is_edit else tr("new_user"))
        header.setObjectName("section_title")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.username = QLineEdit()
        self.username.setReadOnly(self.is_edit)
        if self.is_edit:
            self.username.setPlaceholderText("")
        else:
            self.username.setPlaceholderText("Unique username...")
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Full name...")
        self.role = QComboBox()
        self.role.addItems([tr("admin"), tr("supervisor"), tr("cashier")])
        self._role_vals = ["admin", "supervisor", "cashier"]

        if not self.is_edit:
            self.password = QLineEdit()
            self.password.setEchoMode(QLineEdit.Password)
            self.password.setPlaceholderText("Initial password")
            form.addRow(tr("username"), self.username)
            form.addRow(tr("full_name"), self.full_name)
            form.addRow(tr("role"), self.role)
            form.addRow(tr("password"), self.password)
        else:
            self.username.setText(user.get("username", ""))
            self.full_name.setText(user.get("full_name", ""))
            role_val = user.get("role", "cashier")
            self.role.setCurrentIndex(self._role_vals.index(role_val) if role_val in self._role_vals else 2)
            form.addRow(tr("username"), self.username)
            form.addRow(tr("full_name"), self.full_name)
            form.addRow(tr("role"), self.role)

        outer.addLayout(form)
        outer.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(tr("save"))
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

    def get_data(self) -> dict:
        d = {
            "username": self.username.text().strip(),
            "full_name": self.full_name.text().strip(),
            "role": self._role_vals[self.role.currentIndex()],
        }
        if not self.is_edit:
            d["password"] = self.password.text()
        return d


class ResetPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("reset_password"))
        self.setFixedWidth(360)

        outer = QVBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Reset Password")
        header.setObjectName("section_title")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(14)
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("New password")
        form.addRow(tr("new_password"), self.pw)
        outer.addLayout(form)

        outer.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton(tr("save"))
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setFixedWidth(100)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        outer.addLayout(btn_row)

    def get_password(self) -> str:
        return self.pw.text()


class UserManagementView(QWidget):
    def __init__(self):
        super().__init__()
        self._data: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Page header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        page_title = QLabel(tr("users"))
        page_title.setObjectName("page_title")
        subtitle = QLabel(tr("users_subtitle"))
        subtitle.setObjectName("sub_title")
        title_col.addWidget(page_title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()
        add_btn = QPushButton("＋  " + tr("create_user"))
        add_btn.setObjectName("PrimaryButton")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._add)
        header_row.addWidget(add_btn)
        root.addLayout(header_row)

        # Table card
        table_card = QFrame()
        table_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }"
        )
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", tr("username"), tr("full_name"), tr("role"),
            tr("status"), tr("col_last_login"), tr("col_must_change_pw")
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        table_layout.addWidget(self.table)
        root.addWidget(table_card, stretch=1)

        # Bottom action bar
        btns = QHBoxLayout()
        btns.addStretch()
        for label, slot, obj_name in [
            (tr("edit"),           self._edit,          "SecondaryButton"),
            (tr("toggle_active"),  self._toggle_active, "SecondaryButton"),
            (tr("reset_password"), self._reset_password,"SecondaryButton"),
            (tr("refresh"),        self.load,           "SecondaryButton"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(36)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        root.addLayout(btns)

    def load(self):
        if not require_role("admin"):
            QMessageBox.warning(self, tr("error"), tr("admin_only"))
            return
        ok, data = auth_controller.get_all_users()
        if not ok:
            QMessageBox.warning(self, tr("error"), data)
            return
        self._data = data
        self.table.setRowCount(0)
        for row in data:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 44)

            self._cell(r, 0, str(row["id"]), Qt.AlignCenter)
            self._cell(r, 1, row.get("username", ""))

            full_name = row.get("full_name", "")
            self._cell(r, 2, full_name)

            role_val = row.get("role", "")
            role_item = QTableWidgetItem(tr(role_val).capitalize())
            role_item.setTextAlignment(Qt.AlignCenter)
            fg, _ = _ROLE_COLORS.get(role_val, ("#334155", "#f1f5f9"))
            role_item.setForeground(QColor(fg))
            self.table.setItem(r, 3, role_item)

            active = bool(row.get("is_active", True))
            status_item = QTableWidgetItem(tr("active") if active else tr("inactive"))
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor("#16a34a") if active else QColor("#dc2626"))
            self.table.setItem(r, 4, status_item)

            self._cell(r, 5, str(row.get("last_login") or tr("never"))[:16], Qt.AlignCenter)
            mcp_item = QTableWidgetItem(tr("yes") if row.get("must_change_password") else tr("no"))
            mcp_item.setTextAlignment(Qt.AlignCenter)
            if row.get("must_change_password"):
                mcp_item.setForeground(QColor("#f59e0b"))
            self.table.setItem(r, 6, mcp_item)

    def _cell(self, row: int, col: int, text: str, align=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        self.table.setItem(row, col, item)

    def _selected(self) -> dict | None:
        r = self.table.currentRow()
        return self._data[r] if 0 <= r < len(self._data) else None

    def _add(self):
        if not require_role("admin"):
            return
        dlg = UserDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.get_data()
        ok, msg = auth_controller.create_user(
            current_user_id(), d["username"], d["password"], d["role"], d["full_name"]
        )
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _edit(self):
        row = self._selected()
        if not row:
            return
        dlg = UserDialog(user=row, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        d = dlg.get_data()
        ok, msg = auth_controller.update_user(
            current_user_id(), row["id"], d["full_name"], d["role"]
        )
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _toggle_active(self):
        row = self._selected()
        if not row:
            return
        ok, msg = auth_controller.toggle_user_active(current_user_id(), row["id"])
        if ok:
            self.load()
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _reset_password(self):
        row = self._selected()
        if not row:
            return
        dlg = ResetPasswordDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        ok, msg = auth_controller.admin_reset_password(
            current_user_id(), row["id"], dlg.get_password()
        )
        if ok:
            QMessageBox.information(self, tr("success"), msg)
        else:
            QMessageBox.warning(self, tr("error"), msg)
