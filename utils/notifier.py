"""Email / WhatsApp notification helper.

Two transports:
  - ``send_email``     — SMTP (TLS). Honours per-license feature gates and
                          the per-recipient opt-in fields on the customer /
                          supplier records.
  - ``send_whatsapp``  — opens the WhatsApp Web URL with a pre-filled
                          message and the customer's phone number. Requires
                          no API key; the user clicks Send manually.

Both functions return ``(success: bool, message: str)`` so the caller can
toast the result.

SMTP settings live in the desktop app's ``config`` / settings JSON so they
can be edited in the UI; nothing is hardcoded. The SMTP password is stored
DPAPI-encrypted via :class:`utils.secrets_store.SecretsStore`, never in the
plain settings JSON.

TLS / authentication:
  - Uses STARTTLS on port 587 (most common). Falls back to SMTP_SSL on 465.
  - Passwords are read from the secrets store (DPAPI) where possible.

Why this is safe:
  - We never log SMTP credentials
  - We never include the password in the email body
  - We use ``email.utils.formataddr`` to avoid header injection
  - We refuse to send to recipients that have not opted in (the
    customer/supplier ``notify_email`` checkbox must be True)
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
import urllib.parse
import webbrowser
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Iterable, Optional, Tuple

logger = logging.getLogger(__name__)


# ── secrets (DPAPI) for the SMTP password ─────────────────────────────────
def _smtp_secrets_store():
    from config import CONFIG_DIR
    from utils.secrets_store import SecretsStore
    return SecretsStore(
        os.path.join(str(CONFIG_DIR), "smtp.enc"),
        description="AccountingPro SMTP password",
    )


def save_smtp_password(password: str) -> None:
    """Persist the SMTP password DPAPI-encrypted. Empty string clears it."""
    store = _smtp_secrets_store()
    if password:
        store.save({"smtp_password": password})
    else:
        store.clear()


def load_smtp_password() -> str:
    try:
        return str(_smtp_secrets_store().load().get("smtp_password", "") or "")
    except Exception:
        return ""


# ── settings (loaded from config.get_setting) ─────────────────────────────
def _smtp_settings() -> dict:
    """Read SMTP config from settings. Returns a dict with all None values
    if SMTP isn't configured yet. Password is read from the DPAPI secrets
    store first, falling back to the legacy settings key."""
    try:
        from config import get_setting
    except ImportError:
        get_setting = lambda k, d=None: d
    password = load_smtp_password() or (get_setting("notifications.smtp_password", "") or "").strip()
    return {
        "host":     (get_setting("notifications.smtp_host", "") or "").strip(),
        "port":     int(get_setting("notifications.smtp_port", 587) or 587),
        "user":     (get_setting("notifications.smtp_user", "") or "").strip(),
        "password": password,
        "from_name":(get_setting("notifications.smtp_from_name", "Accounting Pro") or "").strip(),
        "from_email":(get_setting("notifications.smtp_from_email", "") or "").strip(),
        "use_tls":  bool(get_setting("notifications.smtp_use_tls", True)),
    }


def notifications_enabled() -> bool:
    try:
        from config import get_setting
    except ImportError:
        return False
    return bool(get_setting("notifications.enabled", True))


def is_email_configured() -> bool:
    s = _smtp_settings()
    return bool(s["host"]) and bool(s["user"]) and bool(s["from_email"])


# ── email send ────────────────────────────────────────────────────────────
def send_email(*, to_email: str, subject: str, body_text: str,
               body_html: Optional[str] = None,
               cc: Iterable[str] = (),
               attachment_path: Optional[str] = None,
               attachment_filename: Optional[str] = None,
               override_from_email: Optional[str] = None,
               override_from_name: Optional[str] = None) -> Tuple[bool, str]:
    """Send a single email. Returns (success, message)."""
    if not to_email or "@" not in to_email:
        return False, "Invalid recipient email address."
    if not is_email_configured():
        return False, ("SMTP is not configured. Go to Settings → Notifications "
                       "and set the SMTP host/user/password first.")
    s = _smtp_settings()
    from_email = (override_from_email or s["from_email"]).strip()
    from_name = (override_from_name or s["from_name"]).strip() or "Accounting Pro"

    msg = EmailMessage()
    msg["Subject"] = subject[:200]
    msg["From"] = formataddr((from_name, from_email))
    # parseaddr + formataddr together prevent header injection
    rcpts = [parseaddr(to_email)[1] or to_email]
    cc_list = [parseaddr(c)[1] for c in cc if c and "@" in c]
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
        rcpts += [c for c in cc_list if c]
    msg["To"] = rcpts[0]
    msg.set_content(body_text or "")
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    if attachment_path and os.path.isfile(attachment_path):
        with open(attachment_path, "rb") as f:
            data = f.read()
        fname = attachment_filename or os.path.basename(attachment_path)
        # Guess mime type from filename extension.
        import mimetypes
        ctype, _ = mimetypes.guess_type(fname)
        if ctype is None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)

    try:
        host, port = s["host"], int(s["port"])
        if s["use_tls"] and port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as smtp:
                if s["user"]:
                    smtp.login(s["user"], s["password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                if s["use_tls"]:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if s["user"]:
                    smtp.login(s["user"], s["password"])
                smtp.send_message(msg)
        return True, f"Email sent to {to_email}"
    except smtplib.SMTPAuthenticationError as exc:
        return False, f"SMTP auth failed: {exc.smtp_code} {exc.smtp_error.decode(errors='replace') if isinstance(exc.smtp_error, bytes) else exc.smtp_error}"
    except (smtplib.SMTPException, OSError) as exc:
        return False, f"SMTP error: {exc}"
    except Exception as exc:  # pragma: no cover
        return False, f"Unexpected error: {exc}"


# ── WhatsApp (web-based, no API key) ─────────────────────────────────────
def send_whatsapp(*, to_phone: str, message: str) -> Tuple[bool, str]:
    """Open the WhatsApp Web ``send`` URL with a pre-filled message.

    No API key required. The operator clicks Send in the browser tab that
    opens. Returns (True, "Opened WhatsApp Web") so the caller can toast.
    """
    phone = "".join(c for c in (to_phone or "") if c.isdigit() or c == "+")
    if not phone:
        return False, "Invalid phone number."
    phone = phone.lstrip("+")
    url = f"https://wa.me/{phone}?text={urllib.parse.quote(message or '')}"
    try:
        webbrowser.open(url)
        return True, "Opened WhatsApp Web — click Send."
    except Exception as exc:
        return False, f"Could not open browser: {exc}"


# ── feature-gate aware wrappers ──────────────────────────────────────────
def send_email_gated(*, feature_id: str, **kwargs) -> Tuple[bool, str]:
    """Check the feature gate, then send. Returns (False, "feature locked")
    if the gate is off so the caller doesn't have to think about it."""
    from utils.feature_gate import require_feature
    from utils.license import license_mgr
    if not license_mgr.has_feature(feature_id):
        return False, ("This notification requires "
                       f"'{feature_id}' which is not enabled on your plan.")
    return send_email(**kwargs)


