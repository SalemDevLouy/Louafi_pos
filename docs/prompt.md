You are an expert Python/PyQt5 desktop application developer. Build me a complete, production-ready Point of Sale (POS) system for small retail stores that can be sold commercially. The system must be fully functional, visually polished, and ready for packaging as a Windows .exe installer.

---

## TECH STACK
- Language: Python 3.10+
- GUI: PyQt5
- Database: SQLite (via built-in sqlite3)
- PDF generation: reportlab
- Charts/graphs: matplotlib (embedded in PyQt5)
- Barcode: python-barcode + Pillow
- Packaging: PyInstaller
- Installer: NSIS (build script included)
- Icons: qtawesome
- Styling: QSS stylesheets

---

## PROJECT STRUCTURE

pos_system/
├── main.py
├── styles.qss
├── config.ini
├── license.key
├── database/
│   ├── db.py              # init_db, get_connection, migrations
│   └── migrations/        # versioned SQL migration files
├── controllers/
│   ├── auth_controller.py
│   ├── product_controller.py
│   ├── sales_controller.py
│   ├── customer_controller.py
│   ├── supplier_controller.py
│   ├── expense_controller.py
│   ├── discount_controller.py
│   └── report_controller.py
├── views/
│   ├── main_window.py
│   ├── login_view.py
│   ├── dashboard_view.py
│   ├── sales_view.py
│   ├── products_view.py
│   ├── inventory_view.py
│   ├── customers_view.py
│   ├── suppliers_view.py
│   ├── expenses_view.py
│   ├── discounts_view.py
│   ├── reports_view.py
│   ├── settings_view.py
│   └── user_management_view.py
├── models/
│   ├── product.py
│   ├── sale.py
│   ├── sale_item.py
│   ├── customer.py
│   ├── supplier.py
│   ├── user.py
│   ├── expense.py
│   └── discount.py
├── utils/
│   ├── auth.py            # password hashing, session management
│   ├── license.py         # license key validation
│   ├── barcode.py         # barcode generation + webcam scan
│   ├── backup.py          # auto backup + restore
│   ├── pdf.py             # invoice + report PDF generation
│   ├── receipt.py         # thermal receipt printer support
│   ├── lang.py            # i18n strings loader
│   ├── tr.py              # translate() helper
│   ├── audit.py           # audit log writer
│   ├── icons.py           # qtawesome icon helper
│   └── categories.py
├── lang/
│   ├── ar.json            # Arabic strings
│   └── fr.json            # French strings
├── receipts/              # auto-saved receipt PDFs
├── backups/               # auto-saved .db backups
├── assets/
│   ├── logo.png
│   └── default_product.png
├── installer/
│   └── setup.nsi          # NSIS installer script
└── requirements.txt

---

## DATABASE SCHEMA

Create all tables with proper foreign keys, indexes, and constraints:

### users
- id, username, password_hash, role (admin/cashier/supervisor), full_name, is_active, created_at, last_login

### products
- id, name, barcode, barcode_2 (secondary), category, unit (piece/kg/box/carton), unit_price_sell, unit_price_buy, unit_price_carton_sell, unit_price_carton_buy, units_per_carton, stock_qty, stock_alert_threshold, supplier_id, image_path, is_active, created_at, updated_at

### sales
- id, cashier_id, customer_id, total_amount, discount_id, discount_value, tax_amount, amount_paid, amount_change, payment_method (cash/card/partial), status (completed/refunded), notes, created_at

### sale_items
- id, sale_id, product_id, quantity, unit_type (piece/carton), unit_price, subtotal

### customers
- id, full_name, phone, address, loyalty_points, total_purchases, debt_amount, created_at

### debt_entries
- id, customer_id, sale_id, amount, type (debit/credit), notes, created_at

### loyalty_transactions
- id, customer_id, sale_id, points_earned, points_redeemed, balance_after, created_at

### suppliers
- id, name, phone, email, address, balance_owed, created_at

### purchase_orders
- id, supplier_id, total_amount, status (pending/received/partial), notes, created_at

### purchase_order_items
- id, po_id, product_id, quantity_ordered, quantity_received, unit_price, subtotal

### expenses
- id, category, description, amount, paid_by (user_id), created_at

### discounts
- id, name, type (percentage/fixed/coupon), value, coupon_code, min_purchase, is_active, valid_from, valid_to

### audit_log
- id, user_id, action, table_name, record_id, old_value (JSON), new_value (JSON), ip_address, created_at

### settings
- key, value (store name, logo path, currency, tax rate, receipt footer, language, backup interval, loyalty rate)

---

## FEATURES TO IMPLEMENT

### 1. Authentication & User Management
- Splash screen → Login screen with username/password
- Password hashing with bcrypt
- Roles: admin (full access), supervisor (no settings/users), cashier (POS only)
- Session token stored in memory (not disk)
- Auto-logout after X minutes of inactivity
- User management screen: create, edit, deactivate users (admin only)
- Force password change on first login

### 2. License System
- On first launch, show license activation screen
- License key format: XXXX-XXXX-XXXX-XXXX (16 chars, base encoded)
- Key encodes: expiry date, max_users, store_id
- Validate key against local hardware fingerprint (MAC address hash)
- Show warning 7 days before expiry
- Graceful lock on expiry (read-only mode, not crash)

