import configparser
import logging
import os
import shutil
import traceback
import zipfile
from datetime import datetime

logger = logging.getLogger(__name__)


def _config() -> tuple[str, str]:
    cfg = configparser.ConfigParser()
    cfg.read("config.ini")
    db_path = cfg.get("database", "path", fallback="pos.db")
    dest = cfg.get("backup", "destination", fallback="backups/")
    return db_path, dest


def create_backup() -> tuple[bool, str]:
    try:
        db_path, dest = _config()
        os.makedirs(dest, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(dest, f"backup_{timestamp}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(db_path):
                zf.write(db_path, os.path.basename(db_path))
            if os.path.exists("config.ini"):
                zf.write("config.ini", "config.ini")
            if os.path.exists("license.key"):
                zf.write("license.key", "license.key")
        return True, zip_path
    except Exception:
        logger.error("backup.create_backup\n%s", traceback.format_exc())
        return False, "Backup failed"


def restore_backup(zip_path: str) -> tuple[bool, str]:
    try:
        db_path, _ = _config()
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            db_name = os.path.basename(db_path)
            if db_name not in names:
                return False, f"Archive does not contain {db_name}"
            zf.extract(db_name, ".")
            if "config.ini" in names:
                zf.extract("config.ini", ".")
            if "license.key" in names:
                zf.extract("license.key", ".")
        return True, "Restore successful — please restart the application"
    except Exception:
        logger.error("backup.restore_backup\n%s", traceback.format_exc())
        return False, "Restore failed"


def list_backups() -> list[dict]:
    try:
        _, dest = _config()
        if not os.path.isdir(dest):
            return []
        files = sorted(
            (f for f in os.listdir(dest) if f.startswith("backup_") and f.endswith(".zip")),
            reverse=True,
        )
        result = []
        for fname in files:
            full = os.path.join(dest, fname)
            result.append({
                "filename": fname,
                "path": full,
                "size_kb": round(os.path.getsize(full) / 1024, 1),
                "mtime": datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M"),
            })
        return result
    except Exception:
        logger.error("backup.list_backups\n%s", traceback.format_exc())
        return []
