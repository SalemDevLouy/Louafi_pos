"""
Development entry point for LouafiPOS with hot-reload enabled.

This is a wrapper around main.py that enables the hot-reload system.
Use this during development to edit view files and see changes instantly.

Usage:
    python main_dev.py

Features:
    • File watcher monitors ./views/ directory
    • Automatic reload when you save a view file
    • Ctrl+R to manually force reload
    • Errors won't crash the app
    • Controllers and DB connections are preserved
"""
import sys
import os

# Ensure project root is in path
HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.append(HERE)

# Import the standard main setup
from main import _load_fonts
import configparser
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from views.main_window import MainWindow
from views.login_view import LoginView
from database.db import init_db
from utils.theme import font_manager

# Import hot-reload system
from dev_hotreload import enable_hot_reload


def main():
    """Run the app with hot-reload enabled."""
    init_db()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    _load_fonts()

    # Sync lang_manager to the configured language BEFORE any UI is built
    cfg = configparser.RawConfigParser()
    cfg.read(os.path.join(HERE, 'config.ini'))
    start_lang = cfg.get('app', 'language', fallback='ar')
    from utils.lang import lang_manager
    if start_lang in ('en', 'ar'):
        lang_manager.set_language(start_lang)

    # Set RTL/LTR layout direction for the whole app before any UI is built
    app.setLayoutDirection(Qt.RightToLeft if start_lang == 'ar' else Qt.LeftToRight)

    # Apply font + stylesheet (reads font_size and language from config.ini)
    font_manager.apply(app)

    # Re-apply on font size changes (triggered from SettingsView)
    font_manager.font_changed.connect(lambda base: font_manager.apply(app, base))

    # Re-apply on language changes (font family may switch Tajawal ↔ Rubik)
    def _on_lang(lang: str):
        app.setLayoutDirection(Qt.RightToLeft if lang == 'ar' else Qt.LeftToRight)
        font_manager.apply(app)
    lang_manager.lang_changed.connect(_on_lang)

    # Show login first; on success swap to main window
    login_window = QtWidgets.QMainWindow()
    login_window.setWindowTitle("LouafiPOS — Login (DEV MODE)")
    login_window.setMinimumSize(480, 560)

    def on_login_success(user):
        login_window.close()
        app.setQuitOnLastWindowClosed(True)
        window = MainWindow()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🔥 ENABLE HOT-RELOAD HERE 🔥
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        enable_hot_reload(window)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        window.showMaximized()
        app._main_window = window

    login_view = LoginView(on_login_success=on_login_success)
    login_window.setCentralWidget(login_view)
    login_window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    print("\n" + "🔥"*30)
    print("  RUNNING IN DEVELOPMENT MODE WITH HOT-RELOAD")
    print("🔥"*30 + "\n")

    # Check if watchdog is installed
    try:
        import watchdog
    except ImportError:
        print("⚠️  WARNING: 'watchdog' package not installed!")
        print("   Install it with: pip install watchdog")
        print("   Hot-reload will not work without it.\n")
        sys.exit(1)

    main()
