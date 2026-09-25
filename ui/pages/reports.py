import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from database import models
from ui.widgets.tooltip import ToolTip
from utils.formatters import format_currency, safe_float
from utils.export import export_to_csv
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class ReportsPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Reports",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        # Tab navigation
        tab_frame = ttk.Frame(self)
        tab_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.tab_var = tk.StringVar(value="sales")
        tabs = [("Sales Report", "sales"), ("Purchases Report", "purchases"),
                ("Combined Report", "combined"), ("P&L Summary", "pnl"),
                ("Tax Summary", "tax"), ("Top Items", "top")]
        for txt, val in tabs:
            rb = ttk.Radiobutton(tab_frame, text=txt, variable=self.tab_var,
                                  value=val, command=self._load)
            rb.pack(side=tk.LEFT, padx=(0, 15))

        # Controls
        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.view_var = tk.StringVar(value="daily")
        for txt, val in [("Daily", "daily"), ("Monthly", "monthly"),
                         ("Yearly", "yearly")]:
            rb = ttk.Radiobutton(controls, text=txt, variable=self.view_var,
                                  value=val, command=self._load)
            rb.pack(side=tk.LEFT, padx=(0, 15))

        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(controls, textvariable=self.date_var,
                                        width=14, state="readonly")
        self.date_combo.pack(side=tk.LEFT, padx=(0, 10))

        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(controls, textvariable=self.year_var,
                                        width=8, state="readonly")
        self.year_combo.pack(side=tk.LEFT, padx=(0, 10))

        self.month_var = tk.StringVar()
        months = [("January", 1), ("February", 2), ("March", 3),
                  ("April", 4), ("May", 5), ("June", 6),
                  ("July", 7), ("August", 8), ("September", 9),
                  ("October", 10), ("November", 11), ("December", 12)]
        self.month_map = {name: num for name, num in months}
        self.month_combo = ttk.Combobox(controls, textvariable=self.month_var,
                                         width=12, state="readonly")
        self.month_combo["values"] = [m[0] for m in months]
        self.month_combo.pack(side=tk.LEFT, padx=(0, 10))

        load_btn = ttk.Button(controls, text="Load", command=self._load)
        load_btn.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(load_btn, "Load report data")

        export_btn = ttk.Button(controls, text="Export CSV",
                                command=self._export)
        export_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(export_btn, "Export report to CSV file")

        pdf_btn = ttk.Button(controls, text="Export PDF",
                             command=self._export_pdf)
        pdf_btn.pack(side=tk.LEFT)
        ToolTip(pdf_btn, "Export report to PDF file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Summary section
        self.summary_frame = ttk.Frame(self._container)
        self.summary_frame.pack(fill=tk.X)

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDCCA",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No report data",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Select a tab and click 'Load' to generate a report.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        self._tree_container = tk.Frame(self._container, bg=BG_COLOR)
        self._tree_container.pack(fill=tk.BOTH, expand=True)

        # Tree table
        cols = ["Item", "Category", "Qty", "Price", "Total", "Status", "Paid", "Date"]
        self.tree = ttk.Treeview(self._tree_container, columns=cols, show="headings", height=14)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.column("Item", width=180, anchor="w")

        scroll = ttk.Scrollbar(self._tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._init_controls()

    def _init_controls(self):
        now = datetime.now()
        current_year = now.year
        years = [str(y) for y in range(current_year - 3, current_year + 2)]
        self.year_combo["values"] = years

        days = [f"{now.year}-{now.month:02d}-{d:02d}" for d in range(1, 32)]
        self.date_combo["values"] = days
        self.date_var.set(f"{now.year}-{now.month:02d}-{now.day:02d}")

        self.year_var.set(str(now.year))
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        self.month_var.set(months[now.month - 1])

        self.date_combo.pack()
        self.year_combo.pack_forget()
        self.month_combo.pack_forget()
        self._load()

    def _safe_get_sales(self, **kw):
        try:
            return models.get_sales(**kw)
        except FileNotFoundError:
            return []

    def _safe_get_daily_sales(self, date_str):
        try:
            return models.get_daily_sales(date_str)
        except FileNotFoundError:
            return {"total": 0, "total_paid": 0, "total_unpaid": 0, "extra_income": 0}

    def _safe_get_purchases(self):
        try:
            return models.get_purchases()
        except FileNotFoundError:
            return []

    def _safe_get_monthly_report(self, year, month):
        try:
            return models.get_monthly_report(year, month)
        except FileNotFoundError:
            return {"total_revenue": 0, "total_profit": 0, "total_paid": 0, "extra_income": 0, "net_income": 0, "items": []}

    def _safe_get_yearly_report(self, year):
        try:
            return models.get_yearly_report(year)
        except FileNotFoundError:
            return []

    def _safe_get_stock_items(self):
        try:
            return models.get_stock_items()
        except FileNotFoundError:
            return []

    def _safe_get_suppliers(self):
        try:
            return models.get_suppliers()
        except FileNotFoundError:
            return []

    # ---------- new tab loaders (P&L / Tax / Top Items) ----------

    def _pnl_rows(self, year):
        """Monthly P&L rows for a year: [Month, Revenue, COGS, Gross Profit,
        Extra Income, Net Profit] + a TOTAL row. Returns list of lists."""
        data = self._safe_get_yearly_report(year)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        rows = []
        t_rev = t_cogs = t_extra = 0.0
        for r in data:
            rev = safe_float(r.get("total_revenue", 0))
            profit = safe_float(r.get("total_profit", 0))
            cogs = round(rev - profit, 2)
            extra = safe_float(r.get("extra_income", 0))
            net = round(profit + extra, 2)
            rows.append([months[int(r["month"]) - 1], format_currency(rev),
                         format_currency(cogs), format_currency(profit),
                         format_currency(extra), format_currency(net)])
            t_rev += rev
            t_cogs += cogs
            t_extra += extra
        rows.append(["TOTAL", format_currency(t_rev), format_currency(t_cogs),
                     format_currency(round(t_rev - t_cogs, 2)),
                     format_currency(t_extra),
                     format_currency(round(t_rev - t_cogs + t_extra, 2))])
        return rows

    def _load_pnl_data(self):
        year = self._get_year()
        if year is None:
            return
        cols = ["Month", "Revenue", "COGS", "Gross Profit", "Extra Income", "Net Profit"]
        self._set_tree_columns(cols, first_wide=True)
        rows = self._pnl_rows(year)
        for i, row in enumerate(rows):
            tag = "total" if i == len(rows) - 1 else ""
            self.tree.insert("", tk.END, values=row, tags=(tag,))
        self.tree.tag_configure("total", background="#EFF6FF")
        ttk.Label(self.summary_frame,
                  text=f"Profit & Loss — {year}").pack(side=tk.LEFT, padx=(0, 15))
        if rows:
            ttk.Label(self.summary_frame,
                      text=f"Net Profit (Year): {rows[-1][-1]}").pack(side=tk.LEFT, padx=(0, 10))

    def _tax_rows(self, year):
        """Monthly tax estimate rows: [Month, Sales, Taxable, <tax components…>, Total Tax]."""
        from utils.tax import get_tax_engine, is_tax_enabled, get_default_rate
        from utils.settings_helper import get_current_country
        engine = get_tax_engine()
        rate = safe_float(get_default_rate())
        country = get_current_country()
        sales = [s for s in self._safe_get_sales()
                 if (s.get("Sale_Date") or "").startswith(str(year))]
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        per_month = {}
        for s in sales:
            sd = str(s.get("Sale_Date") or "")
            m = sd[5:7]
            if m not in per_month:
                per_month[m] = {"count": 0, "taxable": 0.0}
            per_month[m]["count"] += 1
            per_month[m]["taxable"] += safe_float(s.get("Total", 0))

        enabled = is_tax_enabled() and rate > 0
        if enabled:
            sample = engine.compute_tax_breakdown(subtotal=100.0, rate_percent=rate)
            comp_labels = [c["label"] for c in sample["components"]]
        else:
            comp_labels = []

        cols = ["Month", "Sales", "Taxable Sales"] + comp_labels + ["Total Tax"]
        rows = []
        totals = {"count": 0, "taxable": 0.0, "comp": {l: 0.0 for l in comp_labels}, "tax": 0.0}
        for m in sorted(per_month):
            info = per_month[m]
            taxable = round(info["taxable"], 2)
            if enabled and taxable > 0:
                bd = engine.compute_tax_breakdown(subtotal=taxable, rate_percent=rate)
                comp_vals = [round(c["amount"], 2) for c in bd["components"]]
                tax_total = round(bd["tax_amount"], 2)
            else:
                comp_vals = [0.0 for _ in comp_labels]
                tax_total = 0.0
            rows.append([months[int(m) - 1], info["count"], format_currency(taxable)]
                        + [format_currency(v) for v in comp_vals]
                        + [format_currency(tax_total)])
            totals["count"] += info["count"]
            totals["taxable"] += taxable
            totals["tax"] += tax_total
            for l, v in zip(comp_labels, comp_vals):
                totals["comp"][l] += v
        if rows:
            rows.append(["TOTAL", totals["count"], format_currency(round(totals["taxable"], 2))]
                        + [format_currency(round(v, 2)) for v in totals["comp"].values()]
                        + [format_currency(round(totals["tax"], 2))])
        return cols, rows, rate, country, enabled

    def _load_tax_data(self):
        year = self._get_year()
        if year is None:
            return
        cols, rows, rate, country, enabled = self._tax_rows(year)
        self._set_tree_columns(cols, first_wide=True)
        for i, row in enumerate(rows):
            tag = "total" if i == len(rows) - 1 else ""
            self.tree.insert("", tk.END, values=row, tags=(tag,))
        self.tree.tag_configure("total", background="#EFF6FF")
        if not enabled:
            ttk.Label(self.summary_frame,
                      text="Tax is disabled or rate is 0 — enable it in Settings → Tax.").pack(side=tk.LEFT)
        else:
            ttk.Label(self.summary_frame,
                      text=f"Estimated {country} tax on sales @ {rate:g}% — {year}").pack(side=tk.LEFT, padx=(0, 15))
            if rows:
                ttk.Label(self.summary_frame,
                          text=f"Total Tax (Year): {rows[-1][-1]}").pack(side=tk.LEFT, padx=(0, 10))

    def _top_items_rows(self):
        """Item performance rows: [Rank, Item, Category, Qty, Revenue, Profit, % Rev]."""
        sales = self._safe_get_sales()
        stock = {r["ID"]: r for r in self._safe_get_stock_items()}
        agg = {}
        for s in sales:
            item = stock.get(s.get("Stock_ID"), {})
            name = item.get("Item_Name", "Unknown")
            if name not in agg:
                agg[name] = {"item": name, "category": item.get("Category", ""),
                             "qty": 0.0, "revenue": 0.0, "cost": 0.0}
            qty = safe_float(s.get("Quantity_Sold", 0))
            agg[name]["qty"] += qty
            agg[name]["revenue"] += safe_float(s.get("Total", 0))
            agg[name]["cost"] += qty * safe_float(item.get("Purchase_Price", 0))
        total_rev = sum(a["revenue"] for a in agg.values())
        rows = []
        for rank, a in enumerate(sorted(agg.values(), key=lambda x: x["revenue"], reverse=True), 1):
            profit = round(a["revenue"] - a["cost"], 2)
            pct = (a["revenue"] / total_rev * 100) if total_rev > 0 else 0
            rows.append([rank, a["item"], a["category"], int(a["qty"]),
                         format_currency(a["revenue"]), format_currency(profit),
                         f"{pct:.1f}%"])
        return rows

    def _load_top_items(self):
        cols = ["#", "Item", "Category", "Qty Sold", "Revenue", "Profit", "% of Revenue"]
        self._set_tree_columns(cols, first_wide=True)
        self.tree.column("#", width=40, anchor="center")
        rows = self._top_items_rows()
        for row in rows:
            self.tree.insert("", tk.END, values=row)
        if rows:
            ttk.Label(self.summary_frame,
                      text=f"Top seller: {rows[0][1]} ({rows[0][4]})").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame,
                      text=f"{len(rows)} items sold (all time)").pack(side=tk.LEFT)

    def _get_year(self):
        try:
            return int(self.year_var.get().strip())
        except (ValueError, TypeError):
            messagebox.showerror("Input Error", "Please enter a valid year.")
            return None

    def _set_tree_columns(self, cols, first_wide=False):
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor="center")
        if first_wide and cols:
            self.tree.column(cols[0], width=80, anchor="w")

    def _load_sales_data(self):
        view = self.view_var.get()
        if view == "daily":
            date_str = self.date_var.get()
            data = self._safe_get_sales(from_date=date_str, to_date=date_str)
            ds = self._safe_get_daily_sales(date_str)
            total_rev = sum(safe_float(r.get("Total", 0)) for r in data)
            total_qty = sum(safe_float(r.get("Quantity_Sold", 0)) for r in data)
            total_paid = ds.get("total_paid", 0)
            total_unpaid = ds.get("total_unpaid", 0)
            extra = ds.get("extra_income", 0)
            ttk.Label(self.summary_frame, text=f"Date: {date_str}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Sales: {len(data)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Qty: {total_qty}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Revenue: {format_currency(total_rev)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Paid: {format_currency(total_paid)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Unpaid: {format_currency(total_unpaid)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Extra: {format_currency(extra)}").pack(side=tk.LEFT, padx=(0, 15))
            for r in data:
                self.tree.insert("", tk.END, values=(
                    r.get("item_name", ""), r.get("category", ""),
                    r.get("Quantity_Sold", 0), format_currency(r.get("Price", 0)),
                    format_currency(r.get("Total", 0)),
                    (r.get("Payment_Status") or "paid").capitalize(),
                    format_currency(r.get("Paid_Amount", 0)),
                    (r.get("Sale_Date") or "")[:10]))
        elif view == "monthly":
            try:
                year = int(self.year_var.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid year.")
                return
            month_num = self.month_map.get(self.month_var.get())
            report = self._safe_get_monthly_report(year, month_num)
            items = report.get("items", [])
            ttk.Label(self.summary_frame, text=f"{self.month_var.get()} {year}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Revenue: {format_currency(report.get('total_revenue', 0))}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Profit: {format_currency(report.get('total_profit', 0))}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Paid: {format_currency(report.get('total_paid', 0))}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Extra: {format_currency(report.get('extra_income', 0))}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Net: {format_currency(report.get('net_income', 0))}").pack(side=tk.LEFT, padx=(0, 15))
            for r in items:
                qty = r["qty_sold"] or 0
                cost = qty * (r["purchase_price"] or 0)
                rev = r["total_revenue"] or 0
                self.tree.insert("", tk.END, values=(
                    r["item_name"], r["category"], qty, format_currency(r["price"]),
                    format_currency(rev), "N/A", format_currency(rev - cost), ""))
        else:
            try:
                year = int(self.year_var.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid year.")
                return
            data = self._safe_get_yearly_report(year)
            total_rev = sum(safe_float(r.get("total_revenue", 0)) for r in data)
            total_profit = sum(safe_float(r.get("total_profit", 0)) for r in data)
            total_paid = sum(safe_float(r.get("total_paid", 0)) for r in data)
            total_extra = sum(safe_float(r.get("extra_income", 0)) for r in data)
            ttk.Label(self.summary_frame, text=f"Year: {year}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Revenue: {format_currency(total_rev)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Profit: {format_currency(total_profit)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Paid: {format_currency(total_paid)}").pack(side=tk.LEFT, padx=(0, 15))
            ttk.Label(self.summary_frame, text=f"Extra: {format_currency(total_extra)}").pack(side=tk.LEFT, padx=(0, 15))
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            self.tree["columns"] = ["Month", "Sales", "Qty", "Revenue", "Paid", "Unpaid", "Extra", "Profit"]
            self.tree.column("Month", width=80)
            for c in self.tree["columns"]:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=100, anchor="center")
            for r in data:
                m = int(r["month"]) - 1
                self.tree.insert("", tk.END, values=(
                    months[m], r["sale_count"], r["total_qty"],
                    format_currency(r["total_revenue"] or 0),
                    format_currency(r["total_paid"] or 0),
                    format_currency(r["total_unpaid"] or 0),
                    format_currency(r["extra_income"] or 0),
                    format_currency(r["total_profit"] or 0)))
            return

    def _load_purchases_data(self):
        view = self.view_var.get()
        stock = {r["ID"]: r for r in self._safe_get_stock_items()}
        purchases = self._safe_get_purchases()

        if view == "daily":
            date_str = self.date_var.get()
            data = [p for p in purchases if (p.get("Purchase_Date") or "")[:10] == date_str]
            ttk.Label(self.summary_frame, text=f"Date: {date_str}").pack(side=tk.LEFT, padx=(0, 15))
        elif view == "monthly":
            try:
                year = int(self.year_var.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid year.")
                return
            month_num = self.month_map.get(self.month_var.get())
            ym = f"{year}-{month_num:02d}"
            data = [p for p in purchases if (p.get("Purchase_Date") or "").startswith(ym)]
            ttk.Label(self.summary_frame, text=f"{self.month_var.get()} {year}").pack(side=tk.LEFT, padx=(0, 15))
        else:
            try:
                year = int(self.year_var.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid year.")
                return
            data = [p for p in purchases if (p.get("Purchase_Date") or "").startswith(str(year))]
            ttk.Label(self.summary_frame, text=f"Year: {year}").pack(side=tk.LEFT, padx=(0, 15))

        total_cost = sum(safe_float(p.get("Total_Cost", 0)) for p in data)
        total_qty = sum(safe_float(p.get("Quantity", 0)) for p in data)
        ttk.Label(self.summary_frame, text=f"Purchases: {len(data)}").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(self.summary_frame, text=f"Qty: {total_qty}").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(self.summary_frame, text=f"Total Cost: {format_currency(total_cost)}").pack(side=tk.LEFT, padx=(0, 15))

        self.tree["columns"] = ["Item", "Supplier", "Qty", "Unit Cost", "Total Cost", "Date"]
        for c in self.tree["columns"]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor="center")
        self.tree.column("Item", width=180, anchor="w")

        for p in data:
            item = stock.get(p.get("Stock_ID"), {})
            self.tree.insert("", tk.END, values=(
                item.get("Item_Name", "Unknown"),
                p.get("supplier_name", ""),
                p.get("Quantity", 0),
                format_currency(p.get("Cost_Price", 0)),
                format_currency(p.get("Total_Cost", 0)),
                (p.get("Purchase_Date") or "")[:10]))

    def _load_combined_data(self):
        view = self.view_var.get()
        sales_data = []
        purchase_data = []

        if view == "daily":
            date_str = self.date_var.get()
            sales_data = self._safe_get_sales(from_date=date_str, to_date=date_str)
            purchases = self._safe_get_purchases()
            purchase_data = [p for p in purchases if (p.get("Purchase_Date") or "")[:10] == date_str]
            ttk.Label(self.summary_frame, text=f"Date: {date_str}").pack(side=tk.LEFT, padx=(0, 15))
        elif view == "monthly":
            try:
                year = int(self.year_var.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid year.")
                return
            month_num = self.month_map.get(self.month_var.get())
            sales_data = [s for s in self._safe_get_sales() if (s.get("Sale_Date") or "").startswith(f"{year}-{month_num:02d}")]
            purchases = self._safe_get_purchases()
            purchase_data = [p for p in purchases if (p.get("Purchase_Date") or "").startswith(f"{year}-{month_num:02d}")]
            ttk.Label(self.summary_frame, text=f"{self.month_var.get()} {year}").pack(side=tk.LEFT, padx=(0, 15))
        else:
            try:
                year = int(self.year_var.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid year.")
                return
            sales_data = [s for s in self._safe_get_sales() if (s.get("Sale_Date") or "").startswith(str(year))]
            purchases = self._safe_get_purchases()
            purchase_data = [p for p in purchases if (p.get("Purchase_Date") or "").startswith(str(year))]
            ttk.Label(self.summary_frame, text=f"Year: {year}").pack(side=tk.LEFT, padx=(0, 15))

        stock = {r["ID"]: r for r in self._safe_get_stock_items()}
        suppliers = {s["ID"]: s["Name"] for s in self._safe_get_suppliers()}

        total_sales_rev = sum(safe_float(s.get("Total", 0)) for s in sales_data)
        total_sales_qty = sum(safe_float(s.get("Quantity_Sold", 0)) for s in sales_data)
        total_purchase_cost = sum(safe_float(p.get("Total_Cost", 0)) for p in purchase_data)
        total_purchase_qty = sum(safe_float(p.get("Quantity", 0)) for p in purchase_data)

        ttk.Label(self.summary_frame, text=f"Sales: {len(sales_data)}").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(self.summary_frame, text=f"Sales Rev: {format_currency(total_sales_rev)}").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(self.summary_frame, text=f"Purchases: {len(purchase_data)}").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(self.summary_frame, text=f"Purchase Cost: {format_currency(total_purchase_cost)}").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(self.summary_frame, text=f"Net Profit: {format_currency(total_sales_rev - total_purchase_cost)}").pack(side=tk.LEFT, padx=(0, 10))

        self.tree["columns"] = ["Type", "Item", "Qty", "Rate", "Amount", "Party", "Date"]
        for c in self.tree["columns"]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")
        self.tree.column("Item", width=160, anchor="w")
        self.tree.column("Party", width=130, anchor="w")

        for s in sales_data:
            item = stock.get(s.get("Stock_ID"), {})
            self.tree.insert("", tk.END, values=(
                "SALE", item.get("Item_Name", ""),
                s.get("Quantity_Sold", 0), format_currency(s.get("Price", 0)),
                format_currency(s.get("Total", 0)),
                s.get("customer_name", "Walk-in"),
                (s.get("Sale_Date") or "")[:10]))

        for p in purchase_data:
            item = stock.get(p.get("Stock_ID"), {})
            self.tree.insert("", tk.END, values=(
                "PURCHASE", item.get("Item_Name", ""),
                p.get("Quantity", 0), format_currency(p.get("Cost_Price", 0)),
                format_currency(p.get("Total_Cost", 0)),
                p.get("supplier_name", ""),
                (p.get("Purchase_Date") or "")[:10]))

    def _load(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for w in self.summary_frame.winfo_children():
            w.destroy()

        view = self.view_var.get()
        now = datetime.now()

        if view == "daily":
            self.date_combo.pack(side=tk.LEFT, padx=(0, 10))
            self.year_combo.pack_forget()
            self.month_combo.pack_forget()
        elif view == "monthly":
            self.date_combo.pack_forget()
            self.year_combo.pack(side=tk.LEFT, padx=(0, 10))
            self.month_combo.pack(side=tk.LEFT, padx=(0, 10))
        else:
            self.date_combo.pack_forget()
            self.year_combo.pack(side=tk.LEFT, padx=(0, 10))
            self.month_combo.pack_forget()

        # Reset tree columns to default
        default_cols = ["Item", "Category", "Qty", "Price", "Total", "Status", "Paid", "Date"]
        self.tree["columns"] = default_cols
        for c in default_cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, anchor="center")
        self.tree.column("Item", width=180, anchor="w")

        tab = self.tab_var.get()

        if tab in ("pnl", "tax", "top"):
            # Year-scoped reports — only show the year selector.
            self.date_combo.pack_forget()
            self.month_combo.pack_forget()
            self.year_combo.pack(side=tk.LEFT, padx=(0, 10))
            if tab == "pnl":
                self._load_pnl_data()
            elif tab == "tax":
                self._load_tax_data()
            else:
                self._load_top_items()
            items = self.tree.get_children()
            if not items:
                self._tree_container.pack_forget()
                self._empty_state.pack(fill=tk.BOTH, expand=True)
            else:
                self._empty_state.pack_forget()
                self._tree_container.pack(fill=tk.BOTH, expand=True)
            return

        if tab == "sales":
            self._load_sales_data()
        elif tab == "purchases":
            self._load_purchases_data()
        else:
            self._load_combined_data()

        items = self.tree.get_children()
        if not items:
            self._tree_container.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
        else:
            self._empty_state.pack_forget()
            self._tree_container.pack(fill=tk.BOTH, expand=True)

    def _export(self):
        tab = self.tab_var.get()
        view = self.view_var.get()

        if tab in ("pnl", "tax", "top"):
            year = self._get_year()
            if year is None:
                return
            if tab == "pnl":
                headers = ["Month", "Revenue", "COGS", "Gross Profit", "Extra Income", "Net Profit"]
                export_to_csv(self._pnl_rows(year), headers, f"pnl_{year}.csv")
            elif tab == "tax":
                cols, rows, _rate, _country, _en = self._tax_rows(year)
                export_to_csv(rows, cols, f"tax_summary_{year}.csv")
            else:
                headers = ["Rank", "Item", "Category", "Qty Sold", "Revenue", "Profit", "% of Revenue"]
                export_to_csv(self._top_items_rows(), headers, "top_items.csv")
            return

        if tab == "sales":
            if view == "daily":
                data = self._safe_get_sales(from_date=self.date_var.get(), to_date=self.date_var.get())
                headers = ["Item", "Category", "Qty", "Price", "Total", "Status", "Paid", "Date"]
                rows = [[r.get("item_name"), r.get("category"), r.get("Quantity_Sold"),
                         r.get("Price"), r.get("Total"), (r.get("Payment_Status") or "paid"),
                         r.get("Paid_Amount"), (r.get("Sale_Date") or "")[:10]] for r in data]
                export_to_csv(rows, headers, f"sales_{self.date_var.get()}.csv")
            elif view == "monthly":
                try:
                    year = int(self.year_var.get().strip())
                except (ValueError, TypeError):
                    messagebox.showerror("Input Error", "Please enter a valid year.")
                    return
                month_num = self.month_map.get(self.month_var.get())
                report = self._safe_get_monthly_report(year, month_num)
                items = report.get("items", [])
                headers = ["Item", "Category", "Qty", "Price", "Revenue", "Cost", "Profit"]
                rows = [[r["item_name"], r["category"], r["qty_sold"], r["price"],
                         r["total_revenue"], r["qty_sold"] * r["purchase_price"], r["profit"]]
                        for r in items]
                export_to_csv(rows, headers, f"monthly_{year}_{month_num:02d}.csv")
            else:
                try:
                    year = int(self.year_var.get().strip())
                except (ValueError, TypeError):
                    messagebox.showerror("Input Error", "Please enter a valid year.")
                    return
                data = self._safe_get_yearly_report(year)
                headers = ["Month", "Sales", "Qty", "Revenue", "Paid", "Unpaid", "Extra", "Profit"]
                rows = [[r["month"], r["sale_count"], r["total_qty"], r["total_revenue"],
                         r["total_paid"], r["total_unpaid"], r["extra_income"], r["total_profit"]]
                        for r in data]
                export_to_csv(rows, headers, f"yearly_{self.year_var.get()}.csv")
        elif tab == "purchases":
            data = self._safe_get_purchases()
            stock = {r["ID"]: r for r in self._safe_get_stock_items()}
            headers = ["Item", "Supplier", "Qty", "Unit Cost", "Total Cost", "Date"]
            rows = [[stock.get(p.get("Stock_ID"), {}).get("Item_Name", "Unknown"),
                     p.get("supplier_name", ""), p.get("Quantity", 0),
                     p.get("Cost_Price", 0), p.get("Total_Cost", 0),
                     (p.get("Purchase_Date") or "")[:10]] for p in data]
            export_to_csv(rows, headers, "purchases_export.csv")
        else:
            stock = {r["ID"]: r for r in self._safe_get_stock_items()}
            sales = self._safe_get_sales()
            purchases = self._safe_get_purchases()
            headers = ["Type", "Item", "Qty", "Rate", "Amount", "Party", "Date"]
            rows = []
            for s in sales:
                item = stock.get(s.get("Stock_ID"), {})
                rows.append(["SALE", item.get("Item_Name", ""), s.get("Quantity_Sold", 0),
                             s.get("Price", 0), s.get("Total", 0),
                             s.get("customer_name", "Walk-in"), (s.get("Sale_Date") or "")[:10]])
            for p in purchases:
                item = stock.get(p.get("Stock_ID"), {})
                rows.append(["PURCHASE", item.get("Item_Name", ""), p.get("Quantity", 0),
                             p.get("Cost_Price", 0), p.get("Total_Cost", 0),
                             p.get("supplier_name", ""), (p.get("Purchase_Date") or "")[:10]])
            export_to_csv(rows, headers, "combined_report.csv")

    def _export_pdf(self):
        from tkinter import filedialog
        from utils.pdf_export import export_sales_report, HAVE_REPORTLAB
        from utils.feature_gate import require_feature
        if not require_feature("advanced_reports", parent=self,
                               friendly_name="PDF Report Export"):
            return

        if not HAVE_REPORTLAB:
            messagebox.showwarning(
                "Export Unavailable",
                "PDF export requires ReportLab.\n\n"
                "Install it with: pip install reportlab\n\n"
                "You can use CSV export instead."
            )
            return

        tab = self.tab_var.get()
        view = self.view_var.get()
        report_data = []
        title = "Report"

        if tab in ("pnl", "tax", "top"):
            year = self._get_year()
            if year is None:
                return
            if tab == "pnl":
                title = f"Profit & Loss — {year}"
                headers = ["Month", "Revenue", "COGS", "Gross Profit", "Extra Income", "Net Profit"]
                report_data = [dict(zip(headers, r)) for r in self._pnl_rows(year)]
            elif tab == "tax":
                title = f"Tax Summary — {year}"
                cols, rows, _rate, _country, _en = self._tax_rows(year)
                report_data = [dict(zip(cols, r)) for r in rows]
            else:
                title = "Top Items (All Time)"
                headers = ["#", "Item", "Category", "Qty Sold", "Revenue", "Profit", "% of Revenue"]
                report_data = [dict(zip(headers, r)) for r in self._top_items_rows()]
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"{tab}_{year if tab != 'top' else 'all'}.pdf",
            )
            if not filepath:
                return
            success, msg = export_sales_report(report_data, filepath, title=title)
            if success:
                messagebox.showinfo("Export Successful", msg)
            else:
                messagebox.showerror("Export Failed", msg)
            return

        if tab == "sales":
            title = "Sales Report"
            if view == "daily":
                data = self._safe_get_sales(from_date=self.date_var.get(), to_date=self.date_var.get())
                for r in data:
                    report_data.append({
                        "Item": r.get("item_name", ""),
                        "Category": r.get("category", ""),
                        "Qty": r.get("Quantity_Sold", 0),
                        "Price": r.get("Price", 0),
                        "Total": r.get("Total", 0),
                        "Status": (r.get("Payment_Status") or "paid").capitalize(),
                        "Paid": safe_float(r.get("Paid_Amount", 0)),
                        "Date": (r.get("Sale_Date") or "")[:10],
                    })
            elif view == "monthly":
                try:
                    year = int(self.year_var.get().strip())
                except (ValueError, TypeError):
                    messagebox.showerror("Input Error", "Please enter a valid year.")
                    return
                month_num = self.month_map.get(self.month_var.get())
                report = self._safe_get_monthly_report(year, month_num)
                for r in report.get("items", []):
                    qty = r["qty_sold"] or 0
                    cost = qty * (r["purchase_price"] or 0)
                    report_data.append({
                        "Item": r["item_name"],
                        "Category": r["category"],
                        "Qty": qty,
                        "Price": r["price"],
                        "Revenue": r["total_revenue"],
                        "Cost": cost,
                        "Profit": r["total_revenue"] - cost,
                    })
            else:
                try:
                    year = int(self.year_var.get().strip())
                except (ValueError, TypeError):
                    messagebox.showerror("Input Error", "Please enter a valid year.")
                    return
                data = self._safe_get_yearly_report(year)
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                for r in data:
                    m = int(r["month"]) - 1
                    report_data.append({
                        "Month": months[m],
                        "Sales": r["sale_count"],
                        "Qty": r["total_qty"],
                        "Revenue": r["total_revenue"],
                        "Paid": r["total_paid"],
                        "Unpaid": r["total_unpaid"],
                        "Extra": r["extra_income"],
                        "Profit": r["total_profit"],
                    })
        elif tab == "purchases":
            title = "Purchases Report"
            stock = {r["ID"]: r for r in self._safe_get_stock_items()}
            purchases = self._safe_get_purchases()
            for p in purchases:
                item = stock.get(p.get("Stock_ID"), {})
                report_data.append({
                    "Item": item.get("Item_Name", "Unknown"),
                    "Supplier": p.get("supplier_name", ""),
                    "Qty": p.get("Quantity", 0),
                    "Unit Cost": p.get("Cost_Price", 0),
                    "Total Cost": p.get("Total_Cost", 0),
                    "Date": (p.get("Purchase_Date") or "")[:10],
                })
        else:
            title = "Combined Report"
            stock = {r["ID"]: r for r in self._safe_get_stock_items()}
            sales = self._safe_get_sales()
            purchases = self._safe_get_purchases()
            for s in sales:
                item = stock.get(s.get("Stock_ID"), {})
                report_data.append({
                    "Type": "SALE",
                    "Item": item.get("Item_Name", ""),
                    "Qty": s.get("Quantity_Sold", 0),
                    "Rate": s.get("Price", 0),
                    "Amount": s.get("Total", 0),
                    "Party": s.get("customer_name", "Walk-in"),
                    "Date": (s.get("Sale_Date") or "")[:10],
                })
            for p in purchases:
                item = stock.get(p.get("Stock_ID"), {})
                report_data.append({
                    "Type": "PURCHASE",
                    "Item": item.get("Item_Name", ""),
                    "Qty": p.get("Quantity", 0),
                    "Rate": p.get("Cost_Price", 0),
                    "Amount": p.get("Total_Cost", 0),
                    "Party": p.get("supplier_name", ""),
                    "Date": (p.get("Purchase_Date") or "")[:10],
                })

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{tab}_{view}.pdf",
        )
        if not filepath:
            return

        success, msg = export_sales_report(report_data, filepath, title=title)
        if success:
            messagebox.showinfo("Export Successful", msg)
        else:
            messagebox.showerror("Export Failed", msg)
