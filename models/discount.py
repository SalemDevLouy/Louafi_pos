from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Discount:
    id: int = 0
    name: str = ""
    type: str = "percentage"
    value: float = 0.0
    coupon_code: str | None = None
    min_purchase: float | None = None
    is_active: bool = True
    valid_from: str | None = None
    valid_to: str | None = None
