"""Centralized feature / limit gate enforcement for the desktop app.

All UI pages should funnel through these helpers so the gating policy lives in
ONE place. Returns True/False (and optionally shows a toast on block) so
pages can either disable controls at build time or check at action time.

Why this module exists:
    Previously, ``is_pro`` and ``has_feature()`` were the only license
    checks, but no UI code actually called them. Adding per-call gates
    means future feature additions can plug in by adding one line in the
    relevant page.

Usage::

    from utils.feature_gate import require_feature, require_stock_slot

    def on_click_email_invoice():
        if not require_feature("email_invoicing", parent=self):
            return
        # ... do the email send ...

    def on_add_stock_item(form_data):
        if not require_stock_slot(parent=self):
            return
        # ... add the item ...
"""
from __future__ import annotations

import logging
import tkinter as tk
from typing import Any, Optional

from utils.license import license_mgr

logger = logging.getLogger(__name__)


# ── internal helpers ──────────────────────────────────────────────────────
def _toast(parent: Any, message: str, kind: str = "warning") -> None:
    """Try to surface a non-blocking toast using whatever app_ctx/Toast
    exists on the parent widget tree; fall back to a silent messagebox."""
    try:
        app = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        toast = getattr(app, "toast", None)
        if toast is not None and hasattr(toast, "show"):
            toast.show(message, kind, 4500)
            return
    except Exception:
        pass
    # Fall back to messagebox if no toast (e.g. in tests).
    try:
        from tkinter import messagebox
        if kind == "error":
            messagebox.showerror("Feature locked", message)
        else:
            messagebox.showwarning("Feature locked", message)
    except Exception:
        logger.info("[feature_gate] %s", message)


# ── public API ────────────────────────────────────────────────────────────
def has_feature(feature_id: str) -> bool:
    """Convenience pass-through; same as ``license_mgr.has_feature()``."""
    return license_mgr.has_feature(feature_id)


def require_feature(feature_id: str, parent: Any = None,
                    friendly_name: Optional[str] = None,
                    silent: bool = False) -> bool:
    """Returns True if the feature is enabled in the current license.

    If False, optionally surfaces a toast explaining the user needs a higher
    tier. Use ``silent=True`` to gate silently (e.g. to grey out a button
    without nagging the user).
    """
    if has_feature(feature_id):
        return True
    if silent:
        return False
    name = friendly_name or feature_id.replace("_", " ").title()
    tier = license_mgr.effective_tier_name
    reason = license_mgr.feature_gate_reason
    msg = (f"'{name}' is available in Basic/Pro/Enterprise.\n"
           f"Current plan: {tier}.\n"
           f"Reason: {reason or 'Free trial'}."
           f"\n\nActivate a license in Settings → License.")
    _toast(parent, msg, "warning")
    return False


def max_stock_items() -> int:
    return license_mgr.max_stock_items


def current_stock_count() -> int:
    """Live count of stock items in the active workbook."""
    try:
        from database import models
        return len(models.get_stock_items() or [])
    except Exception as exc:
        logger.debug("current_stock_count: %s", exc)
        return 0


def can_add_stock_item() -> bool:
    cap = max_stock_items()
    return current_stock_count() < cap


def require_stock_slot(parent: Any = None, silent: bool = False) -> bool:
    cap = max_stock_items()
    cur = current_stock_count()
    if cur < cap:
        return True
    if silent:
        return False
    tier = license_mgr.effective_tier_name
    msg = (f"Stock limit reached: {cur}/{cap} items.\n"
           f"Current plan: {tier}.\n"
           f"Upgrade to Pro/Enterprise to add more stock items.\n\n"
           f"Activate a license in Settings → License.")
    _toast(parent, msg, "warning")
    return False


def require_pro(parent: Any = None, action: str = "perform this action",
                silent: bool = False) -> bool:
    """Returns True if the user has any non-free tier."""
    if license_mgr.is_pro or license_mgr.is_enterprise:
        return True
    if silent:
        return False
    msg = (f"'{action}' requires a Pro/Enterprise license.\n"
           f"Current plan: {license_mgr.effective_tier_name}.\n\n"
           f"Activate a license in Settings → License.")
    _toast(parent, msg, "warning")
    return False


# Convenience: list every gate a UI page might want to check
ALL_GATES = (
    "whatsapp_invoice",
    "cloud_backup",
    "email_invoicing",
    "advanced_reports",
    "multi_company",
    "customer_notifications",
    "purchase_notifications",
    "sale_notifications",
)
