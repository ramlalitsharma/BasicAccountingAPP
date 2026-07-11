import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from database import models
from config import (
    APP_NAME, VERSION,
    CARD_BG, BG_COLOR, FONT_FAMILY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CARD_BORDER,
    FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL,
    PADDING_LG, PRIMARY_COLOR, ACCENT_COLOR,
    DANGER_COLOR,
)
from utils.formatters import format_currency, safe_float
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class MetricCard(tk.Frame):
    def __init__(self, parent, label, icon, color, bg_color, on_click=None, **kwargs):
        super().__init__(parent, bg=CARD_BG,
                         highlightbackground=CARD_BORDER,
                         highlightthickness=1, padx=16, pady=14, **kwargs)
        self.columnconfigure(1, weight=1)

        icon_f = tk.Frame(self, bg=bg_color, width=42, height=42)
        icon_f.pack_propagate(False)
        icon_f.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="nw")

        tk.Label(icon_f, text=icon, font=(FONT_FAMILY, 20),
                 bg=bg_color, fg=color).place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self, text=label, font=(FONT_FAMILY, FONT_SIZE_SM),
                 bg=CARD_BG, fg=TEXT_SECONDARY).grid(row=0, column=1, sticky="sw", pady=(0, 1))

        self.value_lbl = tk.Label(self, text="--", font=(FONT_FAMILY, 20, "bold"),
                                  bg=CARD_BG, fg=color)
        self.value_lbl.grid(row=1, column=1, sticky="nw")

        if on_click:
            self.configure(cursor="hand2")
            for w in (self, icon_f, self.value_lbl):
                w.bind("<Button-1>", lambda e: on_click())

    def set_value(self, text):
        self.value_lbl.config(text=text)


class DashboardPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        self._welcome_frame = tk.Frame(self, bg=BG_COLOR)
        self._dashboard_frame = tk.Frame(self, bg=BG_COLOR)
        self._build_welcome()
        self._build_dashboard()

    def _build_welcome(self):
        w = self._welcome_frame
        tk.Frame(w, bg=BG_COLOR, height=40).pack()

        tk.Label(w, text=APP_NAME, font=(FONT_FAMILY, 36, "bold"),
                 bg=BG_COLOR, fg=PRIMARY_COLOR).pack(pady=(0, 4))
        tk.Label(w, text=f"Version {VERSION} | Professional Accounting Suite",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_MUTED).pack()
        tk.Frame(w, bg=BG_COLOR, height=24).pack()

        card = tk.Frame(w, bg=CARD_BG, highlightbackground=CARD_BORDER,
                        highlightthickness=1, padx=30, pady=20)
        card.pack(pady=6)

        tk.Label(card, text="Get Started", font=(FONT_FAMILY, FONT_SIZE_XL, "bold"),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack()
        tk.Frame(card, bg=BG_COLOR, height=8).pack()
        tk.Label(card, text="Open an existing workbook or create a new one to begin.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=CARD_BG, fg=TEXT_SECONDARY).pack()

        btn_row = tk.Frame(card, bg=CARD_BG)
        btn_row.pack(pady=10)

        for text, cmd, color in [
            ("\u2795  New File", self._new_file, ACCENT_COLOR),
            ("\uD83D\uDCC2  Open File", self._open_file, PRIMARY_COLOR),
        ]:
            tk.Button(btn_row, text=text, font=(FONT_FAMILY, FONT_SIZE_LG, "bold"),
                      bg=color, fg="white", bd=0, padx=20, pady=8,
                      cursor="hand2", command=cmd).pack(side=tk.LEFT, padx=6)

        tk.Frame(w, bg=BG_COLOR, height=20).pack()
        features_frame = tk.Frame(w, bg=BG_COLOR)
        features_frame.pack(pady=6)

        for icon, title, desc in [
            ("\u25A3", "Stock Management", "Track inventory, categories, and low stock alerts"),
            ("\u20B9", "Sales & Billing", "Record sales, print bills, and manage payments"),
            ("\u25C8", "Supplier & Customer", "Manage your business relationships"),
            ("\u25A4", "Reports & Analytics", "Visual reports with revenue trends"),
        ]:
            f = tk.Frame(features_frame, bg=CARD_BG, highlightbackground=CARD_BORDER,
                         highlightthickness=1, padx=14, pady=6)
            f.pack(fill=tk.X, pady=2, padx=40)
            tk.Label(f, text=f"{icon}  {title}", font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
                     bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
            tk.Label(f, text=desc, font=(FONT_FAMILY, FONT_SIZE_SM),
                     bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w")

    def _new_file(self):
        app = self.winfo_toplevel()
        if hasattr(app, '_new_file'):
            app._new_file()

    def _open_file(self):
        app = self.winfo_toplevel()
        if hasattr(app, '_open_file_dialog'):
            app._open_file_dialog()

    def _build_dashboard(self):
        d = self._dashboard_frame
        self._cards = {}
        self._canvas_refs = []

        tk.Label(d, text="Dashboard", font=(FONT_FAMILY, FONT_SIZE_XXL, "bold"),
                 bg=BG_COLOR, fg=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_LG, pady=(16, 2))
        tk.Label(d, text="Business overview at a glance",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=PADDING_LG)
        tk.Frame(d, bg=BG_COLOR, height=6).pack()

        canvas = tk.Canvas(d, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(d, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_COLOR)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        cf = scroll_frame

        # ---- KPI CARDS ----
        cards_data = [
            ("Total Items", "total_items", "\u25A3", "#2563EB", "#EFF6FF"),
            ("Low Stock", "low_stock", "\u26A0", "#DC2626", "#FEF2F2"),
            ("Stock Value", "stock_value", "\u20B9", "#059669", "#ECFDF5"),
            ("Today's Revenue", "sales_today", "\u2191", "#0284C7", "#F0F9FF"),
            ("Monthly Revenue", "monthly_revenue", "\u2211", "#0891B2", "#ECFEFF"),
            ("Pending Payments", "total_pending", "\u23F0", "#EA580C", "#FFF7ED"),
            ("Extra Income Today", "extra_income_today", "\u2726", "#7C3AED", "#F5F3FF"),
            ("Total Customers", "total_customers", "\u25CF", "#0D9488", "#F0FDFA"),
        ]

        cards_grid = tk.Frame(cf, bg=BG_COLOR)
        cards_grid.pack(fill=tk.X, padx=PADDING_LG, pady=(0, 10))

        click_map = {
            "total_items": self._show_all_items,
            "total_pending": self._show_pending_customers,
        }
        for i, (label, key, icon, color, card_bg) in enumerate(cards_data):
            on_click = click_map.get(key)
            card = MetricCard(cards_grid, label, icon, color, card_bg, on_click=on_click)
            card.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="nsew")
            self._cards[key] = card

        for i in range(4):
            cards_grid.grid_columnconfigure(i, weight=1)

        # ---- CHARTS ROW 1 ----
        charts1 = tk.Frame(cf, bg=BG_COLOR)
        charts1.pack(fill=tk.X, padx=PADDING_LG, pady=(0, 10))

        for side, lbl, figsize in [("left", "Revenue Trend (Last 7 Days)", (5, 2.8)),
                                     ("right", "Payment Status Breakdown", (4, 2.8))]:
            wrap = ttk.LabelFrame(charts1, text=lbl, padding=8)
            wrap.pack(side=side, fill=tk.BOTH, expand=True, padx=4)

            fig = Figure(figsize=figsize, dpi=80, facecolor="#F8FAFC")
            ax = fig.add_subplot(111)
            canvas_w = FigureCanvasTkAgg(fig, wrap)
            canvas_w.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            if side == "left":
                self._fig_trend, self._ax_trend, self._canvas_trend = fig, ax, canvas_w
            else:
                self._fig_pie, self._ax_pie, self._canvas_pie = fig, ax, canvas_w

        # ---- CHARTS ROW 2 ----
        charts2 = tk.Frame(cf, bg=BG_COLOR)
        charts2.pack(fill=tk.X, padx=PADDING_LG, pady=(0, 10))

        for side, lbl, figsize in [("left", "Monthly Revenue vs Extra Income", (5, 2.8)),
                                     ("right", "Stock by Category", (4, 2.8))]:
            wrap = ttk.LabelFrame(charts2, text=lbl, padding=8)
            wrap.pack(side=side, fill=tk.BOTH, expand=True, padx=4)

            fig = Figure(figsize=figsize, dpi=80, facecolor="#F8FAFC")
            ax = fig.add_subplot(111)
            canvas_w = FigureCanvasTkAgg(fig, wrap)
            canvas_w.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            if side == "left":
                self._fig_monthly, self._ax_monthly, self._canvas_monthly = fig, ax, canvas_w
            else:
                self._fig_stock, self._ax_stock, self._canvas_stock = fig, ax, canvas_w

        # ---- RECENT ACTIVITY SECTION ----
        activity_frame = tk.Frame(cf, bg=BG_COLOR)
        activity_frame.pack(fill=tk.X, padx=PADDING_LG, pady=(0, 16))

        # Recent Sales
        recent_sales_frame = ttk.LabelFrame(activity_frame, text="Recent Sales (Last 10)", padding=8)
        recent_sales_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self._recent_sales_tree = ttk.Treeview(recent_sales_frame,
            columns=("date", "item", "customer", "amount", "status"),
            show="headings", height=6)
        for col, w, txt in [("date", 90, "Date"), ("item", 130, "Item"),
                             ("customer", 120, "Customer"), ("amount", 80, "Amount"),
                             ("status", 80, "Status")]:
            self._recent_sales_tree.heading(col, text=txt)
            self._recent_sales_tree.column(col, width=w, minwidth=60)
        self._recent_sales_tree.pack(fill=tk.BOTH, expand=True)

        # Recent Preorders
        recent_preorders_frame = ttk.LabelFrame(activity_frame, text="Recent Preorders (Last 10)", padding=8)
        recent_preorders_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=4)

        self._recent_preorders_tree = ttk.Treeview(recent_preorders_frame,
            columns=("date", "customer", "item", "total", "status"),
            show="headings", height=6)
        for col, w, txt in [("date", 90, "Date"), ("customer", 120, "Customer"),
                             ("item", 130, "Item"), ("total", 80, "Total"),
                             ("status", 80, "Status")]:
            self._recent_preorders_tree.heading(col, text=txt)
            self._recent_preorders_tree.column(col, width=w, minwidth=60)
        self._recent_preorders_tree.pack(fill=tk.BOTH, expand=True)

        # Refresh button
        btn_frame = tk.Frame(cf, bg=BG_COLOR)
        btn_frame.pack(pady=(0, 16))
        ttk.Button(btn_frame, text="\u21BB  Refresh Dashboard",
                   command=self.refresh).pack()

        self.refresh()

    def _safe_get_sales(self):
        try:
            return models.get_sales()
        except FileNotFoundError:
            return []

    def _safe_get_stock_items(self):
        try:
            return models.get_stock_items()
        except FileNotFoundError:
            return []

    def _safe_get_yearly_report(self, year):
        try:
            return models.get_yearly_report(year)
        except FileNotFoundError:
            return []

    def _plot_revenue_trend(self):
        self._ax_trend.clear()
        sales = self._safe_get_sales()
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        revenues = []
        for d in dates:
            day_sales = [s for s in sales if str(s.get("Sale_Date") or "")[:10] == d]
            revenues.append(sum(safe_float(s.get("Total", 0)) for s in day_sales))
        self._ax_trend.plot(dates, revenues, marker="o", color="#2563EB", linewidth=2)
        self._ax_trend.set_xticks(range(len(dates)))
        self._ax_trend.set_xticklabels([d[-5:] for d in dates], rotation=45, fontsize=8)
        self._ax_trend.set_ylabel("Revenue", fontsize=9)
        self._ax_trend.grid(True, alpha=0.3)
        self._fig_trend.tight_layout()
        self._canvas_trend.draw()

    def _plot_payment_breakdown(self):
        self._ax_pie.clear()
        sales = self._safe_get_sales()
        paid = sum(safe_float(s.get("Paid_Amount", 0)) for s in sales)
        unpaid = sum(safe_float(s.get("Unpaid_Amount", 0)) for s in sales)
        if paid + unpaid == 0:
            self._ax_pie.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=10)
        else:
            self._ax_pie.pie([paid, unpaid], labels=["Paid", "Unpaid"],
                           autopct="%1.1f%%", colors=["#059669", "#DC2626"],
                           startangle=90)
        self._ax_pie.set_title(f"Total: {format_currency(paid + unpaid)}", fontsize=9)
        self._fig_pie.tight_layout()
        self._canvas_pie.draw()

    def _plot_monthly_comparison(self):
        self._ax_monthly.clear()
        year = datetime.now().year
        yearly = self._safe_get_yearly_report(year)
        if not yearly:
            self._ax_monthly.text(0.5, 0.5, "No data for this year", ha="center", va="center", fontsize=10)
        else:
            months = [r["month"] for r in yearly]
            revenues = [safe_float(r.get("total_revenue", 0)) for r in yearly]
            extras = [safe_float(r.get("extra_income", 0)) for r in yearly]
            x = range(len(months))
            w = 0.35
            self._ax_monthly.bar([i - w/2 for i in x], revenues, w, label="Revenue", color="#2563EB")
            self._ax_monthly.bar([i + w/2 for i in x], extras, w, label="Extra Income", color="#7C3AED")
            self._ax_monthly.set_xticks(x)
            self._ax_monthly.set_xticklabels([f"M{m}" for m in months], fontsize=8)
            self._ax_monthly.legend(fontsize=8)
        self._fig_monthly.tight_layout()
        self._canvas_monthly.draw()

    def _plot_stock_by_category(self):
        self._ax_stock.clear()
        stock = self._safe_get_stock_items()
        cats = {}
        for s in stock:
            cat = s.get("Category", "Uncategorized")
            cats[cat] = cats.get(cat, 0) + int(safe_float(s.get("Quantity", 0)))
        if not cats:
            self._ax_stock.text(0.5, 0.5, "No stock data", ha="center", va="center", fontsize=10)
        else:
            labels = list(cats.keys())
            sizes = list(cats.values())
            self._ax_stock.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
            self._ax_stock.set_title(f"Total Items: {sum(sizes)}", fontsize=9)
        self._fig_stock.tight_layout()
        self._canvas_stock.draw()

    def refresh(self):
        if not models.get_active_file():
            self._dashboard_frame.pack_forget()
            self._welcome_frame.pack(fill=tk.BOTH, expand=True)
            return
        self._welcome_frame.pack_forget()
        self._dashboard_frame.pack(fill=tk.BOTH, expand=True)

        try:
            stats = models.get_dashboard_stats()
        except (FileNotFoundError, OSError):
            stats = {}

        # Calculate monthly revenue
        year = datetime.now().year
        monthly_data = self._safe_get_yearly_report(year)
        monthly_revenue = sum(safe_float(r.get("total_revenue", 0)) for r in monthly_data)

        total_customers = len(self._safe_get_sales())
        try:
            customers = models.get_customers()
            total_customers = len(customers)
        except (FileNotFoundError, OSError):
            pass

        stats["monthly_revenue"] = monthly_revenue
        stats["total_customers"] = total_customers

        currency_keys = {"stock_value", "sales_today", "monthly_revenue",
                         "extra_income_today", "total_revenue", "total_pending"}
        for key, card in self._cards.items():
            val = stats.get(key, 0)
            text = format_currency(val) if key in currency_keys else str(int(val))
            card.set_value(text)

        self._plot_revenue_trend()
        self._plot_payment_breakdown()
        self._plot_monthly_comparison()
        self._plot_stock_by_category()

        self._load_recent_sales()
        self._load_recent_preorders()

    def _load_recent_sales(self):
        for item in self._recent_sales_tree.get_children():
            self._recent_sales_tree.delete(item)
        sales = self._safe_get_sales()
        for s in sales[:10]:
            self._recent_sales_tree.insert("", tk.END, values=(
                str(s.get("Sale_Date") or "")[:10],
                s.get("item_name", ""),
                s.get("customer_name", ""),
                format_currency(s.get("Total", 0)),
                (s.get("payment_status") or "unknown").capitalize(),
            ))

    def _load_recent_preorders(self):
        for item in self._recent_preorders_tree.get_children():
            self._recent_preorders_tree.delete(item)
        try:
            preorders = models.get_preorders()
        except (FileNotFoundError, OSError):
            preorders = []
        for p in preorders[:10]:
            self._recent_preorders_tree.insert("", tk.END, values=(
                str(p.get("Created_At") or "")[:10],
                p.get("customer_name", ""),
                p.get("item_name", ""),
                format_currency(p.get("Total", 0)),
                (p.get("Status") or "pending").capitalize(),
            ))

    def _show_pending_customers(self):
        try:
            sales = models.get_sales()
            customers = models.get_customers()
        except (FileNotFoundError, OSError):
            messagebox.showinfo("Pending Payments", "No data available")
            return

        cust_map = {}
        for c in customers:
            cust_map[c.get("ID")] = c.get("Name", "Unknown")

        pending_by_cust = {}
        for s in sales:
            unpaid = safe_float(s.get("Unpaid_Amount", 0))
            if unpaid > 0:
                cid = s.get("Customer_ID")
                if cid not in pending_by_cust:
                    pending_by_cust[cid] = {"total": 0.0, "latest_date": ""}
                pending_by_cust[cid]["total"] += unpaid
                sale_date = str(s.get("Sale_Date") or "")[:10]
                if sale_date and (not pending_by_cust[cid]["latest_date"] or sale_date > pending_by_cust[cid]["latest_date"]):
                    pending_by_cust[cid]["latest_date"] = sale_date

        if not pending_by_cust:
            messagebox.showinfo("Pending Payments", "No pending payments found!")
            return

        app = self.winfo_toplevel()
        body = app.show_modal("Pending Payments by Customer", width=700, height=450)

        tk.Label(body, text=f"Customers with unpaid balances",
                 font=(FONT_FAMILY, FONT_SIZE_MD),
                 bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=(0, 8))

        cols = ("customer", "pending_amount", "latest_sale", "days_pending")
        tree = ttk.Treeview(body, columns=cols, show="headings", height=15)
        tree.heading("customer", text="Customer")
        tree.heading("pending_amount", text="Pending Amount")
        tree.heading("latest_sale", text="Latest Sale")
        tree.heading("days_pending", text="Days Pending")
        tree.column("customer", width=200, anchor="w")
        tree.column("pending_amount", width=150, anchor="e")
        tree.column("latest_sale", width=120, anchor="center")
        tree.column("days_pending", width=100, anchor="center")

        scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        total_pending = 0.0
        today = datetime.now()
        rows = []
        for cid, info in pending_by_cust.items():
            name = cust_map.get(cid, f"Customer #{cid}")
            total_pending += info["total"]
            days = ""
            if info["latest_date"]:
                try:
                    sale_dt = datetime.strptime(info["latest_date"], "%Y-%m-%d")
                    days = str((today - sale_dt).days)
                except ValueError:
                    days = "?"
            rows.append((name, info["total"], info["latest_date"], days))

        rows.sort(key=lambda r: r[1], reverse=True)
        for name, amount, date, days in rows:
            tree.insert("", tk.END, values=(name, format_currency(amount), date, days))

        tk.Label(body, text=f"Total Pending: {format_currency(total_pending)}",
                 font=(FONT_FAMILY, FONT_SIZE_LG, "bold"),
                 bg=CARD_BG, fg=DANGER_COLOR).pack(anchor="w", pady=(8, 0))

    def _show_all_items(self):
        try:
            items = models.get_stock_items()
        except FileNotFoundError:
            messagebox.showinfo("Stock Items", "No data available")
            return

        app = self.winfo_toplevel()
        body = app.show_modal("All Stock Items", width=800, height=500)

        cols = ("name", "category", "quantity", "min_qty", "purchase_price", "selling_price")
        tree = ttk.Treeview(body, columns=cols, show="headings", height=20)
        tree.heading("name", text="Item Name")
        tree.heading("category", text="Category")
        tree.heading("quantity", text="Qty")
        tree.heading("min_qty", text="Min Qty")
        tree.heading("purchase_price", text="Purchase Price")
        tree.heading("selling_price", text="Selling Price")
        tree.column("name", width=180, anchor="w")
        tree.column("category", width=120, anchor="w")
        tree.column("quantity", width=70, anchor="e")
        tree.column("min_qty", width=70, anchor="e")
        tree.column("purchase_price", width=110, anchor="e")
        tree.column("selling_price", width=110, anchor="e")

        scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for item in items:
            tree.insert("", tk.END, values=(
                item.get("Item_Name", ""),
                item.get("Category", ""),
                item.get("Quantity", 0),
                item.get("Min_Quantity", 0),
                format_currency(item.get("Purchase_Price", 0)),
                format_currency(item.get("Selling_Price", 0)),
            ))
