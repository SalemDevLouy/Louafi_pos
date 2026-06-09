import json
import logging
import traceback
from database.db import get_connection

logger = logging.getLogger(__name__)


def log_action(user_id: int, action: str, table_name: str,
               record_id=None, old_value=None, new_value=None) -> None:
    try:
        conn = get_connection()
        conn.execute(
            """INSERT INTO audit_log
               (user_id, action, table_name, record_id, old_value, new_value)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                action,
                table_name,
                record_id,
                json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
                json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
            ),
        )
        conn.commit()
    except Exception:
        logger.error("audit.log_action failed\n%s", traceback.format_exc())


def get_log(filters: dict | None = None):
    try:
        conn = get_connection()
        query = """
            SELECT al.id, u.username, al.action, al.table_name,
                   al.record_id, al.old_value, al.new_value, al.created_at
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE 1=1
        """
        params: list = []

        if filters:
            if filters.get("user_id"):
                query += " AND al.user_id = ?"
                params.append(filters["user_id"])
            if filters.get("table_name"):
                query += " AND al.table_name = ?"
                params.append(filters["table_name"])
            if filters.get("date_from"):
                query += " AND DATE(al.created_at) >= ?"
                params.append(filters["date_from"])
            if filters.get("date_to"):
                query += " AND DATE(al.created_at) <= ?"
                params.append(filters["date_to"])

        query += " ORDER BY al.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return True, [dict(r) for r in rows]
    except Exception:
        logger.error("audit.get_log failed\n%s", traceback.format_exc())
        return False, "Failed to retrieve audit log"
