import logging
import traceback
from datetime import date
from database.db import get_connection
from utils import audit

logger = logging.getLogger(__name__)


def get_all(active_only: bool = False) -> tuple[bool, list | str]:
    try:
        conn = get_connection()
        query = "SELECT * FROM discounts WHERE 1=1"
        params: list = []
        if active_only:
            today = date.today().isoformat()
            query += " AND is_active = 1 AND (valid_from IS NULL OR valid_from <= ?) AND (valid_to IS NULL OR valid_to >= ?)"
            params.extend([today, today])
        query += " ORDER BY name"
        rows = conn.execute(query, params).fetchall()
        return True, [dict(r) for r in rows]
    except Exception:
        logger.error("discount_controller.get_all\n%s", traceback.format_exc())
        return False, "Failed to retrieve discounts"


def get_by_id(discount_id: int) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        row = conn.execute("SELECT * FROM discounts WHERE id = ?", (discount_id,)).fetchone()
        if not row:
            return False, "Discount not found"
        return True, dict(row)
    except Exception:
        logger.error("discount_controller.get_by_id\n%s", traceback.format_exc())
        return False, "Failed to retrieve discount"


def get_by_coupon(code: str) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        today = date.today().isoformat()
        row = conn.execute(
            """SELECT * FROM discounts
               WHERE coupon_code = ? AND is_active = 1
               AND (valid_from IS NULL OR valid_from <= ?)
               AND (valid_to IS NULL OR valid_to >= ?)""",
            (code, today, today),
        ).fetchone()
        if not row:
            return False, "Invalid or expired coupon"
        return True, dict(row)
    except Exception:
        logger.error("discount_controller.get_by_coupon\n%s", traceback.format_exc())
        return False, "Failed to validate coupon"


def apply_discount(discount: dict, subtotal: float) -> float:
    if discount.get("min_purchase") and subtotal < discount["min_purchase"]:
        return 0.0
    if discount["type"] == "percentage":
        return round(subtotal * discount["value"] / 100, 2)
    if discount["type"] == "fixed":
        return min(round(discount["value"], 2), subtotal)
    if discount["type"] == "coupon":
        if discount.get("value", 0) <= 1:
            return round(subtotal * discount["value"], 2)
        return min(round(discount["value"], 2), subtotal)
    return 0.0


def create(user_id: int, name: str, dtype: str, value: float,
           coupon_code: str | None, min_purchase: float | None,
           valid_from: str | None, valid_to: str | None) -> tuple[bool, str]:
    try:
        if dtype not in ("percentage", "fixed", "coupon"):
            return False, "Invalid discount type"
        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO discounts (name, type, value, coupon_code, min_purchase, is_active, valid_from, valid_to)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
            (name, dtype, value, coupon_code, min_purchase, valid_from, valid_to),
        )
        conn.commit()
        audit.log_action(user_id, "CREATE", "discounts", cur.lastrowid,
                         new_value={"name": name, "type": dtype, "value": value})
        return True, "Discount created"
    except Exception:
        logger.error("discount_controller.create\n%s", traceback.format_exc())
        return False, "Failed to create discount"


def update(user_id: int, discount_id: int, name: str, dtype: str,
           value: float, coupon_code: str | None, min_purchase: float | None,
           is_active: bool, valid_from: str | None, valid_to: str | None) -> tuple[bool, str]:
    try:
        if dtype not in ("percentage", "fixed", "coupon"):
            return False, "Invalid discount type"
        conn = get_connection()
        old = conn.execute("SELECT * FROM discounts WHERE id = ?", (discount_id,)).fetchone()
        if not old:
            return False, "Discount not found"
        conn.execute(
            """UPDATE discounts SET name=?, type=?, value=?, coupon_code=?,
               min_purchase=?, is_active=?, valid_from=?, valid_to=? WHERE id=?""",
            (name, dtype, value, coupon_code, min_purchase,
             1 if is_active else 0, valid_from, valid_to, discount_id),
        )
        conn.commit()
        audit.log_action(user_id, "UPDATE", "discounts", discount_id,
                         old_value=dict(old),
                         new_value={"name": name, "type": dtype, "value": value})
        return True, "Discount updated"
    except Exception:
        logger.error("discount_controller.update\n%s", traceback.format_exc())
        return False, "Failed to update discount"


def delete(user_id: int, discount_id: int) -> tuple[bool, str]:
    try:
        conn = get_connection()
        old = conn.execute("SELECT * FROM discounts WHERE id = ?", (discount_id,)).fetchone()
        if not old:
            return False, "Discount not found"
        conn.execute("DELETE FROM discounts WHERE id = ?", (discount_id,))
        conn.commit()
        audit.log_action(user_id, "DELETE", "discounts", discount_id, old_value=dict(old))
        return True, "Discount deleted"
    except Exception:
        logger.error("discount_controller.delete\n%s", traceback.format_exc())
        return False, "Failed to delete discount"