### 3. Point of Sale (Sales View)
- Left panel: product search (by name or barcode), category filter buttons, product grid with image thumbnails
- Right panel: current cart (item, qty, unit type, price, subtotal), totals section
- Barcode scanner input: auto-detects fast keystroke input from USB scanner
- Webcam barcode scan button (OpenCV + pyzbar)
- Quantity can be typed or +/- buttons
- Switch unit type per item (piece ↔ carton), price updates automatically
- Apply discount: select from saved discounts or enter coupon code
- Payment section: select method (cash/card/partial), enter amount paid, show change
- Loyalty points: show customer's current points, offer to redeem (1 point = configurable value)
- Complete sale: save to DB, print/save PDF receipt, update stock, update loyalty points, clear cart
- Quick customer selector with debt indicator
- Hold/resume sale (save cart to temp table)
- Refund mode: select past sale, select items to refund, restock inventory

### 4. Product Management
- Full CRUD with image upload (stored as path)
- Dual barcode support (original + generated)
- Multi-unit pricing: price per piece, price per carton, units per carton
- Batch stock update (receive goods: enter qty received per product)
- Import products from Excel/CSV
- Export product catalog to PDF
- Print barcode labels (generate barcode image, print sheet)
- Clone product (duplicate with new name/barcode)

### 5. Inventory Management
- Stock levels table with color coding (red = below alert, yellow = near alert, green = ok)
- Low stock alerts panel on dashboard
- Stock movement history per product (sales consumed, goods received)
- Manual stock adjustment with reason (damage, loss, count correction) — logged to audit
- Filter by category, supplier, stock status

### 6. Customer Management
- Customer list with search, total purchases, debt balance, loyalty points
- Customer profile: purchase history, debt history, loyalty transaction log
- Add debt payment: enter amount, reduce debt, log transaction
- Bulk SMS/WhatsApp export (export list of customers with debt as CSV)

### 7. Supplier Management
- Supplier list with balance owed
- Purchase Orders: create PO (select supplier, add products + qty + price), save as pending
- Receive goods: select pending PO, confirm quantities received, update stock, record payment
- Supplier payment tracking

### 8. Expenses Management
- Add daily expense with category (rent, utilities, salaries, maintenance, other), description, amount
- Daily/monthly expense summary
- Expenses factored into profit reports

### 9. Discounts & Promotions
- Create discount: percentage, fixed amount, or coupon code
- Set validity date range and minimum purchase
- Apply at checkout by selecting or entering coupon code
- Discount usage report

### 10. Reports
- Daily sales report: total sales, total items sold, payment method breakdown, top products
- Date range report with matplotlib chart (bar chart by day)
- Profit report: revenue - cost - expenses = net profit
- Product performance: best sellers, slow movers
- Customer debt summary
- Export any report to PDF (with store logo and header) and Excel (.xlsx)
- End-of-day closing report: sales summary + cash drawer reconciliation

### 11. Settings
- Store info: name, address, phone, logo
- Currency symbol, tax rate (optional tax on invoice)
- Receipt customization: header text, footer text, show/hide tax line
- Language: Arabic / French (switch without restart)
- Loyalty program: points per 100 DA spent, point redemption value
- Auto-backup: interval (daily/weekly), destination folder
- Theme: light / dark

### 12. Audit Log
- Every create/update/delete action logged automatically
- Log includes: user, timestamp, table, old value (JSON), new value (JSON)
- Viewable in admin panel with filters (by user, by date, by table)

### 13. Backup & Restore
- Auto-backup on app close and on schedule
- Backup file = timestamped .db copy + config.ini zipped
- Manual backup button in settings
- Restore: select backup file → confirm → replace current DB → restart

### 14. PDF Invoice
Use reportlab to generate:
- Store logo (top left), store name/address/phone (top right)
- Invoice number, date, cashier name
- Items table: name | qty | unit | unit price | subtotal
- Totals section: subtotal, discount, tax, total paid, change
- Payment method
- Loyalty points earned/redeemed
- Footer with custom text + "Thank you" message
- Support Arabic text rendering (using arabic_reshaper + python-bidi)

### 15. Thermal Receipt (Optional)
- Format receipt for 58mm or 80mm thermal printer
- Use python-escpos for direct printer communication
- Fallback: save as .txt in receipts/ folder

---

## UI/UX REQUIREMENTS
- RTL layout support (for Arabic)
- Sidebar navigation with icons (qtawesome)
- Stacked widget for switching views (no page reload)
- Consistent QSS stylesheet: dark sidebar, white content area, accent color for buttons
- Table views use QTableWidget with alternating row colors
- All destructive actions require confirmation dialog
- Loading spinners for DB operations > 200ms
- Keyboard shortcuts: F2 = focus barcode, F5 = new sale, F10 = complete sale, Escape = cancel/back
- Status bar showing: logged-in user, current time, low stock alert count
- Responsive to window resize (no fixed pixel layouts)

---

## IMPLEMENTATION RULES
- Use MVC architecture strictly: views never touch the DB directly
- All DB operations go through controllers
- All controllers return (success: bool, data/error: any) tuples
- Use QThread for any operation that may block the UI (PDF generation, backup, report export)
- Log all exceptions to a local error.log file with traceback
- Never store plaintext passwords anywhere
- Config values read from config.ini via configparser, never hardcoded
- All user-facing strings go through tr() for localization
- On first run: create DB, prompt for admin account creation, store settings

---

## DELIVERABLES
1. Every file listed in the project structure, fully implemented (no placeholder/stub functions)
2. requirements.txt with pinned versions
3. build.bat script that runs PyInstaller to produce a single .exe
4. installer/setup.nsi NSIS script that creates a Windows installer with:
   - Start menu shortcut
   - Desktop shortcut
   - Uninstaller
   - Auto-detect Python runtime (bundled via PyInstaller)
5. README.md with: setup instructions, first-run guide, how to change language, how to restore backup

---

Build this file by file. Start with:
1. database/db.py (full schema)
2. utils/auth.py and utils/license.py
3. main.py and views/login_view.py
4. Then proceed view by view

After each file, confirm it is complete and ask which file to build next.