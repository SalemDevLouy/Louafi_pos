"""
LouafiPOS — License Key Generator
Run:  python keygen.py
"""
import hashlib, hmac, sys, uuid
from datetime import date, datetime

_SECRET = b"POS_ALGERIA_2024_SECRET"


def fingerprint() -> str:
    mac = uuid.getnode()
    return hashlib.sha256(str(mac).encode()).hexdigest()[:16].upper()


def generate(store_id: str, expiry: str) -> str:
    """
    store_id : 4-char store code, e.g. LPOS or ELZW
    expiry   : date string YYYY-MM-DD
    """
    sid = store_id[:4].upper()
    fp  = fingerprint()
    payload = f"{sid}:{expiry}:{fp}"
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:4].upper()
    raw = f"{sid}{expiry.replace('-', '')}{sig}"   # 4+8+4 = 16 chars
    return "-".join(raw[i:i+4] for i in range(0, 16, 4))


def main():
    print("=" * 48)
    print("   LouafiPOS  —  License Key Generator")
    print("=" * 48)
    print(f"  Machine fingerprint : {fingerprint()}")
    print()

    store_id = input("  Store ID (4 chars, e.g. LPOS) : ").strip() or "LPOS"
    expiry   = input("  Expiry date (YYYY-MM-DD)      : ").strip()

    try:
        datetime.strptime(expiry, "%Y-%m-%d")
    except ValueError:
        print("  ERROR: date must be YYYY-MM-DD format.")
        sys.exit(1)

    key = generate(store_id, expiry)
    print()
    print("  ┌─────────────────────────┐")
    print(f"  │  Key : {key:>16}  │")
    print("  └─────────────────────────┘")
    print()
    print("  Paste this key into the activation dialog when you start the app.")
    print("  IMPORTANT: this key is valid ONLY on this machine.")


if __name__ == "__main__":
    main()
