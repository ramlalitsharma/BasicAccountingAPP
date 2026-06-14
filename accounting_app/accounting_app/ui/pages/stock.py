import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from utils.export import export_to_csv
from utils.formatters import format_currency


class StockPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Stock Inventory",
                           font=("Segoe UI", 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)

        ttk.Label(toolbar, text="Category:").pack(side=tk.LEFT, padx=(10, 2))
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(toolbar, textvariable=self.cat_var,
                                       width=15, state="readonly")
        self.cat_combo.pack(side=tk.LEFT)
        self.cat_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        add_btn = ttk.Button(toolbar, text="Add Item",
                             command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        edit_btn = ttk.Button(toolbar, text="Edit",
                              command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        delete_btn = ttk.Button(toolbar, text="Delete",
                                command=self._delete)
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        import_btn = ttk.Button(toolbar, text="Import CSV",
                                command=self._import_csv)
        import_btn.pack(side=tk.RIGHT, padx=(5, 0))
        log_btn = ttk.Button(toolbar, text="Stock Log",
                             command=self._show_log)
        log_btn.pack(side=tk.RIGHT, padx=(5, 0))
        export_btn = ttk.Button(toolbar, text="Export CSV",
                                command=self._export)
        export_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cols = {"Item": 160, "Category": 120, "Qty": 70, "Min": 60,
                "Cost": 90, "Price": 90, "Margin": 80, "Supplier": 150}
        self.table = Table(self, columns=cols, key_column="ID",
                           on_double_click=self._edit_form)
        self.table.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.refresh()

    def refresh(self):
        cat = self.cat_var.get()
        if cat == "All":
            cat = ""
        raw = models.get_stock_items(search=self.search.get(), category=cat)
        display = []
        for r in raw:
            cost = r.get("Purchase_Price", 0) or 0
            price = r.get("Selling_Price", 0) or 0
            margin = ((price - cost) / cost * 100) if cost > 0 else 0
            display.append({
                "ID": r.get("ID"),
                "Item": r.get("Item_Name", ""),
                "Category": r.get("Category", ""),
                "Qty": r.get("Quantity", 0),
                "Min": r.get("Min_Quantity", 0),
                "Cost": format_currency(cost),
                "Price": format_currency(price),
                "Margin": f"{margin:.0f}%",
                "Supplier": r.get("supplier_name", ""),
            })
        self.table.populate(display)
        self._refresh_categories()

    def _refresh_categories(self):
        cats = models.get_categories()
        current = self.cat_var.get()
        self.cat_combo["values"] = ["All"] + cats
        if not current:
            self.cat_var.set("All")

    def _on_search(self, text):
        self.refresh()

    def _add_form(self):
        app = self.winfo_toplevel()
        body = app.show_modal("Add Stock Item", width=500, height=420)

        fields = {}
        row = 0
        for label, key in [("Item Name", "item_name"),
                           ("Category", "category"),
                           ("Quantity", "quantity"),
                           ("Min Quantity", "min_quantity"),
                           ("Purchase Price", "purchase_price"),
                           ("Selling Price", "selling_price")]:
            ttk.Label(body, text=label).grid(row=row, column=0, padx=10,
                                             pady=6, sticky="w")
            entry = ttk.Entry(body, width=35)
            entry.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
            fields[key] = entry
            row += 1

        ttk.Label(body, text="Supplier").grid(row=row, column=0, padx=10,
                                              pady=6, sticky="w")
        suppliers = models.get_suppliers()
        supplier_names = {s["Name"]: s["ID"] for s in suppliers}
        supplier_var = tk.StringVar()
        ttk.Combobox(body, textvariable=supplier_var,
                     values=[""] + list(supplier_names.keys()),
                     state="normal", width=32).grid(row=row, column=1, padx=10, pady=6, sticky="ew")

        def save():
            try:
                name = fields["item_name"].get().strip()
                if not name:
                    raise ValueError("Item Name is required")
                models.add_stock_item(
                    name, fields["category"].get(),
                    int(fields["quantity"].get() or 0),
                    float(fields["purchase_price"].get() or 0),
                    float(fields["selling_price"].get() or 0),
                    int(fields["min_quantity"].get() or 5),
                    supplier_names.get(supplier_var.get()),
                )
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Item added")

        ttk.Button(body, text="Save", command=save).grid(
            row=row, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _edit_form(self):
        item_id = self.table.get_selected_key()
        if not item_id:
            messagebox.showwarning("No Selection", "Select an item first")
            return
        item = models.get_stock_item(item_id)
        if not item:
            return

        app = self.winfo_toplevel()
        body = app.show_modal("Edit Stock Item", width=500, height=420)

        fields = {}
        row = 0
        for label, key in [("Item Name", "Item_Name"), ("Category", "Category"),
                           ("Quantity", "Quantity"), ("Min Quantity", "Min_Quantity"),
                           ("Purchase Price", "Purchase_Price"),
                           ("Selling Price", "Selling_Price")]:
            ttk.Label(body, text=label).grid(row=row, column=0, padx=10, pady=6, sticky="w")
            entry = ttk.Entry(body, width=35)
            entry.insert(0, str(item.get(key, "")))
            entry.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
            fields[key] = entry
            row += 1

        suppliers = models.get_suppliers()
        supplier_names = {s["Name"]: s["ID"] for s in suppliers}
        supplier_var = tk.StringVar()
        ttk.Label(body, text="Supplier").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        combo = ttk.Combobox(body, textvariable=supplier_var,
                              values=[""] + list(supplier_names.keys()),
                              state="normal", width=32)
        combo.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
        if item.get("supplier_name"):
            supplier_var.set(item["supplier_name"])

        def save():
            try:
                name = fields["Item_Name"].get().strip()
                if not name:
                    raise ValueError("Item Name is required")
                models.update_stock_item(
                    item_id, name, fields["Category"].get(),
                    int(fields["Quantity"].get() or 0),
                    int(fields["Min_Quantity"].get() or 5),
                    float(fields["Purchase_Price"].get() or 0),
                    float(fields["Selling_Price"].get() or 0),
                    supplier_names.get(supplier_var.get()),
                )
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Item updated")

        ttk.Button(body, text="Update", command=save).grid(
            row=row + 1, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _delete(self):
        item_id = self.table.get_selected_key()
        if not item_id:
            messagebox.showwarning("No Selection", "Select an item first")
            return
        if messagebox.askyesno("Confirm", "Delete this stock item?"):
            try:
                models.delete_stock_item(item_id)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.refresh()

    def _import_csv(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        import csv
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    models.add_stock_item(
                        row.get("Item_Name", row.get("Item", "")),
                        row.get("Category", ""),
                        int(row.get("Quantity", 0)),
                        float(row.get("Purchase_Price", 0)),
                        float(row.get("Selling_Price", 0)),
                        int(row.get("Min_Quantity", 5)),
                    )
                    count += 1
            self.refresh()
            messagebox.showinfo("Import", f"Imported {count} items")
        except PermissionError as e:
            messagebox.showerror("Update Required", str(e))
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def _show_log(self):
        item_key = self.table.get_selected_key()
        logs = models.get_stock_log(stock_id=item_key, limit=200)
        app = self.winfo_toplevel()
        body = app.show_modal("Stock Change Log", width=750, height=450)

        cols = {"Created_At": 160, "Change_Type": 100, "Qty_Change": 80,
                "Old_Qty": 70, "New_Qty": 70, "Note": 250}
        tree = ttk.Treeview(body, columns=list(cols.keys()), show="headings")
        for col, w in cols.items():
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=w)
        for log in logs:
            tree.insert("", tk.END, values=[log.get(c, "") for c in cols])
        scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

    def _export(self):
        raw = models.get_stock_items(search=self.search.get(), category=self.cat_var.get())
        headers = ["Item", "Category", "Qty", "Min Qty", "Cost", "Price", "Margin", "Supplier"]
        rows = []
        for r in raw:
            cost = r.get("Purchase_Price", 0) or 0
            price = r.get("Selling_Price", 0) or 0
            margin = f"{((price - cost) / cost * 100):.0f}%" if cost > 0 else "0%"
            rows.append([r.get("Item_Name"), r.get("Category"), r.get("Quantity"),
                         r.get("Min_Quantity"), cost, price, margin,
                         r.get("supplier_name", "")])
        export_to_csv(rows, headers, "stock_export.csv")