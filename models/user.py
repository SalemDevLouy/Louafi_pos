from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: int = 0
    username: str = ""
    password_hash: str = ""
    role: str = "cashier"
    full_name: str = ""
    is_active: bool = True
    must_change_password: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: str | None = None
