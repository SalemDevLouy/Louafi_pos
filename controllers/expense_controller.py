import logging
import traceback
from database.db import get_connection
from utils import audit

logger = logging.getLogger(__name__)


def get_all(filters: dict | None = None) -> tuple[bool, list | str]:
    try:
        conn = get_connection()
        query = "SELECT * FROM expenses WHERE 1=1"
        params: list = []
        if filters:
            if filters.get("category"):
                query += " AND category = ?"
                params.append(filters["category"])
            if filters.get("date_from"):
                query += " AND DATE(created_at) >= ?"
                params.append(filters["date_from"])
            if filters.get("date_to"):
                query += " AND DATE(created_at) <= ?"
                params.append(filters["date_to"])
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return True, [dict(r) for r in rows]
    except Exception:
        logger.error("expense_controller.get_all\n%s", traceback.format_exc())
        return False, "Failed to retrieve expenses"


def create(user_id: int, category: str, description: str,
           amount: float, paid_by: str) -> tuple[bool, str]:
    try:
        conn = get_connection()
        cur = conn.execute(
            "INSERT INTO expenses (category, description, amount, paid_by) VALUES (?, ?, ?, ?)",
            (category, description, amount, paid_by),
        )
        conn.commit()
        audit.log_action(user_id, "CREATE", "expenses", cur.lastrowid,
                         new_value={"category": category, "amount": amount})
        return True, "Expense recorded"
    except Exception:
        logger.error("expense_controller.create\n%s", traceback.format_exc())
        return False, "Failed to record expense"


def update(user_id: int, expense_id: int, category: str,
           description: str, amount: float, paid_by: str) -> tuple[bool, str]:
    try:
        conn = get_connection()
        old = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if not old:
            return False, "Expense not found"
        conn.execute(
            "UPDATE expenses SET category=?, description=?, amount=?, paid_by=? WHERE id=?",
            (category, description, amount, paid_by, expense_id),
        )
        conn.commit()
        audit.log_action(user_id, "UPDATE", "expenses", expense_id,
                         old_value=dict(old),
                         new_value={"category": category, "amount": amount})
        return True, "Expense updated"
    except Exception:
        logger.error("expense_controller.update\n%s", traceback.format_exc())
        return False, "Failed to update expense"


def delete(user_id: int, expense_id: int) -> tuple[bool, str]:
    try:
        conn = get_connection()
        old = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if not old:
            return False, "Expense not found"
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        audit.log_action(user_id, "DELETE", "expenses", expense_id, old_value=dict(old))
        return True, "Expense deleted"
    except Exception:
        logger.error("expense_controller.delete\n%s", traceback.format_exc())
        return False, "Failed to delete expense"


def get_summary(date_from: str, date_to: str) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM expenses
               WHERE DATE(created_at) BETWEEN ? AND ?
               GROUP BY category
               ORDER BY total DESC""",
            (date_from, date_to),
        ).fetchall()
        total = sum(r["total"] for r in rows)
        return True, {"by_category": [dict(r) for r in rows], "total": total}
    except Exception:
        logger.error("expense_controller.get_summary\n%s", traceback.format_exc())
        return False, "Failed to get expense summary"


def get_categories() -> list[str]:
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT DISTINCT category FROM expenses ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]
    except Exception:
        return []