def send_whatsapp_gated(*, feature_id: str, **kwargs) -> Tuple[bool, str]:
    from utils.license import license_mgr
    if not license_mgr.has_feature(feature_id):
        return False, ("WhatsApp notifications are not enabled on your plan.")
    return send_whatsapp(**kwargs)


# ── diagnostics ───────────────────────────────────────────────────────────
def test_smtp_connection() -> Tuple[bool, str]:
    """Try to connect + (if credentials exist) authenticate. Sends nothing."""
    s = _smtp_settings()
    if not s["host"]:
        return False, "SMTP host is not configured."
    try:
        host, port = s["host"], int(s["port"])
        if s["use_tls"] and port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as smtp:
                if s["user"]:
                    smtp.login(s["user"], s["password"])
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                if s["use_tls"]:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if s["user"]:
                    smtp.login(s["user"], s["password"])
        return True, f"Connected to {host}:{port}" + (" and logged in." if s["user"] else ".")
    except smtplib.SMTPAuthenticationError as exc:
        detail = exc.smtp_error.decode(errors="replace") if isinstance(exc.smtp_error, bytes) else exc.smtp_error
        return False, f"Authentication failed ({exc.smtp_code}): {detail}"
    except (smtplib.SMTPException, OSError) as exc:
        return False, f"Connection failed: {exc}"
    except Exception as exc:  # pragma: no cover
        return False, f"Unexpected error: {exc}"


