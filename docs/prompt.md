## CONTEXT — READ THIS FULLY BEFORE WRITING ANY CODE

You are a senior Python/PyQt5 engineer helping me build a commercial Point of Sale (POS)
system for small retail stores in Algeria. This is a multi-session project.

Your job in this conversation is NOT to generate the full project at once.
Your job is to act as a stateful co-developer:
- Hold this entire spec in memory as the source of truth
- When I say "build X", generate ONLY that file — complete, no stubs, no placeholders
- When I say "next", suggest the logical next file based on the dependency graph below
- When I share an error, debug it in context of the full spec
- Never rewrite a completed file unless I explicitly say "rewrite X"

When you finish a file, end with exactly:
✅ [filename] done — tested interface: [list the functions/classes this file exposes]
Ready for: [suggested next file]

---

## DEPENDENCY ORDER (build in this sequence)

Phase 1 — Core Foundation
  1. requirements.txt
  2. database/db.py
  3. config.ini (template)
  4. utils/auth.py
  5. utils/license.py
  6. utils/audit.py
  7. utils/backup.py

Phase 2 — Business Logic (Controllers)
  8.  controllers/auth_controller.py
  9.  controllers/product_controller.py
  10. controllers/sales_controller.py
  11. controllers/customer_controller.py
  12. controllers/supplier_controller.py
  13. controllers/expense_controller.py
  14. controllers/discount_controller.py
  15. controllers/report_controller.py

Phase 3 — Utilities
  16. utils/pdf.py
  17. utils/receipt.py
  18. utils/barcode.py
  19. utils/lang.py + utils/tr.py
  20. utils/icons.py
  21. utils/categories.py
  22. lang/ar.json + lang/fr.json

Phase 4 — UI Shell
  23. styles.qss
  24. main.py
  25. views/login_view.py
  26. views/main_window.py

Phase 5 — Feature Views
  27. views/dashboard_view.py
  28. views/sales_view.py
  29. views/products_view.py
  30. views/inventory_view.py
  31. views/customers_view.py
  32. views/suppliers_view.py
  33. views/expenses_view.py
  34. views/discounts_view.py
  35. views/reports_view.py
  36. views/settings_view.py
  37. views/user_management_view.py

Phase 6 — Packaging
  38. build.bat
  39. installer/setup.nsi
  40. README.md

---

## TECH STACK

| Layer        | Library                              |
|--------------|--------------------------------------|
| GUI          | PyQt5                                |
| Database     | SQLite via sqlite3                   |
| PDF          | reportlab + arabic_reshaper + bidi   |
| Charts       | matplotlib (embedded in PyQt5)       |
| Barcode gen  | python-barcode + Pillow              |
| Barcode scan | pyzbar + OpenCV (webcam)             |
| Auth         | bcrypt                               |
| Packaging    | PyInstaller + NSIS                   |
| Icons        | qtawesome                            |

---

## PROJECT STRUCTURE

pos_system/
├── main.py
├── styles.qss
├── config.ini
├── license.key
├── database/
│   └── db.py
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
│   ├── login_view.py
│   ├── main_window.py
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
│   ├── auth.py
│   ├── license.py
│   ├── barcode.py
│   ├── backup.py
│   ├── pdf.py
│   ├── receipt.py
│   ├── lang.py
│   ├── tr.py
│   ├── audit.py
│   ├── icons.py
│   └── categories.py
├── lang/
│   ├── ar.json
│   └── fr.json
├── receipts/
├── backups/
├── assets/
│   ├── logo.png
│   └── default_product.png
├── installer/
│   └── setup.nsi
├── build.bat
├── requirements.txt
└── README.md

---

## DATABASE SCHEMA (db.py must create all of these)

users
  id, username, password_hash, role (admin/cashier/supervisor),
  full_name, is_active, created_at, last_login, must_change_password

products
  id, name, barcode, barcode_2, category, unit, unit_price_sell,
  unit_price_buy, unit_price_carton_sell, unit_price_carton_buy,
  units_per_carton, stock_qty, stock_alert_threshold, supplier_id,
  image_path, is_active, created_at, updated_at

sales
  id, cashier_id, customer_id, total_amount, discount_id,
  discount_value, tax_amount, amount_paid, amount_change,
  payment_method (cash/card/partial), status (completed/refunded),
  notes, created_at

sale_items
  id, sale_id, product_id, quantity, unit_type (piece/carton),
  unit_price, subtotal

customers
  id, full_name, phone, address, loyalty_points,
  total_purchases, debt_amount, created_at

debt_entries
  id, customer_id, sale_id, amount, type (debit/credit),
  notes, created_at

loyalty_transactions
  id, customer_id, sale_id, points_earned, points_redeemed,
  balance_after, created_at

suppliers
  id, name, phone, email, address, balance_owed, created_at

purchase_orders
  id, supplier_id, total_amount, status (pending/received/partial),
  notes, created_at

purchase_order_items
  id, po_id, product_id, quantity_ordered, quantity_received,
  unit_price, subtotal

expenses
  id, category, description, amount, paid_by, created_at

