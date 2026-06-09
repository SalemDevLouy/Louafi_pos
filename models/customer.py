from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Customer:
    id: int = 0
    full_name: str = ""
    phone: str = ""
    address: str = ""
    loyalty_points: int = 0
    total_purchases: float = 0.0
    debt_amount: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
