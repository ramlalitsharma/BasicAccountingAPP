"""UI smoke test: builds every page + every Settings tab on a hidden Tk root.

Catches constructor/build-time crashes (missing imports, NameError, wrong
widget kwargs, …) without opening visible windows or starting the mainloop.

Run:  python test_ui_smoke.py
"""
import os
import sys
import tempfile
import traceback

os.environ.setdefault("DISPLAY", "")
sys.path.insert(0, os.path.dirname(__file__))

errors = []


def check(ok, msg):
    print(("  OK: " if ok else "  FAIL: ") + msg)
    if not ok:
        errors.append(msg)


def main():
    import tkinter as tk
    from database import models

    tmpdir = tempfile.mkdtemp()
    os.environ["ACCOUNTING_DATA_DIR"] = tmpdir
    wb = models.create_new_workbook()

    print("1. Building main app window (hidden)...")
    try:
        from ui.app import AccountingApp
        app = AccountingApp()  # AccountingApp IS the root window (tk.Tk subclass)
        app.withdraw()
        root = app
        check(True, "AccountingApp constructed")
    except Exception:
        check(False, "AccountingApp constructor:\n" + traceback.format_exc(limit=3))
        sys.exit(1)

    print("\n2. Building every sidebar page...")
    from ui.app import NAV_ITEMS
    for key, _label in NAV_ITEMS:
        try:
            app._navigate(key)
            app.update_idletasks()
            check(True, f"page '{key}' builds")
        except Exception:
            check(False, f"page '{key}' failed:\n{traceback.format_exc(limit=3)}")

    print("\n3. Building every Settings tab...")
    try:
        from ui.pages.settings import SettingsPage
        sp = None
        for w in app.winfo_children():
            w.update_idletasks()
        # find the settings page instance created by _navigate
        sp = app._pages.get("settings")
        if sp is None:
            check(False, "settings page instance not found")
        else:
            nb = sp._notebook
            tabs = [nb.tab(i, "text").strip() for i in range(nb.index("end"))]
            expected = ["General", "Business", "Vertical", "Features", "Tax",
                        "Notifications", "Users", "Audit Log", "Company",
                        "Backup", "License", "Updates"]
            for t in expected:
                check(any(t in x for x in tabs), f"settings tab '{t}' present")
            for t in tabs:
                check("failed to load" not in t.lower()
                      and "error" not in t.lower() or t in expected,
                      f"settings tab '{t}' built without error placeholder")
    except Exception:
        check(False, "settings tab enumeration failed:\n" + traceback.format_exc(limit=3))

    print("\n4. Widget sanity on key pages...")
    try:
        sales = app._pages.get("sales")
        check(sales is not None and hasattr(sales, "_maybe_notify_sale")
              and hasattr(sales, "_invoice_pdf") and hasattr(sales, "_email_invoice")
              and hasattr(sales, "_send_reminder"),
              "Sales page has notify/PDF/email/reminder actions")
        customers = app._pages.get("customers")
        check(customers is not None and hasattr(customers, "_show_statement"),
              "Customers page has account statement")
        dash = app._pages.get("dashboard")
        check(dash is not None and hasattr(dash, "_show_expiring_items")
              and hasattr(dash, "_show_pending_customers"),
              "Dashboard has expiry + pending modals")
    except Exception:
        check(False, "widget sanity failed:\n" + traceback.format_exc(limit=3))

    try:
        os.remove(wb)
    except OSError:
        pass
    app.destroy()

    print("\n" + "=" * 40)
    if errors:
        print(f"FAILED: {len(errors)} problems")
        sys.exit(1)
    print("ALL UI SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
