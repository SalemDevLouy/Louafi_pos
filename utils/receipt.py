import os
from datetime import datetime


RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'receipts')


def write_receipt(sale: dict) -> str:
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    fname = f"receipt_{sale['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(RECEIPTS_DIR, fname)

    lines = []
    lines.append('--- POS Receipt ---')
    lines.append(f"Sale ID: {sale['id']}")
    lines.append(f"Date: {sale['date']}")
    lines.append('')
    lines.append('Items:')
    for it in sale['items']:
        lines.append(f"{it['name']} x{it['quantity']} @ {it['price']:.2f} -> {it['quantity']*it['price']:.2f}")
    lines.append('')
    lines.append(f"Total: {sale['total']:.2f}")
    lines.append('Thank you for your purchase!')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return path


def write_return_receipt(ret: dict) -> str:
    """Write a text receipt for a return/refund.

    ``ret`` is the dict returned by ``ReturnsController.create_return`` and
    contains ``items`` (each with ``product_name``, ``quantity``,
    ``unit_price``, ``subtotal``).
    """
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    fname = f"return_{ret['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(RECEIPTS_DIR, fname)

    lines = []
    lines.append('--- POS Return Receipt ---')
    lines.append(f"Return ID: {ret['id']}")
    lines.append(f"Original Sale ID: {ret['sale_id']}")
    lines.append(f"Date: {ret['created_at']}")
    lines.append('')
    lines.append('Returned Items:')
    for it in ret.get('items', []):
        name = it.get('product_name', 'Item')
        qty = int(it.get('quantity', 0))
        price = float(it.get('unit_price', 0))
        sub = float(it.get('subtotal', qty * price))
        lines.append(f"{name} x{qty} @ {price:.2f} -> {sub:.2f}")
    lines.append('')
    lines.append(f"Total Refund: {ret['total_refund']:.2f}")
    lines.append('Customer signature: ______________________')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return path
