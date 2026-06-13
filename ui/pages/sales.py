import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from utils.export import export_to_csv
from utils.billing import print_bill


class SalesPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Sales",
                           font=("Segoe UI", 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)

        ttk.Label(toolbar, text="From:").pack(side=tk.LEFT, padx=(10, 2))
        self.from_var = tk.StringVar()
        self.from_entry = ttk.Entry(toolbar, textvariable=self.from_var, width=12)
        self.from_entry.pack(side=tk.LEFT)
        self.from_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ttk.Label(toolbar, text="To:").pack(side=tk.LEFT, padx=(5, 2))
        self.to_var = tk.StringVar()
        self.to_entry = ttk.Entry(toolbar, textvariable=self.to_var, width=12)
        self.to_entry.pack(side=tk.LEFT)
        self.to_entry.bind("<KeyRelease>", lambda e: self.refresh())

        add_btn = ttk.Button(toolbar, text="New Sale",
                             command=self._new_sale_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        return_btn = ttk.Button(toolbar, text="Return Sale",
                                command=self._return_sale)
        return_btn.pack(side=tk.RIGHT, padx=(5, 0))
        delete_btn = ttk.Button(toolbar, text="Delete",
                                command=self._delete_sale)
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        print_btn = ttk.Button(toolbar, text="Print Bill",
                               command=self._print_bill)
        print_btn.pack(side=tk.RIGHT, padx=(5, 0))
        export_btn = ttk.Button(toolbar, text="Export CSV",
                                command=self._export)
        export_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cols = {"Invoice": 100, "Item": 160, "Category": 100,
                "Qty": 70, "Price": 90, "Total": 90, "Date": 150}
        self.table = Table(self, columns=cols, key_column="ID",
                           on_double_click=self._print_bill)
        self.table.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.refresh()

    def _fmt_invoice(self, sale):
        sid = sale.get("ID", 0)
        invoice = models.format_invoice_id(sid) if hasattr(models, 'format_invoice_id') else f"#{sid}"
        sale["_invoice"] = invoice

    def refresh(self):
        data = models.get_sales(
            search=self.search.get(),
            from_date=self.from_var.get().strip(),
            to_date=self.to_var.get().strip(),
        )
        display = []
        for r in data:
            self._fmt_invoice(r)
            display.append({
                "ID": r.get("ID"),
                "Invoice": r.get("_invoice"),
                "Item": r.get("item_name", ""),
                "Category": r.get("category", ""),
                "Qty": r.get("Quantity_Sold", 0),
                "Price": r.get("Price", 0),
                "Total": r.get("Total", 0),
                "Date": r.get("Sale_Date", ""),
            })
        self.table.populate(display)

    def _on_search(self, text):
        self.refresh()

    def _new_sale_form(self):
        app = self.winfo_toplevel()
        body = app.show_modal("New Sale", width=450, height=320)

        stock_items = models.get_stock_items()
        item_map = {f"{s['Item_Name']} (Qty: {s['Quantity']})": s["ID"]
                    for s in stock_items}

        ttk.Label(body, text="Item").grid(row=0, column=0, padx=10,
                                          pady=10, sticky="w")
        item_var = tk.StringVar()
        item_combo = ttk.Combobox(body, textvariable=item_var,
                                   values=list(item_map.keys()),
                                   state="normal", width=35)
        item_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Quantity").grid(row=1, column=0, padx=10,
                                              pady=10, sticky="w")
        qty_entry = ttk.Entry(body, width=35)
        qty_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Selling Price").grid(row=2, column=0, padx=10,
                                                   pady=10, sticky="w")
        price_entry = ttk.Entry(body, width=35)
        price_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Total Amount").grid(row=3, column=0, padx=10,
                                                  pady=10, sticky="w")
        total_var = tk.StringVar()
        total_entry = ttk.Entry(body, textvariable=total_var, width=35,
                                 state="readonly")
        total_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        def auto_calc(*args):
            try:
                q = float(qty_entry.get() or 0)
                p = float(price_entry.get() or 0)
                total_var.set(f"{q * p:.2f}")
            except ValueError:
                total_var.set("")

        qty_entry.bind("<KeyRelease>", auto_calc)
        price_entry.bind("<KeyRelease>", auto_calc)

        def record():
            selection = item_var.get()
            if not selection or selection not in item_map:
                messagebox.showerror("Error", "Select a valid item")
                return
            try:
                qty = int(qty_entry.get())
                price = float(price_entry.get())
                if qty <= 0 or price <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Quantity and Price must be positive numbers")
                return
            try:
                models.record_sale(item_map[selection], qty, price)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Sale recorded")

        ttk.Button(body, text="Record Sale", command=record).grid(
            row=4, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _return_sale(self):
        sel = self.table.get_selected_row()
        if not sel:
            messagebox.showwarning("No Selection", "Select a sale to return")
            return
        sale_id = sel["key"]
        if messagebox.askyesno("Confirm Return",
                               "This will restore stock and delete the sale. Continue?"):
            try:
                models.return_sale(sale_id)
                self.refresh()
                messagebox.showinfo("Success", "Sale returned and stock restored")
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def _delete_sale(self):
        sale_id = self.table.get_selected_key()
        if not sale_id:
            messagebox.showwarning("No Selection", "Select a sale to delete")
            return
        if messagebox.askyesno("Confirm Delete",
                               "Delete this sale? (stock will NOT be restored)"):
            try:
                models.delete_sale(sale_id)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.refresh()

    def _print_bill(self):
        sel = self.table.get_selected_row()
        if not sel:
            messagebox.showwarning("No Selection", "Select a sale to print")
            return
        values = sel["values"]
        invoice_id = values[0] if values else f"#{sel['key']}"
        sale_data = {
            "id": sel["key"],
            "invoice_id": invoice_id,
            "item_name": values[1],
            "category": values[2],
            "quantity_sold": values[3],
            "price": values[4],
            "total": values[5],
            "sale_date": values[6],
        }
        print_bill(sale_data)

    def _export(self):
        data = models.get_sales(
            search=self.search.get(),
            from_date=self.from_var.get().strip(),
            to_date=self.to_var.get().strip(),
        )
        headers = ["Invoice", "Item", "Category", "Qty", "Price", "Total", "Date"]
        rows = []
        for r in data:
            self._fmt_invoice(r)
            rows.append([r["_invoice"], r["item_name"], r["category"],
                         r["Quantity_Sold"], r["Price"], r["Total"], r["Sale_Date"]])
        export_to_csv(rows, headers, "sales_export.csv")