# ── message templates ─────────────────────────────────────────────────────
def _money(value) -> str:
    try:
        from config import get_setting
        sym = get_setting("currency_symbol", "\u20B9")
    except ImportError:
        sym = "\u20B9"
    try:
        return f"{sym}{float(value):,.2f}"
    except (ValueError, TypeError):
        return f"{sym}0.00"


def build_sale_receipt_text(sale: dict, customer_name: str = "") -> str:
    """Plain-text receipt for a sale (suitable for email body / WhatsApp)."""
    try:
        from utils.company import load_company
        company = load_company()
    except Exception:
        company = {}
    lines = []
    if company.get("name"):
        lines.append(str(company["name"]))
    if company.get("phone"):
        lines.append(f"Ph: {company['phone']}")
    lines.append("-" * 40)
    lines.append(f"SALE RECEIPT  {sale.get('receipt_no', '')}")
    lines.append(f"Date: {sale.get('sale_date', '')}")
    if customer_name:
        lines.append(f"Customer: {customer_name}")
    lines.append("-" * 40)
    lines.append(f"{sale.get('item_name', '')}")
    lines.append(
        f"  {sale.get('quantity_sold', 0)} x {_money(sale.get('price', 0))}"
        f" = {_money(sale.get('total', 0))}"
    )
    lines.append("-" * 40)
    lines.append(f"Total:   {_money(sale.get('total', 0))}")
    lines.append(f"Paid:    {_money(sale.get('paid_amount', 0))}")
    unpaid = sale.get("unpaid_amount", 0) or 0
    try:
        unpaid_f = float(unpaid)
    except (ValueError, TypeError):
        unpaid_f = 0.0
    if unpaid_f > 0:
        lines.append(f"Balance: {_money(unpaid_f)}")
    status = str(sale.get("payment_status", "paid")).upper()
    lines.append(f"Status:  {status}")
    if company.get("invoice_note"):
        lines.append("-" * 40)
        lines.append(str(company["invoice_note"]))
    lines.append("-" * 40)
    lines.append("Thank you for your business!")
    return "\n".join(lines)


def build_payment_reminder_text(customer_name: str, due_amount, due_sales=None) -> str:
    """Plain-text payment reminder for a customer with outstanding balance."""
    try:
        from utils.company import load_company
        company = load_company()
    except Exception:
        company = {}
    lines = []
    shop = company.get("name") or "our store"
    lines.append(f"Payment reminder from {shop}")
    lines.append("-" * 40)
    lines.append(f"Dear {customer_name or 'Customer'},")
    lines.append("")
    lines.append(f"This is a friendly reminder that a balance of "
                 f"{_money(due_amount)} is pending on your account with {shop}.")
    if due_sales:
        lines.append("")
        lines.append("Pending bills:")
        for s in due_sales[:10]:
            receipt = s.get("Receipt_No") or f"Sale #{s.get('ID', '')}"
            date = str(s.get("Sale_Date") or "")[:10]
            amount = _money(s.get("Unpaid_Amount", 0))
            lines.append(f"  • {receipt}  ({date})  —  {amount}")
    lines.append("")
    lines.append("Kindly arrange payment at your earliest convenience.")
    if company.get("phone"):
        lines.append(f"For any questions, call us at {company['phone']}.")
    lines.append("")
    lines.append("Thank you!")
    return "\n".join(lines)


