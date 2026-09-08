"""Returns & Refunds.

Every return is bound to an original invoice (sales.id).  Refund amounts are
always taken from the original sale_items.unit_price and are never editable by
the cashier.  Stock is put back automatically.
"""
from __future__ import annotations

from typing import List

from database.db import get_connection, now_iso
from utils import audit


class ReturnsController:
    # ── Sales history lookup ──────────────────────────────────────────────────

    def search_sales(self, term: str = '') -> List[dict]:
        """Recent sales, optionally filtered by invoice # or customer text."""
        conn = get_connection()
        term = (term or '').strip()
        sql = """
            SELECT s.id,
                   s.created_at,
                   s.payment_method,
                   s.status,
                   COALESCE(NULLIF(s.total_amount, 0), s.total, 0) AS total_effective,
                   COALESCE(c.full_name, c.name, '—') AS customer_name,
                   COALESCE(u.username, '—') AS cashier_name,
                   COALESCE((SELECT SUM(r.total_refund) FROM returns r
                              WHERE r.sale_id = s.id), 0) AS refunded
              FROM sales s
              LEFT JOIN customers c ON c.id = s.customer_id
              LEFT JOIN users u ON u.id = s.cashier_id
        """
        params: list = []
        if term:
            if term.isdigit():
                sql += ' WHERE s.id = ?'
                params.append(int(term))
            else:
                sql += """ WHERE c.name LIKE ? OR c.full_name LIKE ?
                           OR c.phone LIKE ?"""
                like = f'%{term}%'
                params.extend([like, like, like])
        sql += ' ORDER BY s.id DESC LIMIT 200'
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_sale_detail(self, sale_id: int) -> dict:
        """Full header + line items for one invoice, with qty already returned."""
        conn = get_connection()
        header = conn.execute(
            """SELECT s.*,
                      COALESCE(c.full_name, c.name, '—') AS customer_name,
                      COALESCE(u.username, '—') AS cashier_name
               FROM sales s
               LEFT JOIN customers c ON c.id = s.customer_id
               LEFT JOIN users u ON u.id = s.cashier_id
               WHERE s.id = ?""",
            (sale_id,),
        ).fetchone()
        if not header:
            conn.close()
            raise ValueError(f'Sale #{sale_id} not found.')

        items = conn.execute(
            """SELECT si.id AS sale_item_id,
                      si.product_id,
                      si.quantity AS qty_sold,
                      si.price AS unit_price,
                      COALESCE(si.subtotal, si.price * si.quantity, 0) AS line_total,
                      p.name AS product_name,
                      p.barcode,
                      p.quantity AS current_stock,
                      COALESCE((SELECT SUM(ri.quantity) FROM return_items ri
                                 JOIN returns r ON r.id = ri.return_id
                                WHERE ri.sale_item_id = si.id), 0) AS qty_returned
               FROM sale_items si
               JOIN products p ON p.id = si.product_id
               WHERE si.sale_id = ?
               ORDER BY si.id""",
            (sale_id,),
        ).fetchall()
        conn.close()

        detail = dict(header)
        detail['total_effective'] = float(
            header['total_amount'] or header['total'] or 0.0
        )
        detail['items'] = [dict(r) for r in items]
        return detail

    # ── Create a return ───────────────────────────────────────────────────────

    def create_return(self, sale_id: int, reason: str,
                      items: List[tuple], actor_id: int | None = None) -> dict:
        """Record a return for one invoice.

        ``items`` is a list of ``(sale_item_id, quantity)``.  Validates that each
        quantity is still returnable (sold − already returned), restocks the
        products, and marks the sale as ``'returned'`` when every line is back.
        """
        conn = get_connection()
        validated = []      # return_items rows
        restock: dict = {}  # product_id -> total qty to add back
        refund_total = 0.0
        created_at = now_iso()
        return_id = None
        new_status = None
        try:
            cur = conn.cursor()
            header = cur.execute(
                'SELECT * FROM sales WHERE id = ?', (sale_id,)
            ).fetchone()
            if not header:
                raise ValueError(f'Sale #{sale_id} not found.')
            if header['status'] == 'returned':
                raise ValueError(
                    'This sale is already fully returned — nothing left to return.'
                )

            for sale_item_id, qty in items:
                qty = int(qty)
                if qty <= 0:
                    continue
                row = cur.execute(
                    """SELECT si.*,
                              COALESCE((SELECT SUM(ri.quantity) FROM return_items ri
                                         JOIN returns r ON r.id = ri.return_id
                                        WHERE ri.sale_item_id = si.id), 0) AS already
                       FROM sale_items si
                       WHERE si.id = ? AND si.sale_id = ?""",
                    (sale_item_id, sale_id),
                ).fetchone()
                if not row:
                    raise ValueError(f'Invalid line item #{sale_item_id} on this sale.')
                remaining = int(row['quantity'] - row['already'])
                if qty > remaining:
                    pname = cur.execute(
                        'SELECT name FROM products WHERE id = ?', (row['product_id'],)
                    ).fetchone()
                    name = pname['name'] if pname else 'item'
                    raise ValueError(
                        f'Cannot return {qty} of "{name}": only {remaining} '
                        'still returnable on this invoice.'
                    )
                subtotal = round(row['price'] * qty, 2)
                validated.append({
                    'sale_item_id': sale_item_id,
                    'product_id': row['product_id'],
                    'quantity': qty,
                    'unit_price': row['price'],
                    'subtotal': subtotal,
                    'product_name': None,  # filled before the receipt is written
                })
                refund_total += subtotal
                restock[row['product_id']] = restock.get(row['product_id'], 0) + qty

            if not validated:
                raise ValueError('No items selected to return.')

            refund_total = round(refund_total, 2)

            cur.execute(
                """INSERT INTO returns
                   (sale_id, customer_id, total_refund, reason, returned_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sale_id, header['customer_id'], refund_total, reason or None,
                 actor_id, created_at),
            )
            return_id = cur.lastrowid

            for v in validated:
                # fetch product name for the receipt/trail
                pname = cur.execute(
                    'SELECT name FROM products WHERE id = ?', (v['product_id'],)
                ).fetchone()
                v['product_name'] = pname['name'] if pname else ''
                cur.execute(
                    """INSERT INTO return_items
                       (return_id, sale_item_id, product_id, quantity, unit_price, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (return_id, v['sale_item_id'], v['product_id'], v['quantity'],
                     v['unit_price'], v['subtotal']),
                )

            for product_id, qty in restock.items():
                cur.execute(
                    'UPDATE products SET quantity = quantity + ? WHERE id = ?',
                    (qty, product_id),
                )

            # Mark the sale fully returned when every sold quantity is back.
            total_sold = cur.execute(
                'SELECT COALESCE(SUM(quantity), 0) FROM sale_items WHERE sale_id = ?',
                (sale_id,),
            ).fetchone()[0]
            total_ret = cur.execute(
                """SELECT COALESCE(SUM(ri.quantity), 0)
                   FROM return_items ri
                   JOIN returns r ON r.id = ri.return_id
                   WHERE r.sale_id = ?""",
                (sale_id,),
            ).fetchone()[0]
            if total_ret >= total_sold:
                cur.execute("UPDATE sales SET status = 'returned' WHERE id = ?", (sale_id,))
                new_status = 'returned'

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        audit.log_action(
            actor_id, 'RETURN', 'returns', return_id,
            new_value={
                'sale_id': sale_id,
                'total_refund': refund_total,
                'reason': reason,
                'items': [(v['sale_item_id'], v['quantity']) for v in validated],
            },
        )

        summary = {
            'id': return_id,
            'sale_id': sale_id,
            'total_refund': refund_total,
            'created_at': created_at,
            'status': new_status or 'completed',
            'items': validated,
        }
        self._write_receipt(summary)
        return summary

    @staticmethod
    def _write_receipt(ret: dict) -> None:
        """Best-effort text receipt for the return (never blocks the return)."""
        try:
            from utils.receipt import write_return_receipt
            write_return_receipt(ret)
        except Exception:
            pass
