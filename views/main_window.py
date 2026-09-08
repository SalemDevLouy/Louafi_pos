from PyQt5 import QtWidgets, QtCore, QtGui
import qtawesome as qta
from controllers.product_controller import ProductController
from controllers.sales_controller import SalesController
from views.products_view import ProductsView
from views.reports_view import ReportsView
from views.inventory_view import InventoryView
from views.customers_view import CustomersView
from views.suppliers_view import SuppliersView
from views.expenses_view import ExpensesView
from views.sales_view import SalesView
from views.discounts_view import DiscountsView
from views.settings_view import SettingsView
from views.user_management_view import UserManagementView
from views.hidden_dashboard_view import HiddenDashboardView
from utils.lang import lang_manager, tr
from utils import auth as auth_utils
from utils.permissions import role_can

# ── Page registry (order = sidebar order) ─────────────────────────────────────
# Each entry describes one application page.  'key' must exist in
# utils/permissions.PAGE_ROLES — the RBAC layer decides which of these pages
# the logged-in role actually gets in the sidebar and in the stack.
# 'nav': False marks a secret page (reachable only programmatically).
_PAGES = [
    dict(key='sales',     icon='fa5s.cash-register', tr_key='nav_sales',
         btn='btn_sales',     view='sales_view',     module='views.sales_view',
         cls='SalesView',     refresh='refresh_cart'),
    dict(key='products',  icon='fa5s.shopping-bag',  tr_key='nav_products',
         btn='btn_products',  view='products_view',  module='views.products_view',
         cls='ProductsView',  refresh='load_products'),
    dict(key='inventory', icon='fa5s.boxes',         tr_key='nav_inventory',
         btn='btn_inventory', view='inventory_view', module='views.inventory_view',
         cls='InventoryView', refresh='refresh'),
    dict(key='reports',   icon='fa5s.chart-bar',     tr_key='nav_reports',
         btn='btn_reports',   view='reports_view',   module='views.reports_view',
         cls='ReportsView',   refresh='generate'),
    dict(key='customers', icon='fa5s.users',         tr_key='nav_customers',
         btn='btn_customers', view='customers_view', module='views.customers_view',
         cls='CustomersView', refresh='refresh_customers'),
    dict(key='suppliers', icon='fa5s.truck',         tr_key='nav_suppliers',
         btn='btn_suppliers', view='suppliers_view', module='views.suppliers_view',
         cls='SuppliersView', refresh='refresh'),
    dict(key='expenses',  icon='fa5s.receipt',       tr_key='nav_expenses',
         btn='btn_expenses',  view='expenses_view',  module='views.expenses_view',
         cls='ExpensesView',  refresh='load'),
    dict(key='discounts', icon='fa5s.tags',          tr_key='nav_discounts',
         btn='btn_discounts', view='discounts_view', module='views.discounts_view',
         cls='DiscountsView', refresh='load'),
    dict(key='settings',  icon='fa5s.cog',           tr_key='nav_settings',
         btn='btn_settings',  view='settings_view',  module='views.settings_view',
         cls='SettingsView',  refresh=None),
    dict(key='users',     icon='fa5s.user-shield',   tr_key='nav_users',
         btn='btn_users',     view='users_view',     module='views.user_management_view',
         cls='UserManagementView', refresh='load'),
    dict(key='hidden_dashboard', icon='', tr_key='', btn='',
         view='hidden_dashboard', module='views.hidden_dashboard_view',
         cls='HiddenDashboardView', refresh='refresh', nav=False),
]

_ICON_COLOR        = '#cfd8f5'   # normal icon colour (matches sidebar text)
_ICON_COLOR_SEL    = '#ffffff'   # selected
_ICON_SIZE         = QtCore.QSize(22, 22)

