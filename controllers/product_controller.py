import sqlite3
from typing import List
from database.db import get_connection
from models.product import Product
from utils.barcode import generate_barcode


class ProductController:
    def __init__(self):
        pass

    def add_product(self, name: str, barcode: str | None, price: float, quantity: int, category: str | None) -> Product:
        conn = get_connection()
        cur = conn.cursor()

        if not barcode:
            barcode = generate_barcode()

        cur.execute(
            'INSERT INTO products (name, barcode, price, quantity, category) VALUES (?, ?, ?, ?, ?)',
            (name, barcode, price, quantity, category),
        )
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return Product(pid, name, barcode, price, quantity, category)

    def update_product(self, product_id: int, **kwargs):
        allowed = ['name', 'barcode', 'price', 'quantity', 'category', 'min_level', 'cost_price']
        fields = []
        values = []
        for k, v in kwargs.items():
            if k in allowed:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return
        values.append(product_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def delete_product(self, product_id: int):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()

    def get_all(self) -> List[Product]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM products ORDER BY name')
        rows = cur.fetchall()
        conn.close()
        return [Product(r['id'], r['name'], r['barcode'], r['price'], r['quantity'], r['category'],
                        r['min_level'] if 'min_level' in r.keys() else 5,
                        r['cost_price'] if 'cost_price' in r.keys() else 0.0) for r in rows]

    def search(self, term: str) -> List[Product]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM products WHERE name LIKE ? OR barcode = ? ORDER BY name', (f'%{term}%', term))
        rows = cur.fetchall()
        conn.close()
        return [Product(r['id'], r['name'], r['barcode'], r['price'], r['quantity'], r['category'],
                        r['min_level'] if 'min_level' in r.keys() else 5,
                        r['cost_price'] if 'cost_price' in r.keys() else 0.0) for r in rows]

    def get_by_barcode(self, barcode: str) -> Product | None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM products WHERE barcode = ?', (barcode,))
        r = cur.fetchone()
        conn.close()
        if r:
            return Product(r['id'], r['name'], r['barcode'], r['price'], r['quantity'], r['category'],
                           r['min_level'] if 'min_level' in r.keys() else 5,
                           r['cost_price'] if 'cost_price' in r.keys() else 0.0)
        return None
