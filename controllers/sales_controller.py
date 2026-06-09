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

    def complete_sale(self, customer_id: int = None) -> Dict:
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

        conn = get_connection()
        cur = conn.cursor()
        total_amount = self.total()
        date = now_iso()
        cur.execute(
            'INSERT INTO sales (date, total, customer_id) VALUES (?, ?, ?)',
            (date, total_amount, customer_id),
        )
        sale_id = cur.lastrowid

        for item in self.cart:
            p = item['product']
            q = int(item['quantity'])
            cur.execute('INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)', (sale_id, p.id, q, p.price))

            # reduce stock
            new_qty = max(0, p.quantity - q)
            cur.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_qty, p.id))

        conn.commit()
        conn.close()

        sale = {
            'id': sale_id,
            'date': date,
            'total': total_amount,
            'items': [{'name': i['product'].name, 'barcode': i['product'].barcode, 'quantity': i['quantity'], 'price': i['product'].price} for i in self.cart],
        }

        # write a simple receipt
        write_receipt(sale)

        # clear cart
        self.clear_cart()

        return sale
