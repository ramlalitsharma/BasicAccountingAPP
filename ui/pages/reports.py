import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from utils.formatters import format_currency
from utils.export import export_to_csv


class ReportsPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Reports",
                           font=("Segoe UI", 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        tab_frame = ttk.Frame(self)
        tab_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.view_var = tk.StringVar(value="daily")
        for txt, val in [("Daily", "daily"), ("Monthly", "monthly"),
                         ("Yearly", "yearly")]:
            rb = ttk.Radiobutton(tab_frame, text=txt, variable=self.view_var,
                                  value=val, command=self._load)
            rb.pack(side=tk.LEFT, padx=(0, 15))

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=20, pady=(0, 10))

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

        export_btn = ttk.Button(controls, text="Export CSV",
                                command=self._export)
        export_btn.pack(side=tk.LEFT)

        self.summary_frame = ttk.Frame(self)
        self.summary_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        cols = ["Item", "Category", "Qty Sold", "Unit Price",
                "Revenue", "Cost", "Profit"]
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.column("Item", width=180, anchor="w")
        self.tree.column("Category", width=120, anchor="w")

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 20))

        self._init_controls()

    def _init_controls(self):
        from datetime import datetime
        now = datetime.now()
        years = [str(y) for y in range(2024, 2031)]
        self.year_combo["values"] = years

        days = []
        for d in range(1, 32):
            days.append(f"{now.year}-{now.month:02d}-{d:02d}")
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

    def _load(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for w in self.summary_frame.winfo_children():
            w.destroy()

        view = self.view_var.get()
        from datetime import datetime
        now = datetime.now()

        if view == "daily":
            self.date_combo.pack(side=tk.LEFT, padx=(0, 10))
            self.year_combo.pack_forget()
            self.month_combo.pack_forget()
            date_str = self.date_var.get()
            data = models.get_sales(from_date=date_str, to_date=date_str)
            total_rev = sum(r["total"] or 0 for r in data)
            total_qty = sum(r["quantity_sold"] or 0 for r in data)
            ttk.Label(self.summary_frame,
                      text=f"Daily Report: {date_str}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Sales: {len(data)}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Qty Sold: {total_qty}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Revenue: {format_currency(total_rev)}").pack(side=tk.LEFT, padx=(0, 20))
            for r in data:
                self.tree.insert("", tk.END, values=(
                    r["item_name"], r["category"], r["quantity_sold"],
                    format_currency(r["price"]), format_currency(r["total"]),
                    "-", "-"))
            return

        if view == "monthly":
            self.date_combo.pack_forget()
            self.year_combo.pack(side=tk.LEFT, padx=(0, 10))
            self.month_combo.pack(side=tk.LEFT, padx=(0, 10))
            year = int(self.year_var.get())
            month_name = self.month_var.get()
            month_num = self.month_map.get(month_name)
            data = models.get_monthly_report(year, month_num)
            total_rev = sum(r["total_revenue"] or 0 for r in data)
            total_cost = sum((r["qty_sold"] or 0) * (r["purchase_price"] or 0) for r in data)
            total_profit = total_rev - total_cost
            ttk.Label(self.summary_frame,
                      text=f"{month_name} {year}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Revenue: {format_currency(total_rev)}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Cost: {format_currency(total_cost)}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Profit: {format_currency(total_profit)}").pack(side=tk.LEFT, padx=(0, 20))
            for r in data:
                qty = r["qty_sold"] or 0
                cost = qty * (r["purchase_price"] or 0)
                self.tree.insert("", tk.END, values=(
                    r["item_name"], r["category"], qty,
                    format_currency(r["price"]),
                    format_currency(r["total_revenue"] or 0),
                    format_currency(cost),
                    format_currency(r["profit"] or 0)))
            return

        if view == "yearly":
            self.date_combo.pack_forget()
            self.year_combo.pack(side=tk.LEFT, padx=(0, 10))
            self.month_combo.pack_forget()
            year = int(self.year_var.get())
            data = models.get_yearly_report(year)
            total_rev = sum(r["total_revenue"] or 0 for r in data)
            total_profit = sum(r["total_profit"] or 0 for r in data)
            ttk.Label(self.summary_frame,
                      text=f"Yearly Report: {year}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Revenue: {format_currency(total_rev)}").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(self.summary_frame,
                      text=f"Profit: {format_currency(total_profit)}").pack(side=tk.LEFT, padx=(0, 20))
            months_named = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            self.tree["columns"] = ["Month", "Sales", "Qty Sold", "Revenue", "Profit"]
            for c in self.tree["columns"]:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=110, anchor="center")
            for r in data:
                m = int(r["month"]) - 1
                self.tree.insert("", tk.END, values=(
                    months_named[m], r["sale_count"], r["total_qty"],
                    format_currency(r["total_revenue"] or 0),
                    format_currency(r["total_profit"] or 0)))
            if not data:
                self.tree.insert("", tk.END, values=("No sales data", "", "", "", ""))

    def _export(self):
        view = self.view_var.get()
        data = []
        headers = []
        if view == "daily":
            date_str = self.date_var.get()
            rows = models.get_sales(from_date=date_str, to_date=date_str)
            headers = ["Item", "Category", "Qty", "Price", "Total"]
            data = [[r["item_name"], r["category"], r["quantity_sold"],
                     r["price"], r["total"]] for r in rows]
            default_name = f"sales_{date_str}.csv"
        elif view == "monthly":
            year = int(self.year_var.get())
            month_num = self.month_map.get(self.month_var.get())
            rows = models.get_monthly_report(year, month_num)
            headers = ["Item", "Category", "Qty", "Unit Price", "Revenue", "Cost", "Profit"]
            data = [[r["item_name"], r["category"], r["qty_sold"],
                     r["price"], r["total_revenue"],
                     r["qty_sold"] * r["purchase_price"], r["profit"]]
                    for r in rows]
            default_name = f"monthly_{year}_{month_num:02d}.csv"
        else:
            year = int(self.year_var.get())
            rows = models.get_yearly_report(year)
            headers = ["Month", "Sales Count", "Qty Sold", "Revenue", "Profit"]
            data = [[r["month"], r["sale_count"], r["total_qty"],
                     r["total_revenue"], r["total_profit"]] for r in rows]
            default_name = f"yearly_{year}.csv"
        export_to_csv(data, headers, default_name)
