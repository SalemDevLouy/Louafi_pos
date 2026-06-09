from dataclasses import dataclass


@dataclass
class Sale:
    id: int | None
    date: str
    total: float
