from dataclasses import dataclass


@dataclass
class SaleItem:
    id: int | None
    sale_id: int
    product_id: int
    quantity: int
    price: float
