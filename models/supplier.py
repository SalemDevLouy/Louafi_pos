from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Supplier:
    id: Optional[int]
    name: str
    phone: str
    category: str

    def to_dict(self):
        return vars(self)


@dataclass
class BillingOrder:
    id: Optional[int]
    supplier_id: int
    date: str
    note: str

    def to_dict(self):
        return vars(self)


@dataclass
class BillingItem:
    id: Optional[int]
    billing_order_id: int
    product_id: int
    product_name: str   # denormalized for display
    quantity: int
    buy_price: float
    sale_price: float

    def to_dict(self):
        return vars(self)
