import json
import os
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from config import DATA_DIR

SUB_FILE = os.path.join(DATA_DIR, "subscription.json")
SECRET_KEY = b"AccountingPro-HMAC-Key-2026"
GRACE_DAYS = 15
MONTHLY_PRICE = 500
TOKEN_PRICE = 50
TOKENS_PER_PURCHASE = 10
ADMIN_PASSWORD = "admin"


def _load():
    if not os.path.exists(SUB_FILE):
        return {"subscriber": "", "activated": "", "expires": "",
                "tokens": 0, "tokens_used": 0, "license_type": "none"}
    with open(SUB_FILE, "r") as f:
        return json.load(f)


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SUB_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _make_payload(subscriber, expires, tokens):
    payload = {"s": subscriber, "e": expires, "t": tokens, "v": 1}
    raw = json.dumps(payload, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(raw.encode()).decode()
    sig = hmac.new(SECRET_KEY, encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def _verify_key(key):
    try:
        parts = key.strip().split(".")
        if len(parts) != 2:
            return None
        encoded, sig = parts
        expected = hmac.new(SECRET_KEY, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        raw = base64.urlsafe_b64decode(encoded + "==").decode()
        payload = json.loads(raw)
        return {
            "subscriber": payload["s"],
            "expires": payload["e"],
            "tokens": payload["t"],
        }
    except Exception:
        return None


def generate_license(subscriber, months=1, tokens=0):
    expires = (datetime.now() + timedelta(days=30 * months)).strftime("%Y-%m-%d")
    return _make_payload(subscriber, expires, tokens)


def activate_license(key):
    info = _verify_key(key)
    if not info:
        return False, "Invalid license key"
    data = _load()
    data["subscriber"] = info["subscriber"]
    data["activated"] = datetime.now().strftime("%Y-%m-%d")
    data["expires"] = info["expires"]
    data["tokens"] = data.get("tokens", 0) + info["tokens"]
    data["tokens_used"] = data.get("tokens_used", 0)
    data["license_type"] = "subscription" if info["expires"] > datetime.now().strftime("%Y-%m-%d") else "tokens"
    data["license_key"] = key
    _save(data)
    return True, f"License activated! Expires: {info['expires']}, Tokens: {info['tokens']}"


def get_status():
    data = _load()
    now = datetime.now()
    expires_str = data.get("expires", "")
    if expires_str:
        expires = datetime.strptime(expires_str, "%Y-%m-%d")
        days_left = (expires - now).days
        grace_end = expires + timedelta(days=GRACE_DAYS)
        grace_days_left = (grace_end - now).days
        is_expired = days_left < 0
        in_grace = is_expired and grace_days_left >= 0
        blocked = grace_days_left < 0
    else:
        days_left = 0
        grace_days_left = 0
        is_expired = True
        in_grace = False
        blocked = True

    remaining_tokens = max(0, data.get("tokens", 0) - data.get("tokens_used", 0))
    return {
        "subscriber": data.get("subscriber", ""),
        "activated": data.get("activated", ""),
        "expires": expires_str,
        "days_left": days_left,
        "grace_days_left": grace_days_left,
        "is_expired": is_expired,
        "in_grace": in_grace,
        "blocked": blocked,
        "tokens": data.get("tokens", 0),
        "tokens_used": data.get("tokens_used", 0),
        "remaining_tokens": remaining_tokens,
        "license_type": data.get("license_type", "none"),
    }


def check_write_allowed():
    """Returns (allowed, message, needs_token).
    needs_token: if True, a token must be consumed for this write."""
    status = get_status()
    if not status["is_expired"]:
        # Active subscription - free writes
        return True, "", False
    # Expired but in grace period
    if status["in_grace"]:
        if status["remaining_tokens"] > 0:
            return True, "Using token (grace period)", True
        return True, "", False
    # Fully blocked
    if status["remaining_tokens"] > 0:
        return True, "Using token", True
    return False, "Subscription expired. Please renew at ₹500/month.", False


def use_token():
    data = _load()
    used = data.get("tokens_used", 0)
    total = data.get("tokens", 0)
    if used >= total:
        return False
    data["tokens_used"] = used + 1
    _save(data)
    return True


def add_tokens(additional):
    data = _load()
    data["tokens"] = data.get("tokens", 0) + additional
    _save(data)
    return data["tokens"]


def renew_subscription(months=1):
    data = _load()
    now = datetime.now()
    current_expires = data.get("expires", "")
    if current_expires and current_expires > now.strftime("%Y-%m-%d"):
        base = datetime.strptime(current_expires, "%Y-%m-%d")
    else:
        base = now
    data["expires"] = (base + timedelta(days=30 * months)).strftime("%Y-%m-%d")
    data["license_type"] = "subscription"
    _save(data)
    return data["expires"]
