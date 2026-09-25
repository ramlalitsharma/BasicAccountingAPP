"""Bank Reconciliation — match a bank statement CSV against recorded
sales/purchases. Enabled by the ``bank_recon`` feature flag.

Workflow: user imports a CSV (columns: date, description, amount — we
auto-detect header names), the page matches each bank line to sales/purchases
within ±3 days and ±0.01 amount, then shows matched and unmatched pairs.
"""
import csv
import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

from database import models
from ui.widgets.tooltip import ToolTip
from utils.formatters import format_currency, safe_float
from config import (FONT_FAMILY, BG_COLOR, CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY,
                    FONT_SIZE_MD, FONT_SIZE_XL, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR)

logger = logging.getLogger(__name__)

_DATE_ALIASES = ("date", "transaction date", "value date", "posting date")
_DESC_ALIASES = ("description", "narration", "details", "remarks", "particulars")
_AMT_ALIASES = ("amount", "debit", "credit", "transaction amount")
_DATE_FMTS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y")
_MATCH_WINDOW_DAYS = 3


def _find_col(headers, aliases):
    low = {h.lower().strip(): h for h in headers}
    for a in aliases:
        for h in low:
            if a == h or a in h:
                return low[h]
    return None


def _parse_date(raw):
    raw = (raw or "").strip()[:10]
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _load_bank_csv(path):
    """Return list of {date, description, amount} dicts from a bank CSV."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    headers = list(rows[0].keys()) if rows else []
    date_col = _find_col(headers, _DATE_ALIASES)
    desc_col = _find_col(headers, _DESC_ALIASES)
    amt_col = _find_col(headers, _AMT_ALIASES)
    if not amt_col:
        raise ValueError("Could not find an Amount column in that CSV.")
    out = []
    for r in rows:
        amt = safe_float(str(r.get(amt_col, "")).replace(",", ""))
        if amt == 0:
            continue
        out.append({
            "date": _parse_date(r.get(date_col, "")) if date_col else "",
            "description": (r.get(desc_col, "") or "").strip() if desc_col else "",
            "amount": amt,
        })
    return out


class BankReconPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._bank_rows = []
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Bank Reconciliation",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        imp = ttk.Button(toolbar, text="Import Bank CSV", command=self._import_csv)
        imp.pack(side=tk.LEFT)
        ToolTip(imp, "Import a bank statement CSV (date, description, amount)")

        run_btn = ttk.Button(toolbar, text="Match Now", style="Success.TButton",
                             command=self._match)
        run_btn.pack(side=tk.LEFT, padx=(8, 0))
        ToolTip(run_btn, "Match bank lines against sales and purchases")

        ttk.Label(toolbar,
                  text=f"Auto-match: same amount within ±{_MATCH_WINDOW_DAYS} days",
                  foreground=TEXT_SECONDARY, font=(FONT_FAMILY, FONT_SIZE_MD)
                  ).pack(side=tk.LEFT, padx=14)

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._summary = ttk.Label(self._container, text="Import a bank statement CSV to begin.",
                                  font=(FONT_FAMILY, FONT_SIZE_MD), foreground=TEXT_SECONDARY)
        self._summary.pack(anchor="w", pady=(0, 6))

        cols = ("bank_date", "bank_desc", "bank_amt", "matched", "app_side", "app_date", "app_amt")
        self.tree = ttk.Treeview(self._container, columns=cols, show="headings", height=16)
        for col, txt, w, anchor in [("bank_date", "Bank Date", 90, "center"),
                                    ("bank_desc", "Bank Description", 240, "w"),
                                    ("bank_amt", "Amount", 100, "e"),
                                    ("matched", "Status", 90, "center"),
                                    ("app_side", "Matched To", 120, "center"),
                                    ("app_date", "App Date", 90, "center"),
                                    ("app_amt", "App Amount", 100, "e")]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=anchor)
        scroll = ttk.Scrollbar(self._container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure("ok", foreground=SUCCESS_COLOR)
        self.tree.tag_configure("unmatched", foreground=DANGER_COLOR)

    def _import_csv(self):
        path = filedialog.askopenfilename(
            title="Select bank statement CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            self._bank_rows = _load_bank_csv(path)
        except (OSError, ValueError, csv.Error) as e:
            messagebox.showerror("Import failed", str(e))
            return
        self._summary.config(text=f"{len(self._bank_rows)} bank lines loaded — click 'Match Now'.")
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _match(self):
        if not self._bank_rows:
            messagebox.showwarning("Match", "Import a bank CSV first.")
            return
        try:
            sales = models.get_sales()
            purchases = models.get_purchases()
        except (FileNotFoundError, OSError):
            messagebox.showerror("Match", "Open a workbook first.")
            return

        candidates = []
        for s in sales:
            candidates.append({"date": str(s.get("Sale_Date") or "")[:10],
                               "amount": safe_float(s.get("Total", 0)), "kind": "Sale",
                               "label": s.get("Receipt_No", "")})
        for p in purchases:
            candidates.append({"date": str(p.get("Purchase_Date") or "")[:10],
                               "amount": safe_float(p.get("Total_Cost", 0)), "kind": "Purchase",
                               "label": str(p.get("ID", ""))})

        used = set()
        matched = unmatched = 0
        for i, br in enumerate(self._bank_rows):
            best = None
            for j, c in enumerate(candidates):
                if j in used:
                    continue
                # Sales appear as positive inflows; purchases often show as
                # negative (money out) on bank statements — match either sign.
                same_sign = abs(c["amount"] - br["amount"]) <= 0.01
                opposite_sign = (c["kind"] == "Purchase" and
                                 abs(c["amount"] + br["amount"]) <= 0.01)
                if not (same_sign or opposite_sign):
                    continue
                if br["date"] and c["date"]:
                    try:
                        d1 = datetime.strptime(br["date"], "%Y-%m-%d")
                        d2 = datetime.strptime(c["date"], "%Y-%m-%d")
                    except ValueError:
                        continue
                    if abs((d1 - d2).days) > _MATCH_WINDOW_DAYS:
                        continue
                best = (j, c)
                break
            if best:
                used.add(best[0])
                matched += 1
                self.tree.insert("", tk.END, values=(
                    br["date"], br["description"], format_currency(br["amount"]),
                    "✔ matched", f"{best[1]['kind']} {best[1]['label']}",
                    best[1]["date"], format_currency(best[1]["amount"])),
                    tags=("ok",))
            else:
                unmatched += 1
                self.tree.insert("", tk.END, values=(
                    br["date"], br["description"], format_currency(br["amount"]),
                    "✗ no match", "—", "", ""), tags=("unmatched",))

        self._summary.config(
            text=f"{matched} matched · {unmatched} unmatched · "
                 f"{len(candidates) - len(used)} app records not on the statement",
            foreground=(SUCCESS_COLOR if unmatched == 0 else WARNING_COLOR))
