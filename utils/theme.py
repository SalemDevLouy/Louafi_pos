"""
Font-size manager for LouafiPOS.

styles.qss uses ${F_SM}, ${F_MD}, ${F_BASE}, ${F_LG}, ${F_XL}, ${F_HUGE}
as placeholders.  Call apply(app, base) to substitute and push the
sheet to the running QApplication.
"""
import configparser
import os
from string import Template

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFont

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QSS  = os.path.join(_HERE, 'styles.qss')

DEFAULT_BASE = 20        # px  (increase from previous 18-19 default)
MIN_BASE     = 12
MAX_BASE     = 28


def _scale(base: int) -> dict:
    """Derive all tier sizes from one base value."""
    b = max(MIN_BASE, min(MAX_BASE, base))
    return {
        'F_SM':   max(b - 3, 9),   # status bar, table headers
        'F_MD':   max(b - 1, 10),  # tabs, list items, sub-titles
        'F_BASE': b,               # most content text
        'F_LG':   b + 2,           # section headings
        'F_XL':   b + 7,           # banner title
        'F_HUGE': b + 10,          # page title
    }


def build_stylesheet(base: int) -> str:
    """Load styles.qss template and substitute font sizes."""
    try:
        with open(_QSS, encoding='utf-8') as f:
            raw = f.read()
        return Template(raw).safe_substitute(_scale(base))
    except Exception:
        return ''


class _FontManager(QObject):
    font_changed = pyqtSignal(int)   # emits new base px size

    def __init__(self):
        super().__init__()
        self._base = DEFAULT_BASE

    # ── public API ────────────────────────────────────────────────────────

    def base(self) -> int:
        return self._base

    def set_size(self, base: int) -> None:
        base = max(MIN_BASE, min(MAX_BASE, base))
        if base == self._base:
            return
        self._base = base
        self.font_changed.emit(base)

    def apply(self, app, base: int | None = None) -> None:
        """Set app font + stylesheet.  Reads config if base is None."""
        if base is None:
            base = _read_config_size()
        self._base = base
        lang = _read_config_lang()
        family = 'Tajawal' if lang == 'ar' else 'Rubik'
        app.setFont(QFont(family, base))
        app.setStyleSheet(build_stylesheet(base))

    def save_config(self, base: int) -> None:
        """Persist font_size in config.ini."""
        cfg = configparser.RawConfigParser()
        cfg.read(os.path.join(_HERE, 'config.ini'))
        if not cfg.has_section('app'):
            cfg.add_section('app')
        cfg.set('app', 'font_size', str(base))
        with open(os.path.join(_HERE, 'config.ini'), 'w') as f:
            cfg.write(f)


# ── helpers ───────────────────────────────────────────────────────────────

def _read_config_size() -> int:
    cfg = configparser.RawConfigParser()
    cfg.read(os.path.join(_HERE, 'config.ini'))
    return cfg.getint('app', 'font_size', fallback=DEFAULT_BASE)


def _read_config_lang() -> str:
    cfg = configparser.RawConfigParser()
    cfg.read(os.path.join(_HERE, 'config.ini'))
    return cfg.get('app', 'language', fallback='ar')


font_manager = _FontManager()
