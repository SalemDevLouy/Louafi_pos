from dataclasses import dataclass, field


@dataclass
class Product:
    id: int | None
    name: str
    barcode: str | None
    price: float
    quantity: int
    category: str | None
    min_level: int = 5
    cost_price: float = 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'barcode': self.barcode,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category,
            'min_level': self.min_level,
            'cost_price': self.cost_price,
        }