SIDEBAR_WIDE   = 220
SIDEBAR_NARROW =  62
BREAK_WIDTH    = 900


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr('app_title'))
        self.setMinimumSize(800, 550)
        self.resize(1280, 800)
        self._sidebar_expanded = True   # track manual toggle state

        # controllers
        self.product_controller = ProductController()
        self.sales_controller = SalesController(self.product_controller)

        # ── RBAC: keep only the pages this role is allowed to open ─────────
        self._role = auth_utils.current_role()
        self._pages = [dict(p) for p in _PAGES if role_can(self._role, p['key'])]

        # central layout: root (vertical) so banner can span full window,
        # with a horizontal body area that holds the sidebar + content.
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # body area (sidebar + content)
        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # sidebar
        self.sidebar = QtWidgets.QFrame()
        self.sidebar.setObjectName('sidebar')
        self.sidebar.setFixedWidth(SIDEBAR_WIDE)
        sb_layout = QtWidgets.QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # ── Sidebar brand header ───────────────────────────────────────────
        brand_frame = QtWidgets.QFrame()
        brand_frame.setObjectName('sidebarLogo')
        brand_frame.setFixedHeight(58)
        brand_layout = QtWidgets.QHBoxLayout(brand_frame)
        brand_layout.setContentsMargins(14, 0, 8, 0)
        brand_icon = QtWidgets.QLabel()
        brand_icon.setPixmap(qta.icon('fa5s.store', color='#8b5cf6').pixmap(22, 22))
        brand_icon.setCursor(QtCore.Qt.PointingHandCursor)
        brand_icon.setToolTip('System Dashboard')
        brand_icon.mousePressEvent = lambda _e: self._open_hidden_dashboard()
        brand_name = QtWidgets.QLabel('LouafiPOS')
        brand_name.setStyleSheet('color: #f8fafc; font-size: 16px; font-weight: 700; background: transparent;')
        brand_name.setCursor(QtCore.Qt.PointingHandCursor)
        brand_name.setToolTip('System Dashboard')
        brand_name.mousePressEvent = lambda _e: self._open_hidden_dashboard()
        self.btn_toggle_sidebar = QtWidgets.QPushButton()
        self.btn_toggle_sidebar.setIcon(qta.icon('fa5s.angle-left', color='#64748b'))
        self.btn_toggle_sidebar.setIconSize(QtCore.QSize(16, 16))
        self.btn_toggle_sidebar.setFixedSize(28, 28)
        self.btn_toggle_sidebar.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle_sidebar.setToolTip(tr('collapse_sidebar'))
        self.btn_toggle_sidebar.setStyleSheet(
            'QPushButton { background: rgba(255,255,255,0.08); border: none; border-radius: 6px; }'
            'QPushButton:hover { background: rgba(255,255,255,0.15); }'
        )
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        brand_layout.addWidget(brand_icon)
        brand_layout.addWidget(brand_name)
        brand_layout.addStretch()
        brand_layout.addWidget(self.btn_toggle_sidebar)
        sb_layout.addWidget(brand_frame)
        sb_layout.addSpacing(8)

        # build nav buttons ONLY for pages this role may open (RBAC)
        self._nav_buttons = []   # (icon_name, tr_key, QPushButton)
        for page in self._pages:
            if page.get('nav') is False:
                continue
            btn = QtWidgets.QPushButton(f'  {tr(page["tr_key"])}')
            btn.setIcon(qta.icon(page['icon'], color=_ICON_COLOR))
            btn.setIconSize(_ICON_SIZE)
            btn.setFixedHeight(46)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setProperty('flat', True)
            sb_layout.addWidget(btn)
            setattr(self, page['btn'], btn)
            page['_btn'] = btn
            self._nav_buttons.append((page['icon'], page['tr_key'], btn))

        sb_layout.addStretch()

        # ── Bottom utility buttons ─────────────────────────────────────────
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet('background: rgba(255,255,255,0.08); margin: 0 12px; max-height:1px;')
        sb_layout.addWidget(sep)
        sb_layout.addSpacing(4)

        self.btn_lang = QtWidgets.QPushButton(f'  {tr("lang_switch_to_ar")}')
        self.btn_lang.setIcon(qta.icon('fa5s.globe', color=_ICON_COLOR))
        self.btn_lang.setIconSize(_ICON_SIZE)
        self.btn_lang.setFixedHeight(42)
        self.btn_lang.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_lang.setProperty('flat', True)
        self.btn_lang.setStyleSheet(
            'QPushButton { color:#94a3b8; background:transparent; border:none;'
            '  border-radius:10px; text-align:left; padding:10px 14px;'
            '  margin:2px 8px; font-size:14px; }'
            'QPushButton:hover { background:rgba(255,255,255,0.08); color:#e2e8f0; }'
        )
        self.btn_lang.clicked.connect(self._toggle_language)
        sb_layout.addWidget(self.btn_lang)

        self.btn_refresh = QtWidgets.QPushButton(f'  {tr("btn_refresh")}')
        self.btn_refresh.setIcon(qta.icon('fa5s.sync-alt', color=_ICON_COLOR))
        self.btn_refresh.setIconSize(_ICON_SIZE)
        self.btn_refresh.setFixedHeight(42)
        self.btn_refresh.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_refresh.setProperty('flat', True)
        self.btn_refresh.setObjectName('refreshBtn')
        self.btn_refresh.clicked.connect(self._refresh_current_page)
        sb_layout.addWidget(self.btn_refresh)
        sb_layout.addSpacing(8)

        # top banner (slim app bar)
        self.banner = QtWidgets.QFrame()
        self.banner.setObjectName('topBanner')
        self.banner.setFixedHeight(58)
        banner_layout = QtWidgets.QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(20, 0, 20, 0)
        banner_layout.setSpacing(12)
        banner_label = QtWidgets.QLabel(tr('app_banner'))
        banner_label.setStyleSheet('color: #f8fafc; font-size:18px; font-weight:700;'
                                   'font-style:normal; background:transparent;')
        banner_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        banner_layout.addWidget(banner_label)
        banner_layout.addStretch()
        # clock label in banner
        self._clock_label = QtWidgets.QLabel()
        self._clock_label.setStyleSheet(
            'color:#94a3b8; font-size:13px; background:transparent;'
        )
        banner_layout.addWidget(self._clock_label)
        self._update_clock()
        clock_timer = QtCore.QTimer(self)
        clock_timer.timeout.connect(self._update_clock)
        clock_timer.start(30_000)

        # user chip — shows the login AND the role so the active permission
        # level is always visible
        from utils import auth as _auth
        _sess = _auth.get_session()
        _uname = _sess.get('username', '') if _sess else ''
        _urole = (_sess.get('role') or '') if _sess else ''
        _chip_txt = f'  {_uname} · {_urole}  ' if _urole else f'  {_uname}  '
        user_chip = QtWidgets.QLabel(_chip_txt)
        user_chip.setStyleSheet(
            'color:#ede9fe; background:#6d28d9; border-radius:12px;'
            'padding:4px 10px; font-size:12px; font-weight:600;'
        )
        banner_layout.addWidget(user_chip)

        # (no separate header bar — banner serves that role)
        self.header = QtWidgets.QFrame()   # kept as placeholder, hidden
        self.header.setVisible(False)

        # stacked pages — instantiate ONLY the views this role may use (RBAC).
        # Sidebar order == stack order, so nav index == stack index.
        self.stack = QtWidgets.QStackedWidget()
        self._views = []
        for page in self._pages:
            view = self._make_view(page)
            setattr(self, page['view'], view)
            self._views.append(view)
            self.stack.addWidget(view)
            page['index'] = self.stack.count() - 1

        # wire each nav button to its page
        for page in self._pages:
            btn = page.get('_btn')
            if btn is not None:
                btn.clicked.connect(
                    lambda _, ix=page['index']: self.show_page(ix)
                )

        # right-side content column (header + stack). Banner is added
        # to the root layout above so it spans the entire window.
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.header)
        content_layout.addWidget(self.stack, 1)

        # assemble body
        body_layout.addWidget(self.sidebar)
        body_layout.addLayout(content_layout, 1)

        # add banner (full width) then the body area below it
        root_layout.addWidget(self.banner)
        root_layout.addLayout(body_layout, 1)

        # status bar
        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(tr('status_ready'))

        self.show_page(0)   # first page the role is allowed to open

        QtWidgets.QShortcut(QtCore.Qt.Key_F3, self, activated=lambda: self.show_page(0))
        _prod = self._page_by_key('products')
        if _prod is not None:   # F4 only for roles with products access (RBAC)
            QtWidgets.QShortcut(
                QtCore.Qt.Key_F4, self,
                activated=lambda: self.show_page(_prod['index'])
            )

        # apply correct sidebar mode for the initial window size
        QtCore.QTimer.singleShot(0, lambda: self._set_sidebar_mode(self.width() >= BREAK_WIDTH))

        # language support
        lang_manager.lang_changed.connect(self._on_lang_changed)

        # hot-reload support (only used in dev mode)
        self._view_class_map = {
            p['index']: (p['module'], p['cls']) for p in self._pages
        }

    # ── RBAC helpers ─────────────────────────────────────────────────────────

    def _make_view(self, page: dict):
        """Instantiate the view class for a page (with controller injection)."""
        cls = {
            'sales': SalesView, 'products': ProductsView,
            'inventory': InventoryView, 'reports': ReportsView,
            'customers': CustomersView, 'suppliers': SuppliersView,
            'expenses': ExpensesView, 'discounts': DiscountsView,
            'settings': SettingsView, 'users': UserManagementView,
            'hidden_dashboard': HiddenDashboardView,
        }[page['key']]
        key = page['key']
        if key == 'sales':
            return cls(self.sales_controller, self.product_controller)
        if key in ('products', 'inventory', 'suppliers'):
            return cls(self.product_controller)
        return cls()

    def _page_by_key(self, key: str) -> dict | None:
        """Return this role's page entry for ``key``, or None if not permitted."""
        for page in self._pages:
            if page['key'] == key:
                return page
        return None

    # ── Clock ──────────────────────────────────────────────────────────────

    def _update_clock(self):
        from datetime import datetime
        self._clock_label.setText(datetime.now().strftime('%A  %H:%M'))

    # ── Language ───────────────────────────────────────────────────────────

    def _toggle_language(self):
        lang_manager.toggle()

    def _on_lang_changed(self, lang: str):
        """Update layout direction, retranslate this window, then all views."""
        app = QtWidgets.QApplication.instance()
        if lang == 'ar':
            app.setLayoutDirection(QtCore.Qt.RightToLeft)
        else:
            app.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.setWindowTitle(tr('app_title'))
        self.btn_lang.setText(tr('lang_switch_to_ar'))
        self._set_sidebar_mode(self._sidebar_expanded)   # re-applies all labels + arrow
        for view in self._views:
            if hasattr(view, 'retranslate_ui'):
                view.retranslate_ui()
        self.status.showMessage(tr('status_refreshed'), 2000)

    # ── Navigation ────────────────────────────────────────────────────────

    def show_page(self, index: int):
        """Switch stacked page, refresh its data, and update sidebar selection."""
        page = self._pages[index] if 0 <= index < len(self._pages) else None
        if page is None:
            return
        # ── RBAC re-check: deny pages this role may not open ────────────────
        # (covers shortcuts and any programmatic show_page() call)
        if not role_can(self._role, page['key']):
            self.status.showMessage(tr('insuf_perms'), 3000)
            return

        self.stack.setCurrentIndex(index)
        for p in self._pages:
            btn = p.get('_btn')
            if btn is None:
                continue   # secret page / no nav entry
            selected = (p['index'] == index)
            btn.setProperty('selected', 'true' if selected else 'false')
            btn.setIcon(qta.icon(p['icon'], color=_ICON_COLOR_SEL if selected else _ICON_COLOR))
            btn.setIconSize(_ICON_SIZE)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # always refresh the page being shown so data is live
        if page['refresh']:
            getattr(self.stack.widget(index), page['refresh'])()

    def _open_hidden_dashboard(self):
        page = self._page_by_key('hidden_dashboard')
        if page is None or not role_can(self._role, page['key']):
            return
        # deselect all nav buttons (this page has no nav entry)
        for _icon, _key, btn in self._nav_buttons:
            btn.setProperty('selected', 'false')
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.show_page(page['index'])

    def _refresh_current_page(self):
        """Refresh data on the currently visible page."""
        idx = self.stack.currentIndex()
        page = self._pages[idx] if 0 <= idx < len(self._pages) else None
        if page and page['refresh']:
            getattr(self.stack.widget(idx), page['refresh'])()
        self.status.showMessage(tr('status_refreshed'), 2000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # only auto-collapse if the user hasn't manually toggled
        if self._sidebar_expanded and event.size().width() < BREAK_WIDTH:
            self._set_sidebar_mode(False)
        elif not self._sidebar_expanded and event.size().width() >= BREAK_WIDTH:
            pass   # respect manual choice; don't auto-expand

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        self._set_sidebar_mode(self._sidebar_expanded)

    def _set_sidebar_mode(self, expanded: bool):
        """Switch sidebar between icon-only (narrow) and icon+text (wide)."""
        self._sidebar_expanded = expanded
        self.sidebar.setFixedWidth(SIDEBAR_WIDE if expanded else SIDEBAR_NARROW)

        # toggle arrow — flip direction in RTL
        rtl = lang_manager.is_rtl()
        if expanded:
            arrow = 'fa5s.angle-right' if rtl else 'fa5s.angle-left'
            self.btn_toggle_sidebar.setToolTip(tr('collapse_sidebar'))
        else:
            arrow = 'fa5s.angle-left' if rtl else 'fa5s.angle-right'
            self.btn_toggle_sidebar.setToolTip(tr('expand_sidebar'))
        self.btn_toggle_sidebar.setIcon(qta.icon(arrow, color=_ICON_COLOR))

        for icon_name, tr_key, btn in self._nav_buttons:
            btn.setIcon(qta.icon(icon_name, color=_ICON_COLOR))
            btn.setIconSize(_ICON_SIZE)
            if expanded:
                btn.setText(f'  {tr(tr_key)}')
                btn.setToolTip('')
                btn.setStyleSheet('')
            else:
                btn.setText('')
                btn.setToolTip(tr(tr_key))
                btn.setStyleSheet(
                    'QPushButton { padding: 0px; text-align: center; }'
                )

        if expanded:
            self.btn_refresh.setText(f'  {tr("btn_refresh")}')
            self.btn_refresh.setToolTip('')
            self.btn_lang.setText(tr('lang_switch_to_ar'))
            self.btn_lang.setToolTip('')
        else:
            self.btn_refresh.setText('')
            self.btn_refresh.setToolTip(tr('btn_refresh'))
            self.btn_lang.setText('')
            self.btn_lang.setToolTip(tr('lang_switch_to_ar'))

    # ── Hot-Reload Support (Dev Mode) ──────────────────────────────────────

    def reload_current_view(self, module_name=None):
        """
        Rebuild the currently visible view after a file change.

        This is called by the hot-reload system when a view file changes.
        It recreates the view instance without restarting the app or losing
        controller state.

        Args:
            module_name: The module that was reloaded (e.g., 'views.sales_view')
                        If None, reloads the current view regardless of which module changed.
        """
        current_idx = self.stack.currentIndex()

        # Check if the changed module affects the current view
        if module_name is not None:
            view_info = self._view_class_map.get(current_idx)
            if not view_info:
                return
            view_module, _ = view_info
            if module_name != view_module:
                print(f"[HotReload] Changed module ({module_name}) is not the current view, skipping")
                return

        print(f"[HotReload] Rebuilding view at index {current_idx}...")

        try:
            # Get the old widget
            old_widget = self.stack.widget(current_idx)

            # Create new view instance based on index
            new_widget = self._create_view_instance(current_idx)

            if new_widget is None:
                print(f"[HotReload] ✗ Failed to create new view instance")
                return

            # Replace in stack
            self.stack.removeWidget(old_widget)
            self.stack.insertWidget(current_idx, new_widget)
            self.stack.setCurrentIndex(current_idx)

            # Update instance reference
            attr_name = self._pages[current_idx]['view']
            if attr_name:
                setattr(self, attr_name, new_widget)

            # Clean up old widget
            old_widget.deleteLater()

            # Trigger refresh on the new view
            refresh_name = self._pages[current_idx]['refresh']
            if refresh_name:
                getattr(new_widget, refresh_name)()

            print(f"[HotReload] ✓ View rebuilt successfully!")
            self.status.showMessage("🔄 View reloaded", 2000)

        except Exception as e:
            print(f"[HotReload] ✗ Failed to rebuild view:")
            print(f"[HotReload]   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.status.showMessage("⚠ Reload failed - check terminal", 3000)

    def _create_view_instance(self, index):
        """Create a new instance of the view at the given stack index.

        Uses sys.modules to always get the freshest class (critical for
        hot-reload: after importlib.reload(), stale top-level imports
        would otherwise keep using the old class).
        """
        import sys

        view_info = self._view_class_map.get(index)
        if not view_info:
            return None

        module_name, class_name = view_info
        mod = sys.modules.get(module_name)
        if mod is None:
            return None

        cls = getattr(mod, class_name, None)
        if cls is None:
            return None

        # Constructor signatures per page key (RBAC-filtered registry)
        page = self._pages[index]
        key = page['key']
        if key == 'sales':   # SalesView
            return cls(self.sales_controller, self.product_controller)
        elif key in ('products', 'inventory', 'suppliers'):
            return cls(self.product_controller)
        else:
            return cls()
