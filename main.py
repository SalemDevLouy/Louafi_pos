import sys
import os
from PyQt5 import QtWidgets

# ensure package imports work when running this file directly
HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.append(HERE)

from views.main_window import MainWindow
from database.db import init_db


def main():
    # initialize database (creates tables if missing)
    init_db()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')

    # load stylesheet if available
    try:
        qss_path = os.path.join(os.path.dirname(__file__), 'styles.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
    except Exception:
        # fail gracefully if stylesheet can't be read
        pass

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
