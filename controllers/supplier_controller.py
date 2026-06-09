from __future__ import annotations
from typing import List, Optional
from database.db import get_connection, now_iso
from models.supplier import Supplier, BillingOrder, BillingItem


class SupplierController:
    # ── Suppliers CRUD ────────────────────────────────────────────────────────

    def add_supplier(self, name: str, phone: str = '', category: str = '') -> Supplier:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO suppliers (name, phone, category) VALUES (?, ?, ?)',
            (name, phone, category),
        )
        conn.commit()
        sid = cur.lastrowid
        conn.close()
        return Supplier(sid, name, phone, category)

    def update_supplier(self, supplier_id: int, name: str, phone: str, category: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'UPDATE suppliers SET name=?, phone=?, category=? WHERE id=?',
            (name, phone, category, supplier_id),
        )
        conn.commit()
        conn.close()

    def delete_supplier(self, supplier_id: int):
        """Delete supplier and all their billing orders/items (cascade)."""
        conn = get_connection()
        cur = conn.cursor()
        # gather order ids first
        cur.execute('SELECT id FROM billing_orders WHERE supplier_id=?', (supplier_id,))
        order_ids = [r['id'] for r in cur.fetchall()]
        for oid in order_ids:
            cur.execute('DELETE FROM billing_items WHERE billing_order_id=?', (oid,))
        cur.execute('DELETE FROM billing_orders WHERE supplier_id=?', (supplier_id,))
        cur.execute('DELETE FROM suppliers WHERE id=?', (supplier_id,))
        conn.commit()
        conn.close()

    def get_all_suppliers(self) -> List[Supplier]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM suppliers ORDER BY name')
        rows = cur.fetchall()
        conn.close()
        return [Supplier(r['id'], r['name'], r['phone'] or '', r['category'] or '') for r in rows]

    def get_supplier_by_id(self, supplier_id: int) -> Optional[Supplier]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM suppliers WHERE id=?', (supplier_id,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return None
        return Supplier(r['id'], r['name'], r['phone'] or '', r['category'] or '')

    def search_suppliers(self, term: str) -> List[Supplier]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM suppliers WHERE name LIKE ? OR phone LIKE ? OR category LIKE ? ORDER BY name',
            (f'%{term}%', f'%{term}%', f'%{term}%'),
        )
        rows = cur.fetchall()
        conn.close()
        return [Supplier(r['id'], r['name'], r['phone'] or '', r['category'] or '') for r in rows]

    # ── Billing orders CRUD ───────────────────────────────────────────────────

    def add_billing_order(self, supplier_id: int, note: str = '', date: str = '') -> BillingOrder:
        conn = get_connection()
        cur = conn.cursor()
        d = date if date else now_iso()
        cur.execute(
            'INSERT INTO billing_orders (supplier_id, date, note) VALUES (?, ?, ?)',
            (supplier_id, d, note),
        )
        conn.commit()
        oid = cur.lastrowid
        conn.close()
        return BillingOrder(oid, supplier_id, d, note)

    def update_billing_order(self, order_id: int, note: str, date: str):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'UPDATE billing_orders SET note=?, date=? WHERE id=?',
            (note, date, order_id),
        )
        conn.commit()
        conn.close()

    def delete_billing_order(self, order_id: int):
        """Delete a billing order + its items; reverse stock adjustments."""
        conn = get_connection()
        cur = conn.cursor()
        # reverse stock
        cur.execute('SELECT product_id, quantity FROM billing_items WHERE billing_order_id=?', (order_id,))
        for row in cur.fetchall():
            cur.execute(
                'UPDATE products SET quantity = MAX(0, quantity - ?) WHERE id=?',
                (row['quantity'], row['product_id']),
            )
        cur.execute('DELETE FROM billing_items WHERE billing_order_id=?', (order_id,))
        cur.execute('DELETE FROM billing_orders WHERE id=?', (order_id,))
        conn.commit()
        conn.close()

    def get_orders_for_supplier(self, supplier_id: int) -> List[BillingOrder]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM billing_orders WHERE supplier_id=? ORDER BY date DESC',
            (supplier_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [BillingOrder(r['id'], r['supplier_id'], r['date'], r['note'] or '') for r in rows]

    def get_order_by_id(self, order_id: int) -> Optional[BillingOrder]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM billing_orders WHERE id=?', (order_id,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return None
        return BillingOrder(r['id'], r['supplier_id'], r['date'], r['note'] or '')

    # ── Billing items CRUD ────────────────────────────────────────────────────

    def add_billing_item(
        self,
        order_id: int,
        product_id: int,
        quantity: int,
        buy_price: float,
        sale_price: float,
    ) -> BillingItem:
        """Add a line to a billing order and update stock + sale price."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO billing_items (billing_order_id, product_id, quantity, buy_price, sale_price)'
            ' VALUES (?, ?, ?, ?, ?)',
            (order_id, product_id, quantity, buy_price, sale_price),
        )
        item_id = cur.lastrowid
        # push to stock
        cur.execute('UPDATE products SET quantity = quantity + ? WHERE id=?', (quantity, product_id))
        # update cost_price and sale price on the product
        cur.execute(
            'UPDATE products SET cost_price=?, price=? WHERE id=?',
            (buy_price, sale_price, product_id),
        )
        conn.commit()
        # fetch product name for the returned object
        cur.execute('SELECT name FROM products WHERE id=?', (product_id,))
        r = cur.fetchone()
        conn.close()
        product_name = r['name'] if r else ''
        return BillingItem(item_id, order_id, product_id, product_name, quantity, buy_price, sale_price)

    def update_billing_item(
        self,
        item_id: int,
        quantity: int,
        buy_price: float,
        sale_price: float,
    ):
        """Update a billing item — adjusts stock delta and product prices."""
        conn = get_connection()
        cur = conn.cursor()
        # old quantity
        cur.execute('SELECT quantity, product_id FROM billing_items WHERE id=?', (item_id,))
        old = cur.fetchone()
        if not old:
            conn.close()
            return
        delta = quantity - old['quantity']
        product_id = old['product_id']
        cur.execute(
            'UPDATE billing_items SET quantity=?, buy_price=?, sale_price=? WHERE id=?',
            (quantity, buy_price, sale_price, item_id),
        )
        if delta != 0:
            cur.execute(
                'UPDATE products SET quantity = MAX(0, quantity + ?) WHERE id=?',
                (delta, product_id),
            )
        cur.execute(
            'UPDATE products SET cost_price=?, price=? WHERE id=?',
            (buy_price, sale_price, product_id),
        )
        conn.commit()
        conn.close()

    def delete_billing_item(self, item_id: int):
        """Remove a billing line and reverse the stock."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT product_id, quantity FROM billing_items WHERE id=?', (item_id,))
        row = cur.fetchone()
        if row:
            cur.execute(
                'UPDATE products SET quantity = MAX(0, quantity - ?) WHERE id=?',
                (row['quantity'], row['product_id']),
            )
        cur.execute('DELETE FROM billing_items WHERE id=?', (item_id,))
        conn.commit()
        conn.close()

    def get_items_for_order(self, order_id: int) -> List[BillingItem]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT bi.*, p.name AS product_name
              FROM billing_items bi
              JOIN products p ON p.id = bi.product_id
             WHERE bi.billing_order_id = ?
             ORDER BY bi.id
            ''',
            (order_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            BillingItem(
                r['id'], r['billing_order_id'], r['product_id'], r['product_name'],
                r['quantity'], r['buy_price'], r['sale_price'],
            )
            for r in rows
        ]

    # ── Summary helper ────────────────────────────────────────────────────────

    def order_total_cost(self, order_id: int) -> float:
        """Sum of (quantity * buy_price) for all items in the order."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT SUM(quantity * buy_price) FROM billing_items WHERE billing_order_id=?',
            (order_id,),
        )
        val = cur.fetchone()[0]
        conn.close()
        return val or 0.0
