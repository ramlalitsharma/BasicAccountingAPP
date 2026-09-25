"""Customer portal client — push per-customer account data to the cloud server
so customers can view their live statement from any phone browser.

Server contract (Cloudflare Worker, /api/portal/*):
  POST /api/portal/invite  {key_hash, machine_id, customer_name, phone, pin}
  POST /api/portal/sync    {key_hash, machine_id, phone, summary, rows}
  (customer side lives at <server>/portal — phone + PIN login)

Gating: portal sync requires the ``customer_notifications`` feature (Basic+
plans) and an activated license (key_hash present). Everything degrades to a
no-op with a clear message otherwise.
"""
from __future__ import annotations

import json
import logging
import secrets
import urllib.error
import urllib.request
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_TIMEOUT = 20


def _gs(key, default=None):
    from config import get_setting
    return get_setting(key, default)


def portal_enabled() -> bool:
    return bool(_gs("portal.enabled", True))


def _server_root() -> str:
    from utils.license import LICENSE_SERVER_URL
    return LICENSE_SERVER_URL.rstrip("/").removesuffix("/api")


def portal_url() -> str:
    """Public customer-facing portal URL (share this with customers)."""
    return _server_root() + "/portal"


def _identity() -> Tuple[str, str]:
    """(key_hash, machine_id) or ("", "") when no license is activated."""
    try:
        from utils.license import license_mgr
        from utils.fingerprint import get_machine_id
        key_hash = getattr(license_mgr, "_license", {}).get("key_hash", "") or ""
        return key_hash, get_machine_id()
    except Exception:
        return "", ""


def is_licensed_for_portal() -> bool:
    return bool(_identity()[0])


def _post(path: str, payload: dict, timeout: int = _TIMEOUT) -> Tuple[bool, str]:
    url = _server_root() + path
    if not url.lower().startswith("https://"):
        return False, "Portal API must be HTTPS."
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "AccountingPro Portal/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ok = 200 <= getattr(resp, "status", 0) < 300
            data = json.loads(resp.read().decode("utf-8"))
        return (ok and bool(data.get("ok", ok)),
                str(data.get("error") or data.get("message") or "OK" if ok else "failed"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
            return False, str(data.get("error") or exc)
        except Exception:
            return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return False, f"Connection failed: {exc}"


def generate_pin() -> str:
    return f"{secrets.randbelow(900000) + 100000}"  # 6-digit


def invite_customer(customer: dict, pin: Optional[str] = None) -> Tuple[bool, str, str]:
    """Create/refresh a portal login for a customer. Returns (ok, msg, pin)."""
    key_hash, machine_id = _identity()
    if not key_hash:
        return False, "Activate a license first (Settings → License).", ""
    phone = "".join(c for c in str(customer.get("Phone", "") or customer.get("Contact", "") or "")
                    if c.isdigit() or c == "+").lstrip("+")
    if len(phone) < 7:
        return False, "Customer needs a phone number first (edit the customer).", ""
    pin = pin or generate_pin()
    ok, msg = _post("/api/portal/invite", {
        "key_hash": key_hash, "machine_id": machine_id,
        "customer_name": str(customer.get("Name", "") or "")[:120],
        "phone": phone, "pin": pin,
    })
    return ok, msg, (pin if ok else "")


def sync_customer(customer: dict) -> Tuple[bool, str]:
    """Push the latest statement snapshot for one customer."""
    key_hash, machine_id = _identity()
    if not key_hash:
        return False, "No license activated."
    phone = "".join(c for c in str(customer.get("Phone", "") or customer.get("Contact", "") or "")
                    if c.isdigit() or c == "+").lstrip("+")
    if not phone:
        return False, "Customer has no phone number."
    from database import models
    from utils.formatters import safe_float
    rows_raw = models.get_customer_statement(customer.get("ID"))
    rows = [{
        "date": str(r.get("Sale_Date") or "")[:10],
        "receipt": r.get("Receipt_No", ""),
        "item": r.get("item_name", ""),
        "qty": r.get("Quantity_Sold", 0),
        "total": round(safe_float(r.get("Total", 0)), 2),
        "paid": round(safe_float(r.get("Paid_Amount", 0)), 2),
        "unpaid": round(safe_float(r.get("Unpaid_Amount", 0)), 2),
        "status": (r.get("Payment_Status") or "paid"),
    } for r in rows_raw]
    summary = {
        "total_billed": round(sum(r["total"] for r in rows), 2),
        "total_due": round(sum(r["unpaid"] for r in rows), 2),
        "sale_count": len(rows),
    }
    return _post("/api/portal/sync", {
        "key_hash": key_hash, "machine_id": machine_id,
        "phone": phone, "summary": summary, "rows": rows,
    })


def _opted_in(customer: Optional[dict]) -> bool:
    if not customer:
        return False
    return str(customer.get("Portal_Enabled", "")).strip().lower() in ("yes", "true", "1")


def sync_enabled_customers() -> Tuple[int, int]:
    """Sync all portal-enabled customers. Returns (synced, failed)."""
    if not (portal_enabled() and is_licensed_for_portal()):
        return 0, 0
    try:
        from database import models
        customers = models.get_customers()
    except Exception:
        return 0, 0
    synced = failed = 0
    for c in customers:
        if not _opted_in(c):
            continue
        ok, _msg = sync_customer(c)
        synced += ok
        failed += (not ok)
    return synced, failed


def sync_after_sale(customer: Optional[dict]) -> None:
    """Called after a sale: refresh the portal snapshot when applicable.
    Call on a background thread — performs network I/O."""
    if not (portal_enabled() and _opted_in(customer) and is_licensed_for_portal()):
        return
    ok, msg = sync_customer(customer)
    if not ok:
        logger.debug("Portal sync skipped: %s", msg)


def build_share_text(customer: dict, pin: str) -> str:
    try:
        from utils.company import load_company
        shop = load_company().get("name") or "your shop"
    except Exception:
        shop = "your shop"
    name = customer.get("Name", "")
    phone = "".join(c for c in str(customer.get("Phone", "") or customer.get("Contact", "") or "")
                    if c.isdigit() or c == "+").lstrip("+")
    return ("Hello {name}! {shop} has created your customer account.\n\n"
            "Open the Customer Portal: {url}\n"
            "Login with:\n"
            "  Mobile: {phone}\n"
            "  PIN: {pin}\n\n"
            "See your purchases, receipts and balance anytime.").format(
                name=name, shop=shop, url=portal_url(), phone=phone, pin=pin)
