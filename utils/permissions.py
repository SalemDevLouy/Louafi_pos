"""
Central RBAC page permissions.

Single source of truth for which roles may open which pages of the
application.  The main window builds its navigation (and instantiates
only the permitted views) from this table, and every page switch is
re-checked against it — so hidden pages cannot be reached through
shortcuts or programmatic ``show_page()`` calls either.

Usage:
    from utils.permissions import role_can, allowed_pages

    role_can('cashier', 'settings')   # -> False
    allowed_pages('supervisor')       # -> ['sales', 'customers', 'products', ...]
"""

# Roles recognised by the system (kept in sync with auth_controller).
ROLES = ('admin', 'supervisor', 'cashier')

# ── Page access matrix ────────────────────────────────────────────────────────
# key → roles allowed to open the page.  Keys must match the 'key' field of
# the _PAGES registry in views/main_window.py.  Unknown keys / roles are
# denied by default (secure default).
PAGE_ROLES: dict[str, tuple[str, ...]] = {
    # point of sale + customer debts — needed by cashiers on the floor
    'sales':            ('admin', 'supervisor', 'cashier'),
    'customers':        ('admin', 'supervisor', 'cashier'),

    # management pages — supervisors and above
    'products':         ('admin', 'supervisor'),
    'inventory':        ('admin', 'supervisor'),
    'reports':          ('admin', 'supervisor'),
    'suppliers':        ('admin', 'supervisor'),
    'expenses':         ('admin', 'supervisor'),
    'discounts':        ('admin', 'supervisor'),

    # configuration & administration — admin only
    'settings':         ('admin',),
    'users':            ('admin',),
    'hidden_dashboard': ('admin',),   # secret page (brand-logo click)
}


def role_can(role: str | None, page_key: str) -> bool:
    """True if ``role`` may open ``page_key``.  Deny-by-default."""
    if not role:
        return False
    allowed = PAGE_ROLES.get(page_key)
    return allowed is not None and role in allowed


def allowed_pages(role: str | None) -> list[str]:
    """All page keys the role may access, in declaration order."""
    return [key for key, roles in PAGE_ROLES.items() if role in roles]
