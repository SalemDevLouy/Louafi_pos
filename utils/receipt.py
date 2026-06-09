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
