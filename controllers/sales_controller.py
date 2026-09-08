from typing import List, Dict
from database.db import get_connection, now_iso
from utils.receipt import write_receipt


class SalesController:
    def __init__(self, product_controller):
        # product_controller: controller to lookup products and update stock
        self.product_controller = product_controller
        self.cart: List[Dict] = []  # items: {product, quantity}

    def clear_cart(self):
        self.cart = []

    def add_barcode_to_cart(self, barcode: str, qty: int = 1):
        prod = self.product_controller.get_by_barcode(barcode)
        if not prod:
            raise ValueError('Product not found')

        # if already in cart, check combined quantity against stock
        for item in self.cart:
            if item['product'].id == prod.id:
                new_qty = item['quantity'] + qty
                if new_qty > prod.quantity:
                    raise ValueError(
                        f'Not enough stock for "{prod.name}".\n'
                        f'Available: {prod.quantity}, in cart: {item["quantity"]}.'
                    )
                item['quantity'] = new_qty
                return item

        # new item — check stock
        if qty > prod.quantity:
            raise ValueError(
                f'Not enough stock for "{prod.name}".\n'
                f'Available: {prod.quantity}.'
            )

        item = {'product': prod, 'quantity': qty}
        self.cart.append(item)
        return item

    def change_quantity(self, product_id: int, quantity: int):
        for item in self.cart:
            if item['product'].id == product_id:
                q = max(0, int(quantity))
                if q == 0:
                    # remove item if quantity set to zero
                    self.remove_item(product_id)
                    return None
                available = item['product'].quantity
                if q > available:
                    raise ValueError(
                        f'Not enough stock for "{item["product"].name}".\n'
                        f'Available: {available}.'
                    )
                item['quantity'] = q
                return item
        return None

    def remove_item(self, product_id: int):
        self.cart = [i for i in self.cart if i['product'].id != product_id]

    def subtotal(self) -> float:
        return sum(item['product'].price * item['quantity'] for item in self.cart)

    def total(self) -> float:
        return self.subtotal()

    def complete_sale(self, customer_id: int = None, *, cashier_id=None,
                      discount_id=None, discount_value: float = 0.0,
                      tax_amount: float = 0.0, amount_paid: float = None,
                      amount_change: float = None,
                      payment_method: str = 'cash',
                      notes: str = '') -> Dict:
        if not self.cart:
            raise ValueError('Cart is empty')

        # final stock validation before writing to DB
        for item in self.cart:
            p = item['product']
            q = int(item['quantity'])
            fresh = self.product_controller.get_by_barcode(p.barcode)
            available = fresh.quantity if fresh else p.quantity
            if q > available:
                raise ValueError(
                    f'Not enough stock for "{p.name}".\n'
                    f'Available: {available}, requested: {q}.'
                )

        subtotal = self.subtotal()
        total_amount = round(subtotal - discount_value + tax_amount, 2)
        if amount_paid is None:
            amount_paid = total_amount
        if amount_change is None:
            amount_change = max(round(amount_paid - total_amount, 2), 0)

        conn = get_connection()
        cur = conn.cursor()
        date = now_iso()
        cur.execute(
            '''INSERT INTO sales
               (date, total, customer_id, cashier_id, total_amount,
                discount_id, discount_value, tax_amount, amount_paid,
                amount_change, payment_method, status, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)''',
            (date, total_amount, customer_id, cashier_id, total_amount,
             discount_id, discount_value, tax_amount, amount_paid,
             amount_change, payment_method, notes, date),
        )
        sale_id = cur.lastrowid

        for item in self.cart:
            p = item['product']
            q = int(item['quantity'])
            cur.execute(
                'INSERT INTO sale_items (sale_id, product_id, quantity, price, subtotal)'
                ' VALUES (?, ?, ?, ?, ?)',
                (sale_id, p.id, q, p.price, round(p.price * q, 2)),
            )
            # reduce stock (additive & atomic); trigger mirrors stock_qty
            cur.execute(
                'UPDATE products SET quantity = MAX(0, quantity - ?) WHERE id = ?',
                (q, p.id),
            )

        conn.commit()
        conn.close()

        sale = {
            'id': sale_id,
            'date': date,
            'created_at': date,
            'total': total_amount,
            'total_amount': total_amount,
            'subtotal': round(subtotal, 2),
            'discount_value': discount_value,
            'tax_amount': tax_amount,
            'amount_paid': amount_paid,
            'amount_change': amount_change,
            'payment_method': payment_method,
            'status': 'completed',
            'items': [{'name': i['product'].name,
                       'barcode': i['product'].barcode,
                       'quantity': i['quantity'],
                       'price': i['product'].price} for i in self.cart],
        }

        # write a simple receipt
        write_receipt(sale)

        # clear cart
        self.clear_cart()

        return sale
