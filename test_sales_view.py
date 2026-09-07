#!/usr/bin/env python3
"""
Standalone test launcher for SalesView — no login required.

Runs the sales view in isolation with the real database so you can
tweak sales_view.py and test UI changes instantly.

Usage:
    python test_sales_view.py

After making changes to sales_view.py, just close and re-run this script
(or use Ctrl+R if running via main_dev.py with hot-reload).
"""
import sys
import os

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)

# ── Minimal app init (same as main.py but no login) ────────────────
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from database.db import init_db
from controllers.product_controller import ProductController
from controllers.sales_controller import SalesController
from views.sales_view import SalesView

init_db()

app = QtWidgets.QApplication(sys.argv)
app.setStyle("Fusion")

# Font setup
from main import _load_fonts
_load_fonts()

# Config
import configparser
cfg = configparser.RawConfigParser()
cfg.read(os.path.join(HERE, 'config.ini'))

# Language + RTL
start_lang = cfg.get('app', 'language', fallback='ar')
from utils.lang import lang_manager
if start_lang in ('en', 'ar'):
    lang_manager.set_language(start_lang)
app.setLayoutDirection(Qt.RightToLeft if start_lang == 'ar' else Qt.LeftToRight)

# Font + stylesheet
from utils.theme import font_manager
font_manager.apply(app)
font_manager.font_changed.connect(lambda base: font_manager.apply(app, base))
def _on_lang(lang: str):
    app.setLayoutDirection(Qt.RightToLeft if lang == 'ar' else Qt.LeftToRight)
    font_manager.apply(app)
lang_manager.lang_changed.connect(_on_lang)

# ── Launch SalesView directly ──────────────────────────────────────
pc = ProductController()
sc = SalesController(pc)
view = SalesView(sc, pc)

window = QtWidgets.QMainWindow()
window.setWindowTitle("SalesView — Test Mode (no login)")
window.setMinimumSize(1280, 800)
window.setCentralWidget(view)
window.showMaximized()
window.setStyleSheet("QMainWindow{background:#f8fafc;}")

print("\n✅ SalesView standalone test running!")
print("   Edit sales_view.py and re-run this script to see changes.\n")

sys.exit(app.exec_())
