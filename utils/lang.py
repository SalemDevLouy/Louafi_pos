"""
Singleton language manager.

Usage in any view:
    from utils.lang import lang_manager, tr

    # get translated string
    tr('key')

    # connect to language changes
    lang_manager.lang_changed.connect(self.retranslate_ui)

    # change language (called from settings / main_window)
    lang_manager.set_language('ar')   # or 'en'
"""

from PyQt5.QtCore import QObject, pyqtSignal
from utils.tr import TRANSLATIONS


class _LangManager(QObject):
    # Emitted whenever the language changes.  Views connect to this.
    lang_changed = pyqtSignal(str)   # new lang code: 'en' | 'ar'

    def __init__(self):
        super().__init__()
        self._lang = 'en'

    @property
    def current(self) -> str:
        return self._lang

    def is_rtl(self) -> bool:
        return self._lang == 'ar'

    def set_language(self, lang: str):
        if lang not in ('en', 'ar'):
            raise ValueError(f'Unsupported language: {lang}')
        if lang != self._lang:
            self._lang = lang
            self.lang_changed.emit(lang)

    def toggle(self):
        self.set_language('ar' if self._lang == 'en' else 'en')

    def tr(self, key: str, **kwargs) -> str:
        """Translate key to current language, optionally format with kwargs."""
        entry = TRANSLATIONS.get(key)
        if entry is None:
            return key   # fallback: return key itself
        text = entry.get(self._lang, entry.get('en', key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text


# ── Module-level singleton ────────────────────────────────────────────────────
lang_manager = _LangManager()


def tr(key: str, **kwargs) -> str:
    """Shortcut: translate key in the current language."""
    return lang_manager.tr(key, **kwargs)
