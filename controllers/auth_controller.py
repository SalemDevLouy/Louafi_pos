import logging
import traceback
from datetime import datetime

from database.db import get_connection
from utils import auth, audit

logger = logging.getLogger(__name__)


def login(username: str, password: str) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
        ).fetchone()
        if not row:
            return False, "Invalid username or password"
        user = dict(row)
        if not auth.verify_password(password, user["password_hash"]):
            return False, "Invalid username or password"
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user["id"]),
        )
        conn.commit()
        auth.set_session(user)
        return True, user
    except Exception:
        logger.error("auth_controller.login\n%s", traceback.format_exc())
        return False, "Login error"


def logout() -> None:
    auth.clear_session()


def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
    try:
        conn = get_connection()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return False, "User not found"
        user = dict(row)
        if not auth.verify_password(old_password, user["password_hash"]):
            return False, "Current password is incorrect"
        new_hash = auth.hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
            (new_hash, user_id),
        )
        conn.commit()
        audit.log_action(user_id, "CHANGE_PASSWORD", "users", user_id)
        return True, "Password changed successfully"
    except Exception:
        logger.error("auth_controller.change_password\n%s", traceback.format_exc())
        return False, "Failed to change password"


def get_all_users() -> tuple[bool, list | str]:
    try:
        # RBAC: user listings are admin-only
        if not auth.require_role('admin'):
            return False, "Admin privileges required"
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, username, role, full_name, is_active, created_at, last_login, must_change_password FROM users ORDER BY id"
        ).fetchall()
        return True, [dict(r) for r in rows]
    except Exception:
        logger.error("auth_controller.get_all_users\n%s", traceback.format_exc())
        return False, "Failed to retrieve users"


def create_user(actor_id: int, username: str, password: str,
                role: str, full_name: str) -> tuple[bool, str]:
    try:
        # RBAC: only admins may create users (defense in depth — the view
        # already hides this from non-admins)
        if not auth.require_role('admin'):
            return False, "Admin privileges required"
        if role not in ("admin", "supervisor", "cashier"):
            return False, "Invalid role"
        conn = get_connection()
        exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if exists:
            return False, "Username already exists"
        pw_hash = auth.hash_password(password)
        cur = conn.execute(
            """INSERT INTO users (username, password_hash, role, full_name, is_active, must_change_password)
               VALUES (?, ?, ?, ?, 1, 1)""",
            (username, pw_hash, role, full_name),
        )
        conn.commit()
        audit.log_action(actor_id, "CREATE", "users", cur.lastrowid,
                         new_value={"username": username, "role": role, "full_name": full_name})
        return True, "User created successfully"
    except Exception:
        logger.error("auth_controller.create_user\n%s", traceback.format_exc())
        return False, "Failed to create user"


def toggle_user_active(actor_id: int, user_id: int) -> tuple[bool, str]:
    try:
        # RBAC: only admins may activate/deactivate users
        if not auth.require_role('admin'):
            return False, "Admin privileges required"
        conn = get_connection()
        row = conn.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return False, "User not found"
        new_state = 0 if row["is_active"] else 1
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
        conn.commit()
        action = "ACTIVATE" if new_state else "DEACTIVATE"
        audit.log_action(actor_id, action, "users", user_id)
        return True, "User status updated"
    except Exception:
        logger.error("auth_controller.toggle_user_active\n%s", traceback.format_exc())
        return False, "Failed to update user"


def update_user(actor_id: int, user_id: int, full_name: str,
                role: str) -> tuple[bool, str]:
    try:
        # RBAC: only admins may change users/roles
        if not auth.require_role('admin'):
            return False, "Admin privileges required"
        if role not in ("admin", "supervisor", "cashier"):
            return False, "Invalid role"
        conn = get_connection()
        old = conn.execute(
            "SELECT full_name, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not old:
            return False, "User not found"
        conn.execute(
            "UPDATE users SET full_name = ?, role = ? WHERE id = ?",
            (full_name, role, user_id),
        )
        conn.commit()
        audit.log_action(actor_id, "UPDATE", "users", user_id,
                         old_value=dict(old),
                         new_value={"full_name": full_name, "role": role})
        return True, "User updated successfully"
    except Exception:
        logger.error("auth_controller.update_user\n%s", traceback.format_exc())
        return False, "Failed to update user"


def admin_reset_password(actor_id: int, user_id: int,
                         new_password: str) -> tuple[bool, str]:
    try:
        # RBAC: only admins may reset other users' passwords
        if not auth.require_role('admin'):
            return False, "Admin privileges required"
        conn = get_connection()
        new_hash = auth.hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
            (new_hash, user_id),
        )
        conn.commit()
        audit.log_action(actor_id, "RESET_PASSWORD", "users", user_id)
        return True, "Password reset — user must change it on next login"
    except Exception:
        logger.error("auth_controller.admin_reset_password\n%s", traceback.format_exc())
        return False, "Failed to reset password"
