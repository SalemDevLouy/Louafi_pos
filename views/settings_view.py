import configparser
import logging
import os

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QDoubleSpinBox,
    QSpinBox, QSlider, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QTabWidget, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QSpacerItem
)

from utils import backup as bkp
from utils.lang import tr, lang_manager
from utils import lang as lang_utils
from utils.theme import font_manager, MIN_BASE, MAX_BASE, DEFAULT_BASE
from utils.auth import require_role

logger = logging.getLogger(__name__)
_CONFIG_PATH = "config.ini"
_TAB_STYLE = "background:transparent;"


class BackupWorker(QThread):
    done = pyqtSignal(bool, str)

    def run(self):
        ok, path = bkp.create_backup()
        self.done.emit(ok, path)


class SettingsView(QWidget):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._cfg = configparser.RawConfigParser()
        self._cfg.read(_CONFIG_PATH)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Page header
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        page_title = QLabel(tr("settings"))
        page_title.setObjectName("page_title")
        subtitle = QLabel(tr("settings_subtitle"))
        subtitle.setObjectName("sub_title")
        title_col.addWidget(page_title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()
        save_btn = QPushButton("💾  " + tr("save"))
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._save)
        header_row.addWidget(save_btn)
        root.addLayout(header_row)

        # Tabs card
        tabs_card = QFrame()
        tabs_card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }"
        )
        tabs_layout = QVBoxLayout(tabs_card)
        tabs_layout.setContentsMargins(16, 16, 16, 16)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._store_tab(),   tr("tab_store"))
        tabs.addTab(self._receipt_tab(), tr("tab_receipt"))
        tabs.addTab(self._app_tab(),     tr("tab_app"))
        tabs.addTab(self._backup_tab(),  tr("tab_backup"))
        tabs_layout.addWidget(tabs)
        root.addWidget(tabs_card, stretch=1)

    def _store_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(_TAB_STYLE)
        form = QFormLayout(w)
        form.setSpacing(16)
        form.setContentsMargins(8, 16, 8, 16)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.store_name = QLineEdit()
        self.store_address = QLineEdit()
        self.store_phone = QLineEdit()
        self.currency = QLineEdit()
        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0, 1)
        self.tax_rate.setDecimals(3)
        self.tax_rate.setSingleStep(0.01)
        self.tax_rate.setSuffix("  (e.g. 0.19)")
        self.logo_path = QLineEdit()
        logo_btn = QPushButton("Browse…")
        logo_btn.setObjectName("SecondaryButton")
        logo_btn.setFixedHeight(36)
        logo_btn.clicked.connect(self._browse_logo)
        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.addWidget(self.logo_path)
        logo_row.addWidget(logo_btn)
        logo_widget = QWidget()
        logo_widget.setLayout(logo_row)

        form.addRow(tr("store_name"), self.store_name)
        form.addRow(tr("address"), self.store_address)
        form.addRow(tr("phone"), self.store_phone)
        form.addRow(tr("currency"), self.currency)
        form.addRow(tr("tax_rate"), self.tax_rate)
        form.addRow(tr("image"), logo_widget)
        return w

    def _receipt_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(_TAB_STYLE)
        form = QFormLayout(w)
        form.setSpacing(16)
        form.setContentsMargins(8, 16, 8, 16)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.receipt_header = QLineEdit()
        self.receipt_header.setPlaceholderText("Text shown at the top of receipts")
        self.receipt_footer = QLineEdit()
        self.receipt_footer.setPlaceholderText("Text shown at the bottom of receipts")
        form.addRow(tr("receipt_header"), self.receipt_header)
        form.addRow(tr("receipt_footer"), self.receipt_footer)
        return w

    def _app_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(_TAB_STYLE)
        form = QFormLayout(w)
        form.setSpacing(16)
        form.setContentsMargins(8, 16, 8, 16)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.language = QComboBox()
        self.language.addItems(["ar", "fr"])
        self.theme = QComboBox()
        self.theme.addItems([tr("light"), tr("dark")])
        self.loyalty_rate = QDoubleSpinBox()
        self.loyalty_rate.setRange(0, 1)
        self.loyalty_rate.setDecimals(3)
        self.loyalty_rate.setSingleStep(0.005)
        self.inactivity = QSpinBox()
        self.inactivity.setRange(0, 3600)
        self.inactivity.setSuffix(" s")

        # ── Font size ─────────────────────────────────────────────────────
        font_col = QVBoxLayout()
        font_col.setSpacing(6)
        font_col.setContentsMargins(0, 0, 0, 0)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_row.setContentsMargins(0, 0, 0, 0)
        self._font_presets = {}
        for label, size in [("Small", 14), ("Normal", 16), ("Large", 18), ("X-Large", 20)]:
            btn = QPushButton(label)
            btn.setObjectName("SecondaryButton")
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _, s=size: self._apply_font_preset(s))
            preset_row.addWidget(btn)
            self._font_presets[size] = btn
        preset_row.addStretch()

        slider_row = QHBoxLayout()
        slider_row.setSpacing(10)
        slider_row.setContentsMargins(0, 0, 0, 0)
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setRange(MIN_BASE, MAX_BASE)
        self.font_slider.setTickInterval(2)
        self.font_slider.setTickPosition(QSlider.TicksBelow)
        self.font_slider.setMinimumWidth(160)
        self.font_preview = QLabel("Aa 20px")
        self.font_preview.setFixedWidth(70)
        self.font_slider.valueChanged.connect(self._update_font_preview)
        slider_row.addWidget(self.font_slider, stretch=1)
        slider_row.addWidget(self.font_preview)

        font_col.addLayout(preset_row)
        font_col.addLayout(slider_row)
        font_widget = QWidget()
        font_widget.setLayout(font_col)
        # ─────────────────────────────────────────────────────────────────

        form.addRow(tr("language"), self.language)
        form.addRow(tr("theme"), self.theme)
        form.addRow(tr("loyalty_rate"), self.loyalty_rate)
        form.addRow(tr("inactivity_timeout"), self.inactivity)
        form.addRow(tr("font_size"), font_widget)
        return w

    def _apply_font_preset(self, size: int):
        self.font_slider.setValue(size)

    def _update_font_preview(self):
        size = self.font_slider.value()
        self.font_preview.setStyleSheet(f"font-size: {size}px; font-weight: 600; color: #6d28d9;")
        self.font_preview.setText(f"Aa {size}px")

    def _backup_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(_TAB_STYLE)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.backup_dest = QLineEdit()
        dest_btn = QPushButton("Browse…")
        dest_btn.setObjectName("SecondaryButton")
        dest_btn.setFixedHeight(36)
        dest_btn.clicked.connect(self._browse_dest)
        dest_row = QHBoxLayout()
        dest_row.setContentsMargins(0, 0, 0, 0)
        dest_row.addWidget(self.backup_dest)
        dest_row.addWidget(dest_btn)
        dest_widget = QWidget()
        dest_widget.setLayout(dest_row)
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(0, 1440)
        self.backup_interval.setSuffix(" min")
        form.addRow(tr("backup_destination"), dest_widget)
        form.addRow(tr("backup_interval"), self.backup_interval)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        create_btn = QPushButton("⬆  " + tr("create_backup"))
        create_btn.setObjectName("PrimaryButton")
        create_btn.setFixedHeight(38)
        create_btn.clicked.connect(self._do_backup)
        restore_btn = QPushButton("⬇  " + tr("restore_backup"))
        restore_btn.setObjectName("SecondaryButton")
        restore_btn.setFixedHeight(38)
        restore_btn.clicked.connect(self._do_restore)
        btn_row.addWidget(create_btn)
        btn_row.addWidget(restore_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        existing_label = QLabel(tr("existing_backups"))
        existing_label.setObjectName("section_title")
        layout.addWidget(existing_label)

        self.backup_list = QListWidget()
        self._refresh_backup_list()
        layout.addWidget(self.backup_list, stretch=1)
        return w

    def _load_values(self):
        g = self._cfg
        self.store_name.setText(g.get("store", "name", fallback=""))
        self.store_address.setText(g.get("store", "address", fallback=""))
        self.store_phone.setText(g.get("store", "phone", fallback=""))
        self.currency.setText(g.get("store", "currency", fallback="DZD"))
        self.tax_rate.setValue(g.getfloat("store", "tax_rate", fallback=0.19))
        self.logo_path.setText(g.get("store", "logo_path", fallback="assets/logo.png"))
        self.receipt_header.setText(g.get("receipt", "header", fallback=""))
        self.receipt_footer.setText(g.get("receipt", "footer", fallback=""))
        lang = g.get("app", "language", fallback="ar")
        self.language.setCurrentText(lang)
        theme = g.get("app", "theme", fallback="light")
        self.theme.setCurrentIndex(0 if theme == "light" else 1)
        self.loyalty_rate.setValue(g.getfloat("app", "loyalty_rate", fallback=0.01))
        self.inactivity.setValue(g.getint("app", "inactivity_timeout", fallback=300))
        self.font_slider.setValue(g.getint("app", "font_size", fallback=DEFAULT_BASE))
        self._update_font_preview()
        self.backup_dest.setText(g.get("backup", "destination", fallback="backups/"))
        self.backup_interval.setValue(g.getint("backup", "interval_minutes", fallback=60))

    def _save(self):
        try:
            # RBAC: only admins may change system settings
            if not require_role('admin'):
                QMessageBox.warning(self, tr('error'), tr('insuf_perms'))
                return
            for section in ("store", "receipt", "app", "backup"):
                if not self._cfg.has_section(section):
                    self._cfg.add_section(section)

            self._cfg.set("store", "name", self.store_name.text())
            self._cfg.set("store", "address", self.store_address.text())
            self._cfg.set("store", "phone", self.store_phone.text())
            self._cfg.set("store", "currency", self.currency.text())
            self._cfg.set("store", "tax_rate", str(self.tax_rate.value()))
            self._cfg.set("store", "logo_path", self.logo_path.text())
            self._cfg.set("receipt", "header", self.receipt_header.text())
            self._cfg.set("receipt", "footer", self.receipt_footer.text())
            new_lang = self.language.currentText()
            old_lang = self._cfg.get("app", "language", fallback="ar")
            self._cfg.set("app", "language", new_lang)
            self._cfg.set("app", "theme", "light" if self.theme.currentIndex() == 0 else "dark")
            self._cfg.set("app", "loyalty_rate", str(self.loyalty_rate.value()))
            self._cfg.set("app", "inactivity_timeout", str(self.inactivity.value()))
            self._cfg.set("app", "font_size", str(self.font_slider.value()))
            self._cfg.set("backup", "destination", self.backup_dest.text())
            self._cfg.set("backup", "interval_minutes", str(self.backup_interval.value()))

            with open(_CONFIG_PATH, "w") as f:
                self._cfg.write(f)

            font_manager.set_size(self.font_slider.value())

            if new_lang != old_lang:
                lang_utils.set_language(new_lang)
                self.language_changed.emit(new_lang)

            QMessageBox.information(self, tr("success"), "Settings saved successfully.")
        except Exception:
            logger.exception("settings_view._save failed")
            QMessageBox.warning(self, tr("error"), "Failed to save settings.")

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.logo_path.setText(path)

    def _browse_dest(self):
        path = QFileDialog.getExistingDirectory(self, "Select Backup Destination")
        if path:
            self.backup_dest.setText(path + "/")

    def _do_backup(self):
        self._worker = BackupWorker()
        self._worker.done.connect(self._on_backup_done)
        self._worker.start()

    def _on_backup_done(self, ok: bool, path: str):
        self._refresh_backup_list()
        if ok:
            QMessageBox.information(self, tr("success"), f"Backup saved:\n{path}")
        else:
            QMessageBox.warning(self, tr("error"), path)

    def _do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Backup", "backups/", "ZIP (*.zip)")
        if not path:
            return
        reply = QMessageBox.question(
            self, tr("confirm_action"),
            "Restore this backup? The app must restart after.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        ok, msg = bkp.restore_backup(path)
        if ok:
            QMessageBox.information(self, tr("success"), msg)
        else:
            QMessageBox.warning(self, tr("error"), msg)

    def _refresh_backup_list(self):
        self.backup_list.clear()
        for b in bkp.list_backups():
            self.backup_list.addItem(
                f"{b['filename']}  ({b['size_kb']} KB)  {b['mtime']}"
            )
