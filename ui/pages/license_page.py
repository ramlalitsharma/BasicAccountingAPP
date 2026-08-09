"""License tab UI for the Settings page.

Replaces the legacy inline ``_license_tab`` in ``settings.py``. Built around
the new :class:`utils.license.LicenseManager` (RSA-signed tokens, DPAPI
storage, machine binding, heartbeat).

Public entrypoint: :func:`build_license_tab(notebook, app_ctx)` — appends a
"License" tab to ``notebook`` and returns the frame so callers can rebuild it.

Imports are kept lazy/defensive so that a build error in this module cannot
crash the whole Settings dialog (``settings.py`` already wraps tab builders
in try/except).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional

from config import (
    FONT_FAMILY, FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    CARD_BG, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR, ACCENT_COLOR,
    get_color,
)
from utils.license import license_mgr, HEARTBEAT_INTERVAL_DAYS, HEARTBEAT_GRACE

_TIER_PRICING = {
    "free":      "Free 14-day trial",
    "basic":     "Basic \u20B91,500/mo",
    "pro":       "Professional \u20B93,500/mo",
    "enterprise": "Enterprise \u20B98,500/mo",
}

_FEATURE_DISPLAY = [
    ("whatsapp_invoice",  "WhatsApp Invoice"),
    ("cloud_backup",       "Cloud Backup"),
    ("email_invoicing",    "Email Invoicing"),
    ("advanced_reports",   "Advanced Reports"),
    ("multi_company",     "Multi-Company"),
]


def _tier_color(tier: str) -> str:
    if tier == "free":
        return TEXT_MUTED
    if tier == "enterprise":
        return ACCENT_COLOR
    return SUCCESS_COLOR


def build_license_tab(notebook: ttk.Notebook, app_ctx: Any) -> ttk.Frame:
    """Append the License tab to *notebook* and return the frame.

    ``app_ctx`` must expose ``show_modal(title,w,h)`` / ``close_modal()`` and
    a ``toast`` widget — typically the :class:`AccountingApp` toplevel.
    """
    frame = ttk.Frame(notebook, padding=20)
    notebook.add(frame, text="  License  ")

    # Header
    ttk.Label(frame, text="License",
              font=(FONT_FAMILY, 14, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

    row = 1

    # ── Current plan ─────────────────────────────────────────────────────
    ttk.Label(frame, text="Current Plan:",
              font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
        row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    ttk.Label(frame, text=f"  {license_mgr.tier_name}  ",
              font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
              foreground=_tier_color(license_mgr.tier)).grid(
        row=row, column=1, sticky="w", pady=4)
    row += 1

    if license_mgr.licensee and not license_mgr.is_free:
        ttk.Label(frame, text="Licensed To:",
                  font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
            row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        ttk.Label(frame, text=license_mgr.licensee,
                  font=(FONT_FAMILY, FONT_SIZE_MD)).grid(
            row=row, column=1, sticky="w", pady=4)
        row += 1

    if license_mgr.expires_date:
        ttk.Label(frame, text="Expires:",
                  font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
            row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        days = license_mgr.days_left
        color = SUCCESS_COLOR if days > 7 else (WARNING_COLOR if days > 0 else DANGER_COLOR)
        ttk.Label(frame,
                  text=f"{license_mgr.expires_date}  ({days} day{'s' if days != 1 else ''} left)",
                  font=(FONT_FAMILY, FONT_SIZE_MD),
                  foreground=color).grid(
            row=row, column=1, sticky="w", pady=4)
        row += 1

    ttk.Label(frame, text="Stock Limit:",
              font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
        row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    ttk.Label(frame, text=f"{license_mgr.max_stock_items:,}",
              font=(FONT_FAMILY, FONT_SIZE_MD)).grid(
        row=row, column=1, sticky="w", pady=4)
    row += 1

    if not license_mgr.is_free:
        ttk.Label(frame, text="Heartbeat:",
                  font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
            row=row, column=0, sticky="w", pady=4, padx=(0, 10))
        hb = license_mgr.heartbeat_status
        hb_color = SUCCESS_COLOR if hb == "ok" else (
            WARNING_COLOR if hb in ("overdue", "never", "unknown") else DANGER_COLOR)
        last = license_mgr.last_heartbeat or "never"
        ttk.Label(frame,
                  text=f"{hb}  (last {last}; k={HEARTBEAT_INTERVAL_DAYS}d, grace={HEARTBEAT_GRACE}x)",
                  font=(FONT_FAMILY, FONT_SIZE_MD),
                  foreground=hb_color).grid(
            row=row, column=1, sticky="w", pady=4)
        row += 1

    row += 1  # spacer
    ttk.Separator(frame, orient="horizontal").grid(
        row=row, column=0, columnspan=3, sticky="ew", pady=10)
    row += 1

    # ── Feature list ─────────────────────────────────────────────────────
    features_text = ", ".join(
        label for fid, label in _FEATURE_DISPLAY if license_mgr.has_feature(fid)
    ) or "None"
    ttk.Label(frame, text="Included features:",
              font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 2))
    row += 1
    ttk.Label(frame, text=features_text,
              font=(FONT_FAMILY, FONT_SIZE_MD),
              foreground=TEXT_MUTED,
              wraplength=520, justify="left").grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(0, 10))
    row += 1

    # ── Action buttons ───────────────────────────────────────────────────
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
    row += 1

    if license_mgr.is_free:
        ttk.Button(btn_frame, text="Activate License",
                   command=lambda: _show_activate_dialog(app_ctx, frame)
                   ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(btn_frame, text="Need a license? Contact sales to get a token.",
                  font=(FONT_FAMILY, FONT_SIZE_MD),
                  foreground=TEXT_MUTED).pack(side=tk.LEFT, padx=10)
    else:
        ttk.Button(btn_frame, text="Refresh Heartbeat",
                   command=lambda: _do_heartbeat(app_ctx)
                   ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Deactivate",
                   command=lambda: _do_deactivate(app_ctx, frame)
                   ).pack(side=tk.LEFT, padx=(0, 6))

    # ── Pricing hint ────────────────────────────────────────────────────
    row += 1
    ttk.Label(frame, text="Plans:",
              font=(FONT_FAMILY, FONT_SIZE_MD, "bold")).grid(
        row=row, column=0, columnspan=3, sticky="w", pady=(12, 2))
    row += 1
    for tier_key, label in _TIER_PRICING.items():
        mark = "•" if tier_key == license_mgr.tier else " "
        ttk.Label(frame, text=f"  {mark}  {label}",
                  font=(FONT_FAMILY, FONT_SIZE_MD),
                  foreground=TEXT_SECONDARY).grid(
            row=row, column=0, columnspan=3, sticky="w")
        row += 1

    return frame


def _show_activate_dialog(app_ctx: Any, frame: ttk.Frame) -> None:
    body = app_ctx.show_modal("Activate License", 560, 320)
    if body is None:
        return

    ttk.Label(body, text="Paste the license token you received from the admin dashboard.",
              font=(FONT_FAMILY, FONT_SIZE_MD),
              background=CARD_BG).pack(anchor="w", pady=(10, 10))

    text_widget = tk.Text(body, height=8, width=64,
                          font=("Consolas", 9), wrap="none")
    text_widget.pack(fill=tk.X, pady=(0, 10), padx=10)

    hint = tk.Label(body, text="The token starts with 'eyJ' (base64) or '{' (JSON).",
                    font=(FONT_FAMILY, 9),
                    foreground=TEXT_MUTED, background=CARD_BG)
    hint.pack(anchor="w", padx=10)

    def do_activate():
        raw = text_widget.get("1.0", "end-1c").strip()
        if not raw:
            messagebox.showwarning("Empty", "Please paste a license token first.")
            return
        try:
            ok, msg = license_mgr.activate(raw)
        except Exception as exc:
            ok, msg = False, f"Unexpected error: {exc}"
        if ok:
            try:
                app_ctx.close_modal()
            except Exception:
                pass
            messagebox.showinfo("Activated", msg)
            try:
                app_ctx.toast.show("License activated", "success", 3000)
            except Exception:
                pass
            _rebuild_after_change(app_ctx, frame)
        else:
            messagebox.showerror("Activation Failed", msg)

    btn_bar = tk.Frame(body, background=CARD_BG)
    btn_bar.pack(fill=tk.X, pady=(10, 0), padx=10)
    ttk.Button(btn_bar, text="Activate", command=do_activate).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(btn_bar, text="Cancel",
               command=lambda: app_ctx.close_modal()).pack(side=tk.LEFT)


def _do_heartbeat(app_ctx: Any) -> None:
    try:
        ok, msg = license_mgr.send_heartbeat_now()
        if ok:
            app_ctx.toast.show(msg, "success", 4000)
        else:
            app_ctx.toast.show(msg, "warning", 4000)
    except Exception as exc:
        messagebox.showerror("Heartbeat", f"Error: {exc}")


def _do_deactivate(app_ctx: Any, frame: ttk.Frame) -> None:
    if not messagebox.askyesno(
            "Deactivate License",
            "This will reset the app to Free Trial mode.\n\nContinue?"):
        return
    try:
        license_mgr.deactivate()
        app_ctx.toast.show("License deactivated", "info", 3000)
    except Exception as exc:
        messagebox.showerror("Deactivate", f"Error: {exc}")
        return
    _rebuild_after_change(app_ctx, frame)


def _rebuild_after_change(app_ctx: Any, frame: ttk.Frame) -> None:
    """Remove and re-add the License tab on its parent notebook."""
    try:
        notebook = frame.master
        for i in range(notebook.index("end")):
            if notebook.tab(i, "text") == "  License  ":
                notebook.forget(i)
                break
        build_license_tab(notebook, app_ctx)
    except Exception:
        pass
