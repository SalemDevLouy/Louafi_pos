import sys
import os
import configparser
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt

HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.append(HERE)

from views.main_window import MainWindow
from views.login_view import LoginView
from database.db import init_db
from utils.theme import font_manager


def _load_fonts():
    """Register Tajawal (Arabic) and Rubik (Latin) font families."""
    db = QtGui.QFontDatabase
    font_root = os.path.join(HERE, "fonts", "Rubik,Tajawal")

    tajawal_dir = os.path.join(font_root, "Tajawal")
    rubik_dir   = os.path.join(font_root, "Rubik", "static")

    for directory in (tajawal_dir, rubik_dir):
        if os.path.isdir(directory):
            for fname in os.listdir(directory):
                if fname.lower().endswith(".ttf"):
                    db.addApplicationFont(os.path.join(directory, fname))


def main():
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

    # show login first; on success swap to main window
    login_window = QtWidgets.QMainWindow()
    login_window.setWindowTitle("LouafiPOS — Login")
    login_window.setMinimumSize(480, 560)

    def on_login_success(user):
        login_window.close()
        app.setQuitOnLastWindowClosed(True)
        window = MainWindow()
        window.showMaximized()
        app._main_window = window

    login_view = LoginView(on_login_success=on_login_success)
    login_window.setCentralWidget(login_view)
    login_window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