def send_payment_reminder(customer: dict, due_amount, due_sales=None) -> list:
    """Send a payment reminder to a customer via their opted-in channels.

    Returns a list of ``(channel, ok, message)`` results. The caller shows
    them on the UI thread. No-op when reminders are disabled or the customer
    opted in to nothing.
    """
    results = []
    try:
        from config import get_setting
    except ImportError:
        return results
    if not notifications_enabled():
        return [("reminder", False, "Notifications are disabled (Settings → Notifications).")]
    if not bool(get_setting("notifications.enable_reminders", True)):
        return [("reminder", False, "Payment reminders are disabled (Settings → Notifications).")]
    if not customer:
        return [("reminder", False, "No customer record for this sale.")]

    customer_name = str(customer.get("Name", "") or "")
    text = build_payment_reminder_text(customer_name, due_amount, due_sales)

    if _opted_in(customer, "Notify_Email"):
        to_email = str(customer.get("Email", "") or "").strip()
        if to_email:
            if is_email_configured():
                ok, msg = send_email_gated(
                    feature_id="customer_notifications",
                    to_email=to_email,
                    subject=f"Payment reminder — balance {_money(due_amount)} due",
                    body_text=text,
                )
                results.append(("email", ok, msg))
            else:
                results.append(("email", False,
                                "SMTP not configured — set it up in Settings → Notifications."))
        else:
            results.append(("email", False, "Customer has no email address on file."))

    if _opted_in(customer, "Notify_WhatsApp"):
        phone = str(customer.get("Phone", "") or customer.get("Contact", "") or "").strip()
        if phone:
            ok, msg = send_whatsapp_gated(
                feature_id="whatsapp_invoice",
                to_phone=phone,
                message=text,
            )
            results.append(("whatsapp", ok, msg))
        else:
            results.append(("whatsapp", False, "Customer has no phone number on file."))

    if not results:
        results.append(("reminder", False,
                        f"{customer_name or 'This customer'} has not opted in to "
                        "Email/WhatsApp notifications (edit the customer to enable)."))
    return results


# ── high-level event hooks ────────────────────────────────────────────────
def _opted_in(record: Optional[dict], column: str) -> bool:
    if not record:
        return False
    return str(record.get(column, "")).strip().lower() in ("yes", "true", "1")


def notify_after_sale(customer: Optional[dict], sale: dict) -> list:
    """Send post-sale notifications per settings toggles and the customer's
    opt-in flags. Returns a list of ``(channel, ok, message)`` results —
    the caller is responsible for surfacing them (toast) on the UI thread.

    Safe to call from a background thread. No-op when the master switch or
    every channel is disabled / not opted in.
    """
    results = []
    if not notifications_enabled():
        return results
    if customer is None:
        return results
    try:
        from config import get_setting
    except ImportError:
        return results

    customer_name = str(customer.get("Name", "") or "")
    receipt_text = build_sale_receipt_text(sale, customer_name)

    if bool(get_setting("notifications.on_sale_email", True)) and _opted_in(customer, "Notify_Email"):
        to_email = str(customer.get("Email", "") or "").strip()
        if to_email:
            if is_email_configured():
                ok, msg = send_email_gated(
                    feature_id="sale_notifications",
                    to_email=to_email,
                    subject=f"Receipt {sale.get('receipt_no', '')} — {customer_name or 'Sale'}",
                    body_text=receipt_text,
                )
                results.append(("email", ok, msg))
            else:
                results.append(("email", False,
                                "SMTP not configured — set it up in Settings → Notifications."))

    if bool(get_setting("notifications.on_sale_whatsapp", False)) and _opted_in(customer, "Notify_WhatsApp"):
        phone = str(customer.get("Phone", "") or customer.get("Contact", "") or "").strip()
        if phone:
            ok, msg = send_whatsapp_gated(
                feature_id="whatsapp_invoice",
                to_phone=phone,
                message=receipt_text,
            )
            results.append(("whatsapp", ok, msg))

    return results
