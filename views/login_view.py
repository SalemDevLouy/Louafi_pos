import configparser
import logging
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QDialog,
    QFormLayout, QFrame, QSizePolicy, QSpacerItem
)

from controllers import auth_controller
from utils.lang import tr
from utils import license as lic

logger = logging.getLogger(__name__)


class ChangePasswordDialog(QDialog):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle(tr("change_password"))
        self.setFixedWidth(380)

        outer = QVBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(24, 24, 24, 24)

        header = QLabel(tr("change_password"))
        header.setObjectName("section_title")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.old_pw = QLineEdit(); self.old_pw.setEchoMode(QLineEdit.Password)
        self.new_pw = QLineEdit(); self.new_pw.setEchoMode(QLineEdit.Password)
        self.confirm_pw = QLineEdit(); self.confirm_pw.setEchoMode(QLineEdit.Password)
        form.addRow(tr("old_password"), self.old_pw)
        form.addRow(tr("new_password"), self.new_pw)
        form.addRow(tr("confirm_password"), self.confirm_pw)
        outer.addLayout(form)

        outer.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton(tr("save"))
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedWidth(120)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

    def _save(self):
        if self.new_pw.text() != self.confirm_pw.text():
            QMessageBox.warning(self, tr("error"), tr("pw_no_match"))
            return
        ok, msg = auth_controller.change_password(
            self.user_id, self.old_pw.text(), self.new_pw.text()
        )
        if ok:
            QMessageBox.information(self, tr("success"), msg)
            self.accept()
        else:
            QMessageBox.warning(self, tr("error"), msg)


class ActivationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("activation"))
        self.setFixedWidth(440)

        outer = QVBoxLayout(self)
        outer.setSpacing(16)
        outer.setContentsMargins(24, 24, 24, 24)

        title = QLabel("🔑  " + tr("activation"))
        title.setObjectName("section_title")
        outer.addWidget(title)

        desc = QLabel(tr("activation_desc"))
        desc.setObjectName("sub_title")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("SSSS-DDDDDDDD-CCCC")
        self.key_input.setFixedHeight(42)
        outer.addWidget(self.key_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        activate_btn = QPushButton(tr("activate"))
        activate_btn.setObjectName("PrimaryButton")
        activate_btn.setFixedHeight(40)
        activate_btn.setFixedWidth(140)
        activate_btn.clicked.connect(self._activate)
        btn_row.addWidget(activate_btn)
        outer.addLayout(btn_row)

    def _activate(self):
        ok, msg = lic.activate(self.key_input.text().strip())
        if ok:
            QMessageBox.information(self, tr("success"), msg)
            self.accept()
        else:
            QMessageBox.warning(self, tr("error"), msg)


class LoginView(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self._build_ui()
        self._check_license()

    def _build_ui(self):
        self.setObjectName("LoginView")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedWidth(400)
        vbox = QVBoxLayout(card)
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)

        # Top accent bar
        accent_bar = QFrame()
        accent_bar.setFixedHeight(6)
        accent_bar.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #7c3aed, stop:1 #6d28d9); border-radius:20px 20px 0 0;"
        )
        vbox.addWidget(accent_bar)

        # Card body
        body = QVBoxLayout()
        body.setSpacing(16)
        body.setContentsMargins(36, 32, 36, 36)
        vbox.addLayout(body)

        # Logo
        cfg = configparser.ConfigParser()
        cfg.read("config.ini")
        logo_path = cfg.get("store", "logo_path", fallback="assets/logo.png")
        logo_label = QLabel()
        pix = QPixmap(logo_path)
        if not pix.isNull():
            logo_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("🏪")
            logo_label.setStyleSheet("font-size:48px;")
        logo_label.setAlignment(Qt.AlignCenter)
        body.addWidget(logo_label)

        title = QLabel(tr("app_title"))
        title.setStyleSheet(
            "font-size:22px; font-weight:800; color:#0f172a; "
            "letter-spacing:0.5px; background:transparent;"
        )
        title.setAlignment(Qt.AlignCenter)
        body.addWidget(title)

        tagline = QLabel(tr("sign_in_tagline"))
        tagline.setStyleSheet("font-size:13px; color:#64748b; background:transparent;")
        tagline.setAlignment(Qt.AlignCenter)
        body.addWidget(tagline)

        body.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Username
        user_lbl = QLabel(tr("username"))
        user_lbl.setStyleSheet("font-size:13px; font-weight:600; color:#475569; background:transparent;")
        body.addWidget(user_lbl)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username...")
        self.username_input.setFixedHeight(42)
        body.addWidget(self.username_input)

        # Password
        pw_lbl = QLabel(tr("password"))
        pw_lbl.setStyleSheet("font-size:13px; font-weight:600; color:#475569; background:transparent;")
        body.addWidget(pw_lbl)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(42)
        self.password_input.returnPressed.connect(self._attempt_login)
        body.addWidget(self.password_input)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setFixedHeight(20)
        body.addWidget(self.error_label)

        # Login button
        login_btn = QPushButton(tr("login"))
        login_btn.setFixedHeight(44)
        login_btn.setObjectName("PrimaryButton")
        login_btn.clicked.connect(self._attempt_login)
        body.addWidget(login_btn)

        outer.addWidget(card)

    def _check_license(self):
        status = lic.check()
        if not status["valid"]:
            dlg = ActivationDialog(self)
            if dlg.exec_() != QDialog.Accepted:
                import sys; sys.exit(0)
        elif status["days_left"] is not None and status["days_left"] <= 7:
            from utils.tr import tr as _tr
            msg = _tr("license_expiry_warning").format(days=status["days_left"])
            QMessageBox.warning(self, tr("warning"), msg)

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.error_label.setText(tr("enter_credentials"))
            return
        self.error_label.setText("")
        ok, result = auth_controller.login(username, password)
        if not ok:
            self.error_label.setText(result)
            self.password_input.clear()
            return
        if result.get("must_change_password"):
            dlg = ChangePasswordDialog(result["id"], self)
            dlg.exec_()
        self.on_login_success(result)
