import hashlib
import hmac
import logging
import os
import traceback
import uuid
from datetime import date, datetime

import configparser

logger = logging.getLogger(__name__)

_SECRET = b"POS_ALGERIA_2024_SECRET"
_KEY_FILE = "license.key"
_STATUS: dict = {"valid": False, "expiry": None, "store_id": None, "days_left": None}


def _hw_fingerprint() -> str:
    mac = uuid.getnode()
    return hashlib.sha256(str(mac).encode()).hexdigest()[:16].upper()


def _encode_key(store_id: str, expiry_str: str) -> str:
    # Format: SSSS-DDDDDDDD-CCCC  (store 4 + date 8 + check 4 = 16 → groups of 4)
    payload = f"{store_id[:4].upper()}:{expiry_str}:{_hw_fingerprint()}"
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:4].upper()
    raw = f"{store_id[:4].upper()}{expiry_str.replace('-', '')}{sig}"  # exactly 16
    return "-".join(raw[i:i+4] for i in range(0, 16, 4))


def _decode_key(key: str) -> tuple[bool, dict | str]:
    try:
        raw = key.replace("-", "").upper()
        if len(raw) != 16:
            return False, "Invalid key format"
        store_id = raw[:4]
        expiry_str = raw[4:12]
        sig_given = raw[12:16]
        expiry = datetime.strptime(expiry_str, "%Y%m%d").date()
        payload = f"{store_id}:{expiry.isoformat()}:{_hw_fingerprint()}"
        sig_expected = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:4].upper()
        if not hmac.compare_digest(sig_given, sig_expected):
            return False, "Key does not match this machine"
        return True, {"store_id": store_id, "expiry": expiry}
    except Exception:
        logger.error("license._decode_key\n%s", traceback.format_exc())
        return False, "Malformed license key"


def activate(key: str) -> tuple[bool, str]:
    ok, result = _decode_key(key)
    if not ok:
        return False, result
    try:
        _read_config_key_file_path()
        with open(_key_file_path(), "w") as f:
            f.write(key.strip())
        _refresh_status(result["store_id"], result["expiry"])
        return True, "License activated successfully"
    except Exception:
        logger.error("license.activate\n%s", traceback.format_exc())
        return False, "Could not save license key"


def check() -> dict:
    path = _key_file_path()
    if not os.path.exists(path):
        _STATUS.update({"valid": False, "expiry": None, "store_id": None, "days_left": None})
        return _STATUS
    try:
        with open(path) as f:
            key = f.read().strip()
        ok, result = _decode_key(key)
        if not ok:
            _STATUS.update({"valid": False, "expiry": None, "store_id": None, "days_left": None})
            return _STATUS
        _refresh_status(result["store_id"], result["expiry"])
    except Exception:
        logger.error("license.check\n%s", traceback.format_exc())
        _STATUS.update({"valid": False})
    return _STATUS


def is_valid() -> bool:
    return _STATUS.get("valid", False)


def _refresh_status(store_id: str, expiry: date) -> None:
    today = date.today()
    days_left = (expiry - today).days
    _STATUS.update({
        "valid": days_left >= 0,
        "expiry": expiry.isoformat(),
        "store_id": store_id,
        "days_left": days_left,
    })


def _key_file_path() -> str:
    return _KEY_FILE


def _read_config_key_file_path() -> None:
    global _KEY_FILE
    cfg = configparser.ConfigParser()
    if cfg.read("config.ini") and cfg.has_option("license", "key_file"):
        _KEY_FILE = cfg.get("license", "key_file")
