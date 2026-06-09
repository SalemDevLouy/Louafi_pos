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

    # migrate: add min_level to products if missing
    try:
        cur.execute('ALTER TABLE products ADD COLUMN min_level INTEGER NOT NULL DEFAULT 5')
    except Exception:
        pass

    # migrate: add customer_id to sales if missing
    try:
        cur.execute('ALTER TABLE sales ADD COLUMN customer_id INTEGER REFERENCES customers(id)')
    except Exception:
        pass

    # migrate: add cost_price to products if missing (for profit calc)
    try:
        cur.execute('ALTER TABLE products ADD COLUMN cost_price REAL NOT NULL DEFAULT 0')
    except Exception:
        pass

    # migrate: suppliers / billing tables (safe no-ops if already exist)
    for ddl in (
        'CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, category TEXT)',
        'CREATE TABLE IF NOT EXISTS billing_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_id INTEGER NOT NULL, date TEXT NOT NULL, note TEXT, FOREIGN KEY (supplier_id) REFERENCES suppliers(id))',
        'CREATE TABLE IF NOT EXISTS billing_items (id INTEGER PRIMARY KEY AUTOINCREMENT, billing_order_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, buy_price REAL NOT NULL DEFAULT 0, sale_price REAL NOT NULL DEFAULT 0, FOREIGN KEY (billing_order_id) REFERENCES billing_orders(id), FOREIGN KEY (product_id) REFERENCES products(id))',
    ):
        cur.execute(ddl)

    conn.commit()
    conn.close()


def now_iso():
    # use local time isoformat (acceptable for a local POS)
    return datetime.now().isoformat()
