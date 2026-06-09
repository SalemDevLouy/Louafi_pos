import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos.db')


def get_connection():
    # ensure folder exists
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # products table
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT UNIQUE,
            price REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0,
            category TEXT
        )
        '''
    )

    # sales table
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total REAL NOT NULL
        )
        '''
    )

    # sale items
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        '''
    )

    # customers
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            debt REAL NOT NULL DEFAULT 0
        )
        '''
    )

    # debts ledger
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS debt_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        '''
    )

    # suppliers
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS suppliers (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            category TEXT
        )
        '''
    )

    # billing orders (one per delivery from a supplier)
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS billing_orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            date        TEXT    NOT NULL,
            note        TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
        '''
    )

    # billing items (lines inside a billing order)
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS billing_items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            billing_order_id INTEGER NOT NULL,
            product_id       INTEGER NOT NULL,
            quantity         INTEGER NOT NULL,
            buy_price        REAL    NOT NULL DEFAULT 0,
            sale_price       REAL    NOT NULL DEFAULT 0,
            FOREIGN KEY (billing_order_id) REFERENCES billing_orders(id),
            FOREIGN KEY (product_id)       REFERENCES products(id)
        )
        '''
    )

    # ── Migrate existing tables (safe – ignore if column already exists) ────────

    _migrate(cur, 'ALTER TABLE products ADD COLUMN min_level INTEGER NOT NULL DEFAULT 5')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN unit_price_sell REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN unit_price_buy REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN unit_price_carton_sell REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN unit_price_carton_buy REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN units_per_carton INTEGER NOT NULL DEFAULT 1')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN stock_qty INTEGER NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN stock_alert_threshold INTEGER NOT NULL DEFAULT 5')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN barcode_2 TEXT')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN unit TEXT')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN supplier_id INTEGER')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN image_path TEXT')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN created_at TEXT')
    _migrate(cur, 'ALTER TABLE products ADD COLUMN updated_at TEXT')

    _migrate(cur, 'ALTER TABLE sales ADD COLUMN customer_id INTEGER REFERENCES customers(id)')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN cashier_id INTEGER')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN total_amount REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN discount_id INTEGER')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN discount_value REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN tax_amount REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN amount_paid REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN amount_change REAL NOT NULL DEFAULT 0')
    _migrate(cur, "ALTER TABLE sales ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'cash'")
    _migrate(cur, "ALTER TABLE sales ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN notes TEXT')
    _migrate(cur, 'ALTER TABLE sales ADD COLUMN created_at TEXT')

    _migrate(cur, 'ALTER TABLE customers ADD COLUMN full_name TEXT')
    _migrate(cur, 'ALTER TABLE customers ADD COLUMN loyalty_points INTEGER NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE customers ADD COLUMN total_purchases REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE customers ADD COLUMN debt_amount REAL NOT NULL DEFAULT 0')
    _migrate(cur, 'ALTER TABLE customers ADD COLUMN created_at TEXT')

    # copy old column values → new columns (once, idempotent)
    cur.execute('UPDATE products SET unit_price_sell=price WHERE unit_price_sell=0 AND price>0')
    cur.execute('UPDATE products SET unit_price_buy=cost_price WHERE unit_price_buy=0 AND cost_price>0')
    cur.execute('UPDATE products SET stock_qty=quantity WHERE stock_qty=0 AND quantity>0')
    cur.execute('UPDATE sales SET total_amount=total WHERE total_amount=0 AND total>0')
    cur.execute('UPDATE sales SET created_at=date WHERE created_at IS NULL AND date IS NOT NULL')
    cur.execute('UPDATE customers SET full_name=name WHERE full_name IS NULL')
    cur.execute('UPDATE customers SET debt_amount=debt WHERE debt_amount=0 AND debt>0')

    # ── New tables ────────────────────────────────────────────────────────────

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            username             TEXT    NOT NULL UNIQUE,
            password_hash        TEXT    NOT NULL,
            role                 TEXT    NOT NULL DEFAULT 'cashier',
            full_name            TEXT,
            is_active            INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            created_at           TEXT    DEFAULT (datetime('now','localtime')),
            last_login           TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL,
            description TEXT,
            amount      REAL    NOT NULL DEFAULT 0,
            paid_by     TEXT,
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS discounts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            type         TEXT    NOT NULL DEFAULT 'percentage',
            value        REAL    NOT NULL DEFAULT 0,
            coupon_code  TEXT,
            min_purchase REAL,
            is_active    INTEGER NOT NULL DEFAULT 1,
            valid_from   TEXT,
            valid_to     TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            action     TEXT    NOT NULL,
            table_name TEXT    NOT NULL,
            record_id  INTEGER,
            old_value  TEXT,
            new_value  TEXT,
            created_at TEXT    DEFAULT (datetime('now','localtime'))
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS loyalty_transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER NOT NULL,
            sale_id         INTEGER,
            points_earned   INTEGER NOT NULL DEFAULT 0,
            points_redeemed INTEGER NOT NULL DEFAULT 0,
            balance_after   INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now','localtime'))
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id  INTEGER NOT NULL,
            total_amount REAL    NOT NULL DEFAULT 0,
            status       TEXT    NOT NULL DEFAULT 'pending',
            notes        TEXT,
            created_at   TEXT    DEFAULT (datetime('now','localtime'))
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id             INTEGER NOT NULL,
            product_id        INTEGER NOT NULL,
            quantity_ordered  INTEGER NOT NULL DEFAULT 0,
            quantity_received INTEGER NOT NULL DEFAULT 0,
            unit_price        REAL    NOT NULL DEFAULT 0,
            subtotal          REAL    NOT NULL DEFAULT 0
        )
    ''')

    # migrate: legacy supplier / billing tables
    for ddl in (
        'CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, category TEXT)',
        'CREATE TABLE IF NOT EXISTS billing_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_id INTEGER NOT NULL, date TEXT NOT NULL, note TEXT, FOREIGN KEY (supplier_id) REFERENCES suppliers(id))',
        'CREATE TABLE IF NOT EXISTS billing_items (id INTEGER PRIMARY KEY AUTOINCREMENT, billing_order_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, buy_price REAL NOT NULL DEFAULT 0, sale_price REAL NOT NULL DEFAULT 0, FOREIGN KEY (billing_order_id) REFERENCES billing_orders(id), FOREIGN KEY (product_id) REFERENCES products(id))',
    ):
        cur.execute(ddl)

    conn.commit()
    conn.close()


def _migrate(cur, ddl: str) -> None:
    try:
        cur.execute(ddl)
    except Exception:
        pass


def now_iso():
    # use local time isoformat (acceptable for a local POS)
    return datetime.now().isoformat()
