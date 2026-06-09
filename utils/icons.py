"""Centralised icon helper — wraps qtawesome so every view uses consistent icons."""
import qtawesome as qta
from PyQt5.QtCore import QSize

# ── Sizes ─────────────────────────────────────────────────────────────────────
SM  = QSize(16, 16)   # small  – inline / table buttons
MD  = QSize(20, 20)   # medium – toolbar buttons
LG  = QSize(24, 24)   # large  – page-title labels

# ── Colour palette ────────────────────────────────────────────────────────────
_DARK   = '#263238'   # default dark text colour
_WHITE  = '#ffffff'
_BLUE   = '#1a73e8'
_GREEN  = '#1b5e20'
_RED    = '#c0392b'
_GREY   = '#78909c'
_AMBER  = '#856404'


def get(name: str, color: str = _DARK, size: QSize = MD) -> 'QIcon':
    return qta.icon(name, color=color)


# ── Named shortcuts ───────────────────────────────────────────────────────────
def ic_search(color=_GREY):      return qta.icon('fa5s.search',        color=color)
def ic_add(color=_WHITE):        return qta.icon('fa5s.plus',           color=color)
def ic_edit(color=_WHITE):       return qta.icon('fa5s.pen',            color=color)
def ic_delete(color=_WHITE):     return qta.icon('fa5s.trash-alt',      color=color)
def ic_refresh(color=_WHITE):    return qta.icon('fa5s.sync-alt',       color=color)
def ic_adjust(color=_WHITE):     return qta.icon('fa5s.sliders-h',      color=color)
def ic_credit(color=_WHITE):     return qta.icon('fa5s.credit-card',    color=color)
def ic_payment(color=_WHITE):    return qta.icon('fa5s.check-circle',   color=color)
def ic_accept(color=_WHITE):     return qta.icon('fa5s.check',          color=color)
def ic_debt(color=_WHITE):       return qta.icon('fa5s.file-invoice-dollar', color=color)
def ic_generate(color=_WHITE):   return qta.icon('fa5s.bolt',           color=color)
def ic_manage(color=_WHITE):     return qta.icon('fa5s.cog',            color=color)
def ic_speed(color=_BLUE):       return qta.icon('fa5s.bolt',           color=color)
def ic_warning(color=_AMBER):    return qta.icon('fa5s.exclamation-triangle', color=color)

# page-title icons (larger, coloured)
def ic_page_dashboard(color=_BLUE):   return qta.icon('fa5s.home',          color=color)
def ic_page_products(color=_BLUE):    return qta.icon('fa5s.shopping-bag',  color=color)
def ic_page_inventory(color=_BLUE):   return qta.icon('fa5s.boxes',         color=color)
def ic_page_reports(color=_BLUE):     return qta.icon('fa5s.chart-bar',     color=color)
def ic_page_customers(color=_BLUE):   return qta.icon('fa5s.users',         color=color)
def ic_page_suppliers(color=_BLUE):   return qta.icon('fa5s.truck',         color=color)

# supplier feature icons
def ic_supplier(color=_WHITE):        return qta.icon('fa5s.truck',         color=color)
def ic_billing(color=_WHITE):         return qta.icon('fa5s.file-invoice',  color=color)
def ic_add_billing(color=_WHITE):     return qta.icon('fa5s.plus-circle',   color=color)
def ic_view_items(color=_WHITE):      return qta.icon('fa5s.list',          color=color)
def ic_import_stock(color=_WHITE):    return qta.icon('fa5s.boxes',         color=color)
