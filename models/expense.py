from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Expense:
    id: int = 0
    category: str = ""
    description: str = ""
    amount: float = 0.0
    paid_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
