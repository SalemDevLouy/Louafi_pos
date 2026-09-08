from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from database.db import get_connection, now_iso


@dataclass
class Customer:
    id: int
    name: str
    phone: str
    address: str
    debt: float

    def to_dict(self):
        return vars(self)


@dataclass
class DebtEntry:
    id: int
    customer_id: int
    date: str
    amount: float
    note: str


class CustomerController:
    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_customer(self, name: str, phone: str = '', address: str = '') -> Customer:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO customers (name, phone, address, debt) VALUES (?, ?, ?, 0)',
            (name, phone, address),
        )
        conn.commit()
        cid = cur.lastrowid
        conn.close()
        return Customer(cid, name, phone, address, 0.0)

    def update_customer(self, customer_id: int, **kwargs):
        allowed = ['name', 'phone', 'address']
        fields = [f"{k} = ?" for k in kwargs if k in allowed]
        values = [v for k, v in kwargs.items() if k in allowed]
        if not fields:
            return
        values.append(customer_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE customers SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def delete_customer(self, customer_id: int):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()
        conn.close()

    def get_all(self) -> List[Customer]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM customers ORDER BY name')
        rows = cur.fetchall()
        conn.close()
        return [Customer(r['id'], r['name'], r['phone'] or '', r['address'] or '', r['debt']) for r in rows]

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return None
        return Customer(r['id'], r['name'], r['phone'] or '', r['address'] or '', r['debt'])

    def search(self, term: str) -> List[Customer]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name',
            (f'%{term}%', f'%{term}%'),
        )
        rows = cur.fetchall()
        conn.close()
        return [Customer(r['id'], r['name'], r['phone'] or '', r['address'] or '', r['debt']) for r in rows]

    # ── Debt management ───────────────────────────────────────────────────────

    def add_debt(self, customer_id: int, amount: float, note: str = '') -> DebtEntry:
        """Record a new debt (positive amount = owes money)."""
        conn = get_connection()
        cur = conn.cursor()
        date = now_iso()
        cur.execute(
            'INSERT INTO debt_entries (customer_id, date, amount, note) VALUES (?, ?, ?, ?)',
            (customer_id, date, amount, note),
        )
        cur.execute(
            'UPDATE customers SET debt = debt + ?, debt_amount = debt_amount + ?'
            ' WHERE id = ?',
            (amount, amount, customer_id),
        )
        conn.commit()
        eid = cur.lastrowid
        conn.close()
        return DebtEntry(eid, customer_id, date, amount, note)

    def pay_debt(self, customer_id: int, amount: float, note: str = 'Payment') -> DebtEntry:
        """Record a payment (negative entry reduces debt)."""
        return self.add_debt(customer_id, -abs(amount), note)

    def get_debt_entries(self, customer_id: int) -> List[DebtEntry]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM debt_entries WHERE customer_id = ? ORDER BY date DESC',
            (customer_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [DebtEntry(r['id'], r['customer_id'], r['date'], r['amount'], r['note'] or '') for r in rows]
