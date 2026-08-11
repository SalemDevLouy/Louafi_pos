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

# nav items: (qta icon name, tr-key, button-attr-name)
_NAV = [
    ('fa5s.cash-register','nav_sales',    'btn_sales'),
    ('fa5s.shopping-bag','nav_products',  'btn_products'),
    ('fa5s.boxes',       'nav_inventory', 'btn_inventory'),
    ('fa5s.chart-bar',   'nav_reports',   'btn_reports'),
    ('fa5s.users',       'nav_customers', 'btn_customers'),
    ('fa5s.truck',       'nav_suppliers', 'btn_suppliers'),
    ('fa5s.receipt',     'nav_expenses',  'btn_expenses'),
    ('fa5s.tags',        'nav_discounts', 'btn_discounts'),
    ('fa5s.cog',         'nav_settings',  'btn_settings'),
    ('fa5s.user-shield', 'nav_users',     'btn_users'),
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

        # build nav buttons from _NAV table
        self._nav_buttons = []   # (icon_name, tr_key, QPushButton)
        for icon_name, tr_key, attr in _NAV:
            btn = QtWidgets.QPushButton(f'  {tr(tr_key)}')
            btn.setIcon(qta.icon(icon_name, color=_ICON_COLOR))
            btn.setIconSize(_ICON_SIZE)
            btn.setFixedHeight(46)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setProperty('flat', True)
            sb_layout.addWidget(btn)
            setattr(self, attr, btn)
            self._nav_buttons.append((icon_name, tr_key, btn))

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

        # user chip
        from utils import auth as _auth
        _sess = _auth.get_session()
        _uname = _sess.get('username', '') if _sess else ''
        user_chip = QtWidgets.QLabel(f'  {_uname}  ')
        user_chip.setStyleSheet(
            'color:#ede9fe; background:#6d28d9; border-radius:12px;'
            'padding:4px 10px; font-size:12px; font-weight:600;'
        )
        banner_layout.addWidget(user_chip)

        # (no separate header bar — banner serves that role)
        self.header = QtWidgets.QFrame()   # kept as placeholder, hidden
        self.header.setVisible(False)

        # stacked pages
        self.stack = QtWidgets.QStackedWidget()
        self.sales_view = SalesView(self.sales_controller, self.product_controller)
        self.products_view = ProductsView(self.product_controller)
        self.reports_view = ReportsView()
        self.inventory_view = InventoryView(self.product_controller)
        self.customers_view = CustomersView()
        self.suppliers_view = SuppliersView(self.product_controller)

        self.expenses_view = ExpensesView()
        self.discounts_view = DiscountsView()
        self.settings_view = SettingsView()
        self.users_view = UserManagementView()
        self.hidden_dashboard = HiddenDashboardView()

        self.stack.addWidget(self.sales_view)       # 0
        self.stack.addWidget(self.products_view)    # 1
        self.stack.addWidget(self.inventory_view)   # 2
        self.stack.addWidget(self.reports_view)     # 3
        self.stack.addWidget(self.customers_view)   # 4
        self.stack.addWidget(self.suppliers_view)   # 5
        self.stack.addWidget(self.expenses_view)    # 6
        self.stack.addWidget(self.discounts_view)   # 7
        self.stack.addWidget(self.settings_view)    # 8
        self.stack.addWidget(self.users_view)       # 9
        self.stack.addWidget(self.hidden_dashboard) # 10  ← hidden, not in nav

        self.btn_sales.clicked.connect(lambda: self.show_page(0))
        self.btn_products.clicked.connect(lambda: self.show_page(1))
        self.btn_inventory.clicked.connect(lambda: self.show_page(2))
        self.btn_reports.clicked.connect(lambda: self.show_page(3))
        self.btn_customers.clicked.connect(lambda: self.show_page(4))
        self.btn_suppliers.clicked.connect(lambda: self.show_page(5))
        self.btn_expenses.clicked.connect(lambda: self.show_page(6))
        self.btn_discounts.clicked.connect(lambda: self.show_page(7))
        self.btn_settings.clicked.connect(lambda: self.show_page(8))
        self.btn_users.clicked.connect(lambda: self.show_page(9))

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

        self.show_page(0)

        QtWidgets.QShortcut(QtCore.Qt.Key_F3, self, activated=lambda: self.show_page(0))
        QtWidgets.QShortcut(QtCore.Qt.Key_F4, self, activated=lambda: self.show_page(1))

        # apply correct sidebar mode for the initial window size
        QtCore.QTimer.singleShot(0, lambda: self._set_sidebar_mode(self.width() >= BREAK_WIDTH))

        # language support
        lang_manager.lang_changed.connect(self._on_lang_changed)

        # hot-reload support (only used in dev mode)
        self._view_class_map = {
            0: ('views.sales_view', 'SalesView'),
            1: ('views.products_view', 'ProductsView'),
            2: ('views.inventory_view', 'InventoryView'),
            3: ('views.reports_view', 'ReportsView'),
            4: ('views.customers_view', 'CustomersView'),
            5: ('views.suppliers_view', 'SuppliersView'),
            6: ('views.expenses_view', 'ExpensesView'),
            7: ('views.discounts_view', 'DiscountsView'),
            8: ('views.settings_view', 'SettingsView'),
            9: ('views.user_management_view', 'UserManagementView'),
            10: ('views.hidden_dashboard_view', 'HiddenDashboardView'),
        }

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
        for view in (self.sales_view, self.products_view,
                     self.inventory_view, self.reports_view, self.customers_view,
                     self.suppliers_view, self.expenses_view, self.discounts_view,
                     self.settings_view, self.users_view):
            if hasattr(view, 'retranslate_ui'):
                view.retranslate_ui()
        self.status.showMessage(tr('status_refreshed'), 2000)

    # ── Navigation ────────────────────────────────────────────────────────

    def show_page(self, index: int):
        """Switch stacked page, refresh its data, and update sidebar selection."""
        self.stack.setCurrentIndex(index)
        for i, (icon_name, label, btn) in enumerate(self._nav_buttons):
            selected = (i == index)
            btn.setProperty('selected', 'true' if selected else 'false')
            btn.setIcon(qta.icon(icon_name, color=_ICON_COLOR_SEL if selected else _ICON_COLOR))
            btn.setIconSize(_ICON_SIZE)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # always refresh the page being shown so data is live
        refresh_map = {
            0: lambda: self.sales_view.refresh_cart(),
            1: lambda: self.products_view.load_products(),
            2: lambda: self.inventory_view.refresh(),
            3: lambda: self.reports_view.generate(),
            4: lambda: self.customers_view.refresh_customers(),
            5: lambda: self.suppliers_view.refresh(),
            6: lambda: self.expenses_view.load(),
            7: lambda: self.discounts_view.load(),
            8: None,
            9: lambda: self.users_view.load(),
            10: lambda: self.hidden_dashboard.refresh(),
        }
        fn = refresh_map.get(index)
        if fn:
            fn()

    def _open_hidden_dashboard(self):
        from utils.auth import current_role
        if current_role() != 'admin':
            return
        # deselect all nav buttons (this page has no nav entry)
        for _icon, _key, btn in self._nav_buttons:
            btn.setProperty('selected', 'false')
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.show_page(10)

    def _refresh_current_page(self):
        """Refresh data on the currently visible page."""
        idx = self.stack.currentIndex()
        refresh_map = {
            0: lambda: self.sales_view.refresh_cart(),
            1: lambda: self.products_view.load_products(),
            2: lambda: self.inventory_view.refresh(),
            3: lambda: self.reports_view.generate(),
            4: lambda: self.customers_view.refresh_customers(),
            5: lambda: self.suppliers_view.refresh(),
            6: lambda: self.expenses_view.load(),
            7: lambda: self.discounts_view.load(),
            8: None,
            9: lambda: self.users_view.load(),
            10: lambda: self.hidden_dashboard.refresh(),
        }
        fn = refresh_map.get(idx)
        if fn:
            fn()
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
            view_attr_map = {
                0: 'sales_view',
                1: 'products_view',
                2: 'inventory_view',
                3: 'reports_view',
                4: 'customers_view',
                5: 'suppliers_view',
                6: 'expenses_view',
                7: 'discounts_view',
                8: 'settings_view',
                9: 'users_view',
                10: 'hidden_dashboard',
            }
            attr_name = view_attr_map.get(current_idx)
            if attr_name:
                setattr(self, attr_name, new_widget)

            # Clean up old widget
            old_widget.deleteLater()

            # Trigger refresh on the new view
            refresh_map = {
                0: lambda: new_widget.refresh_cart(),
                1: lambda: new_widget.load_products(),
                2: lambda: new_widget.refresh(),
                3: lambda: new_widget.generate(),
                4: lambda: new_widget.refresh_customers(),
                5: lambda: new_widget.refresh(),
                6: lambda: new_widget.load(),
                7: lambda: new_widget.load(),
                8: None,
                9: lambda: new_widget.load(),
                10: lambda: new_widget.refresh(),
            }
            refresh_fn = refresh_map.get(current_idx)
            if refresh_fn:
                refresh_fn()

            print(f"[HotReload] ✓ View rebuilt successfully!")
            self.status.showMessage("🔄 View reloaded", 2000)

        except Exception as e:
            print(f"[HotReload] ✗ Failed to rebuild view:")
            print(f"[HotReload]   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.status.showMessage("⚠ Reload failed - check terminal", 3000)

    def _create_view_instance(self, index):
        """Create a new instance of the view at the given stack index."""
        view_constructors = {
            0: lambda: SalesView(self.sales_controller, self.product_controller),
            1: lambda: ProductsView(self.product_controller),
            2: lambda: InventoryView(self.product_controller),
            3: lambda: ReportsView(),
            4: lambda: CustomersView(),
            5: lambda: SuppliersView(self.product_controller),
            6: lambda: ExpensesView(),
            7: lambda: DiscountsView(),
            8: lambda: SettingsView(),
            9: lambda: UserManagementView(),
            10: lambda: HiddenDashboardView(),
        }

        constructor = view_constructors.get(index)
        if constructor:
            return constructor()
        return None
