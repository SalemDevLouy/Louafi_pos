import bcrypt
import logging
import traceback

logger = logging.getLogger(__name__)

_session: dict | None = None


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        logger.error("verify_password failed\n%s", traceback.format_exc())
        return False


def set_session(user_row: dict) -> None:
    global _session
    _session = dict(user_row)


def get_session() -> dict | None:
    return _session


def clear_session() -> None:
    global _session
    _session = None


def current_user_id() -> int | None:
    return _session["id"] if _session else None


def current_role() -> str | None:
    return _session["role"] if _session else None


def require_role(*roles: str) -> bool:
    return current_role() in roles