discounts
  id, name, type (percentage/fixed/coupon), value, coupon_code,
  min_purchase, is_active, valid_from, valid_to

audit_log
  id, user_id, action, table_name, record_id,
  old_value (JSON), new_value (JSON), created_at

settings
  key, value

---

## ARCHITECTURE RULES (enforce in every file)

1. MVC strictly — views never import from database/, only from controllers/
2. Every controller function returns a tuple: (bool success, data | error_message)
3. All DB access goes through database/db.py get_connection()
4. All blocking operations (PDF, backup, reports) run in QThread
5. All user-facing strings pass through tr() — never hardcoded
6. All exceptions are caught, logged to error.log with traceback, never silently swallowed
7. Passwords: bcrypt only, never stored or logged in plaintext
8. Config values: always from config.ini via configparser, never hardcoded
9. Every write operation (create/update/delete) calls audit.log_action() after success

---

## FEATURE SPEC SUMMARY

### Auth & Users
- Login screen before anything else
- bcrypt password hashing
- Roles: admin (all), supervisor (no settings/users), cashier (POS only)
- Session held in memory only
- Auto-logout after inactivity timeout from settings
- Force password change on first login (must_change_password flag)
- Admin can create/deactivate users, never delete

### License
- First launch: show activation screen
- Key format: XXXX-XXXX-XXXX-XXXX encoding expiry + store_id
- Bind to hardware fingerprint (MAC address hash)
- 7-day warning before expiry
- On expiry: read-only mode (no new sales), not crash

### POS / Sales View
- Left: barcode input field (USB scanner auto-detected as fast keystrokes),
  product search by name, category filter chips, product grid with thumbnails
- Right: cart table, totals, payment section
- Per cart item: qty input, unit toggle (piece/carton), price auto-updates
- Discount: dropdown of active discounts or coupon code input
- Payment: cash/card/partial, amount paid field, change display
- Loyalty: show customer points, optional redemption
- Actions: Complete Sale (F10), Hold Sale, Refund Mode
- On complete: save sale + items, update stock, update loyalty, generate PDF receipt

### Products
- CRUD with image upload
- Dual barcode (original + generated)
- Multi-unit pricing (piece vs carton)
- Batch stock update (receiving goods)
- Import from CSV/Excel, export catalog to PDF
- Print barcode label sheets
- Clone product

### Inventory
- Table with stock status color coding (red/yellow/green)
- Stock movement history per product
- Manual adjustment with reason (logged to audit)

### Customers
- List with debt + loyalty summary
- Profile view: purchase history, debt log, loyalty log
- Record debt payment

### Suppliers
- List with balance owed
- Purchase Orders: create, receive goods (updates stock)
- Payment tracking

### Expenses
- Add expense with category, description, amount
- Daily/monthly summary view
- Used in profit calculation in reports

### Discounts
- Create: percentage, fixed, or coupon code
- Date range + minimum purchase rules
- Usage report

### Reports
- Daily sales summary
- Date range report with matplotlib bar chart
- Profit: revenue − cost − expenses
- Product performance (best/slow sellers)
- Customer debt summary
- Export all reports to PDF + Excel (.xlsx)
- End-of-day closing report

### Settings
- Store info (name, address, phone, logo)
- Currency symbol, tax rate
- Receipt header/footer text
- Language toggle (Arabic/French, no restart needed)
- Loyalty program rate
- Auto-backup interval + destination
- Theme: light/dark
- Inactivity timeout

### Audit Log
- Automatic on every controller write operation
- Viewable in admin panel, filter by user/date/table

### Backup
- Auto on app close + on schedule from settings
- Manual button in settings
- Restore: pick .zip backup → confirm → restart

### PDF Invoice (reportlab)
- Store logo + info header
- Items table with Arabic text support (arabic_reshaper + bidi)
- Totals block: subtotal, discount, tax, paid, change
- Loyalty points earned/redeemed
- Custom footer

### UI Rules
- RTL layout when language = Arabic
- Sidebar + stacked widget navigation
- QSS: dark sidebar, white content, accent color
- Alternating row colors in all tables
- Confirm dialog on all destructive actions
- QThread + loading spinner for ops > 200ms
- Keyboard shortcuts: F2=barcode focus, F5=new sale, F10=complete, Esc=back
- Status bar: current user, time, low-stock count

---

## HOW TO WORK WITH ME

I will give you one instruction at a time, in one of these forms:

  "build requirements.txt"
  "build database/db.py"
  "build controllers/sales_controller.py"
  "next"                         → you suggest and build the next file
  "error: [paste error]"         → debug without touching other files
  "rewrite views/sales_view.py"  → full rewrite of that file only

You will respond with the complete file content in a single code block.
No partial implementations. No "TODO" comments. No "implement this yourself".
Every function must be fully written.

---

## START INSTRUCTION

Confirm you have read and understood the full spec by responding with:
1. A one-paragraph summary of the system in your own words
2. The dependency order (Phase 1 → 6) as a numbered list
3. The message: "Ready. Tell me which file to build first, or type 'next' to start."

Do not write any code yet.