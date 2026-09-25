import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from utils.formatters import format_currency, safe_float
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class StockPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        from utils.settings_helper import get_active_stock_field_defs
        self._field_defs = get_active_stock_field_defs()
        self._extra_table_cols = [d for _, d in self._field_defs][:4]
        self._build_ui()

    def _render_extra_fields(self, body, start_row, values=None):
        """Render the active vertical's extra stock fields into a form.
        Returns ``(next_row, {column: StringVar})``."""
        vars_map = {}
        row = start_row
        for _key, d in self._field_defs:
            ttk.Label(body, text=d["label"]).grid(row=row, column=0, padx=10,
                                                  pady=8, sticky="w")
            cur = str(values.get(d["column"], "") or "") if values else ""
            var = tk.StringVar(value=cur)
            if d["kind"] == "choice":
                w = ttk.Combobox(body, textvariable=var, values=d.get("choices", []),
                                 state="readonly", width=37)
            else:
                w = ttk.Entry(body, textvariable=var, width=38)
            w.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
            vars_map[d["column"]] = var
            row += 1
        return row, vars_map

    @staticmethod
    def _collect_extras(vars_map):
        """Extras dict for add/update_stock_item — all rendered columns are
        written (including blanks, so edits can clear a value)."""
        return {col: var.get().strip() for col, var in vars_map.items()}

    def _build_ui(self):
        header = ttk.Label(self, text="Stock Inventory",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search stock items by name or category")

        ttk.Label(toolbar, text="Category:").pack(side=tk.LEFT, padx=(10, 2))
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(toolbar, textvariable=self.cat_var,
                                       width=15, state="readonly")
        self.cat_combo.pack(side=tk.LEFT)
        ToolTip(self.cat_combo, "Filter by category")
        self.cat_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        add_btn = ttk.Button(toolbar, text="Add Item",
                             command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Add a new stock item")

        edit_btn = ttk.Button(toolbar, text="Edit",
                              command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(edit_btn, "Edit selected stock item")

        delete_btn = ttk.Button(toolbar, text="Delete",
                                command=self._delete, style="Danger.TButton")
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(delete_btn, "Delete selected stock item")

        import_btn = ttk.Button(toolbar, text="Import CSV",
                                command=self._import_csv)
        import_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(import_btn, "Import items from CSV file")

        log_btn = ttk.Button(toolbar, text="Stock Log",
                             command=self._show_log)
        log_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(log_btn, "View stock change history")

        export_btn = ttk.Button(toolbar, text="Export CSV",
                                command=self._export)
        export_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(export_btn, "Export stock to CSV file")

        self.alert_btn = tk.Button(toolbar, text="\uD83D\uDD14 Alerts", 
                                    command=self._show_alerts, bd=0, padx=8)
        self.alert_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(self.alert_btn, "View low stock alerts")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDCE6",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No stock items yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'Add Item' to add your first product.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Item": 180, "Category": 130, "Qty": 70, "Min": 65,
                "Cost": 95, "Price": 95, "Margin": 85, "Supplier": 130}
        aligns = {"Qty": "e", "Min": "e", "Cost": "e", "Price": "e", "Margin": "e"}
        for d in self._extra_table_cols:
            cols[d["label"]] = 110
        self.table = Table(self._container, columns=cols, key_column="ID",
                           on_double_click=self._edit_form, alignments=aligns)

        self.refresh()

    def refresh(self):
        cat = self.cat_var.get()
        if cat == "All":
            cat = ""
        try:
            raw = models.get_stock_items(search=self.search.get(), category=cat)
        except FileNotFoundError:
            raw = []
        display = []
        for r in raw:
            cost = safe_float(r.get("Purchase_Price", 0))
            price = safe_float(r.get("Selling_Price", 0))
            margin = ((price - cost) / cost * 100) if cost > 0 else 0
            qty = safe_float(r.get("Quantity", 0))
            min_q = safe_float(r.get("Min_Quantity", 0))
            display_row = {
                "ID": r.get("ID"),
                "Item": r.get("Item_Name", ""),
                "Category": r.get("Category", ""),
                "Qty": qty,
                "Min": min_q,
                "Cost": format_currency(cost),
                "Price": format_currency(price),
                "Margin": f"{margin:.0f}%",
                "Supplier": r.get("supplier_name", ""),
                "Quantity": qty,
                "Min_Quantity": min_q,
            }
            for d in self._extra_table_cols:
                display_row[d["label"]] = str(r.get(d["column"], "") or "")
            display.append(display_row)
        self.table.populate(display)
        self._refresh_categories()
        self._update_alert_count()
        if not display:
            self.table.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
        else:
            self._empty_state.pack_forget()
            self.table.pack(fill=tk.BOTH, expand=True)

    def _refresh_categories(self):
        try:
            cats = models.get_categories()
        except FileNotFoundError:
            cats = []
        current = self.cat_var.get()
        self.cat_combo["values"] = ["All"] + cats
        if not current:
            self.cat_var.set("All")

    def _on_search(self, text):
        self.refresh()

    def _add_form(self):
        app = self.winfo_toplevel()
        body = app.show_modal("Add Stock Item", width=520,
                              height=min(560 + 46 * len(self._field_defs), 780))

        try:
            existing_items = models.get_stock_items()
            existing_categories = models.get_categories()
        except FileNotFoundError:
            existing_items = []
            existing_categories = []
        existing_item_names = sorted({s.get("Item_Name", "") for s in existing_items if s.get("Item_Name")})

        fields = {}
        row = 0
        ttk.Label(body, text="Item Name").grid(row=row, column=0, padx=10,
                                               pady=8, sticky="w")
        item_name_combo = ttk.Combobox(body, values=existing_item_names, width=38)
        item_name_combo.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        fields["item_name"] = item_name_combo
        row += 1

        ttk.Label(body, text="Category").grid(row=row, column=0, padx=10,
                                               pady=8, sticky="w")
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(body, textvariable=category_var,
                                      values=existing_categories,
                                      width=38)
        category_combo.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        fields["category"] = category_combo
        row += 1

        def _on_item_name_change(*args):
            current = item_name_combo.get().strip()
            if not current:
                return
            try:
                cat_list = models.get_categories_for_item(current)
            except FileNotFoundError:
                cat_list = []
            if cat_list:
                category_combo["values"] = cat_list
                if category_var.get() not in cat_list:
                    category_var.set(cat_list[0])
            else:
                category_combo["values"] = existing_categories
        item_name_combo.bind("<<ComboboxSelected>>", lambda e: _on_item_name_change())
        item_name_combo.bind("<FocusOut>", lambda e: _on_item_name_change())
        item_name_combo.bind("<KeyRelease>", lambda e: _on_item_name_change())

        for label, key in [("Quantity", "quantity"),
                           ("Min Quantity", "min_quantity"),
                           ("Purchase Price", "purchase_price"),
                           ("Selling Price", "selling_price")]:
            ttk.Label(body, text=label).grid(row=row, column=0, padx=10,
                                             pady=8, sticky="w")
            entry = ttk.Entry(body, width=38)
            entry.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry
            row += 1

        ttk.Label(body, text="Supplier").grid(row=row, column=0, padx=10,
                                              pady=8, sticky="w")
        suppliers = models.get_suppliers()
        supplier_names = {s["Name"]: s["ID"] for s in suppliers}
        supplier_var = tk.StringVar()
        supplier_combo = ttk.Combobox(body, textvariable=supplier_var,
                                       values=[""] + list(supplier_names.keys()),
                                       state="normal", width=38)
        supplier_combo.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        row += 1
        row, extra_vars = self._render_extra_fields(body, row)

        def save():
            name = fields["item_name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Item Name is required")
                return
            # ── Feature gate: stock item limit per license tier ──
            from utils.feature_gate import require_stock_slot
            if not require_stock_slot(parent=body):
                return
            try:
                qty = int(fields["quantity"].get().strip() or 0)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Quantity.")
                return
            try:
                purchase_price = float(fields["purchase_price"].get().strip() or 0)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Purchase Price.")
                return
            try:
                selling_price = float(fields["selling_price"].get().strip() or 0)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Selling Price.")
                return
            try:
                min_qty = int(fields["min_quantity"].get().strip() or 5)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Min Quantity.")
                return
            chosen_supplier_name = supplier_var.get().strip()
            supplier_id = supplier_names.get(chosen_supplier_name) if chosen_supplier_name else None
            try:
                models.add_stock_item(
                    name, fields["category"].get().strip(),
                    qty, purchase_price, selling_price,
                    min_qty,
                    supplier_id,
                    extras=self._collect_extras(extra_vars),
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

        save_row = row
        ttk.Button(body, text="Save", command=save).grid(
            row=save_row, column=0, columnspan=2, pady=(20, 10))
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
        body = app.show_modal("Edit Stock Item", width=520,
                              height=min(560 + 46 * len(self._field_defs), 780))

        try:
            existing_items = models.get_stock_items()
            existing_categories = models.get_categories()
        except FileNotFoundError:
            existing_items = []
            existing_categories = []
        existing_item_names = sorted({s.get("Item_Name", "") for s in existing_items if s.get("Item_Name")})

        fields = {}
        row = 0
        ttk.Label(body, text="Item Name").grid(row=row, column=0, padx=10,
                                               pady=8, sticky="w")
        item_name_combo = ttk.Combobox(body, values=existing_item_names, width=38)
        current_name = item.get("Item_Name", "")
        item_name_combo.set(current_name)
        item_name_combo.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        fields["Item_Name"] = item_name_combo
        row += 1

        ttk.Label(body, text="Category").grid(row=row, column=0, padx=10,
                                               pady=8, sticky="w")
        category_var = tk.StringVar(value=item.get("Category", ""))
        category_combo = ttk.Combobox(body, textvariable=category_var,
                                      values=existing_categories, width=38)
        category_combo.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        fields["Category"] = category_combo
        row += 1

        def _on_item_name_change(*args):
            current = item_name_combo.get().strip()
            if not current or current == current_name:
                return
            try:
                cat_list = models.get_categories_for_item(current)
            except FileNotFoundError:
                cat_list = []
            if cat_list:
                category_combo["values"] = cat_list
                if category_var.get() not in cat_list:
                    category_var.set(cat_list[0])
        item_name_combo.bind("<<ComboboxSelected>>", lambda e: _on_item_name_change())
        item_name_combo.bind("<FocusOut>", lambda e: _on_item_name_change())

        for label, key in [("Quantity", "Quantity"),
                           ("Min Quantity", "Min_Quantity"),
                           ("Purchase Price", "Purchase_Price"),
                           ("Selling Price", "Selling_Price")]:
            ttk.Label(body, text=label).grid(row=row, column=0, padx=10,
                                             pady=8, sticky="w")
            entry = ttk.Entry(body, width=38)
            entry.insert(0, str(item.get(key, "")))
            entry.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry
            row += 1

        suppliers = models.get_suppliers()
        supplier_names = {s["Name"]: s["ID"] for s in suppliers}
        supplier_var = tk.StringVar()
        ttk.Label(body, text="Supplier").grid(row=row, column=0, padx=10,
                                              pady=8, sticky="w")
        supplier_combo = ttk.Combobox(body, textvariable=supplier_var,
                                       values=[""] + list(supplier_names.keys()),
                                       state="normal", width=38)
        supplier_combo.grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        if item.get("supplier_name"):
            supplier_var.set(item["supplier_name"])
        row += 1
        row, extra_vars = self._render_extra_fields(body, row, values=item)

        def save():
            name = fields["Item_Name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Item Name is required")
                return
            try:
                qty = int(fields["Quantity"].get().strip() or 0)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Quantity.")
                return
            try:
                min_qty = int(fields["Min_Quantity"].get().strip() or 5)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Min Quantity.")
                return
            try:
                purchase_price = float(fields["Purchase_Price"].get().strip() or 0)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Purchase Price.")
                return
            try:
                selling_price = float(fields["Selling_Price"].get().strip() or 0)
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Selling Price.")
                return
            chosen_supplier_name = supplier_var.get().strip()
            supplier_id = supplier_names.get(chosen_supplier_name) if chosen_supplier_name else None
            try:
                models.update_stock_item(
                    item_id, name, fields["Category"].get().strip(),
                    qty, min_qty, purchase_price, selling_price,
                    supplier_id,
                    extras=self._collect_extras(extra_vars),
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
            row=row, column=0, columnspan=2, pady=(20, 10))
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
                errors = []
                # First, count incoming rows so we can enforce the stock cap
                # once before any partial-import damage.
                rows = list(reader)
                from utils.feature_gate import max_stock_items, current_stock_count
                cap = max_stock_items()
                cur = current_stock_count()
                slot_left = max(0, cap - cur)
                if slot_left <= 0:
                    messagebox.showwarning(
                        "Stock limit reached",
                        f"You already have {cur}/{cap} stock items.\n"
                        f"Upgrade your license in Settings → License to add more.",
                    )
                    return
                if len(rows) > slot_left:
                    if not messagebox.askyesno(
                        "Stock limit will be reached",
                        f"Importing {len(rows)} items but you only have "
                        f"{slot_left} slot(s) left under the current plan "
                        f"(cap {cap}). Only the first {slot_left} items will be "
                        f"imported. Continue?",
                    ):
                        return
                    rows = rows[:slot_left]
                reader = iter(rows)
                for i, row in enumerate(reader, start=2):
                    try:
                        qty = int(row.get("Quantity", 0))
                    except (ValueError, TypeError):
                        errors.append(f"Row {i}: invalid Quantity '{row.get('Quantity', '')}'")
                        continue
                    try:
                        pp = float(row.get("Purchase_Price", 0))
                    except (ValueError, TypeError):
                        errors.append(f"Row {i}: invalid Purchase_Price '{row.get('Purchase_Price', '')}'")
                        continue
                    try:
                        sp = float(row.get("Selling_Price", 0))
                    except (ValueError, TypeError):
                        errors.append(f"Row {i}: invalid Selling_Price '{row.get('Selling_Price', '')}'")
                        continue
                    try:
                        mq = int(row.get("Min_Quantity", 5))
                    except (ValueError, TypeError):
                        errors.append(f"Row {i}: invalid Min_Quantity '{row.get('Min_Quantity', '')}'")
                        continue
                    models.add_stock_item(
                        row.get("Item_Name", row.get("Item", "")),
                        row.get("Category", ""),
                        qty, pp, sp, mq,
                    )
                    count += 1
            self.refresh()
            msg = f"Imported {count} items"
            if errors:
                msg += "\n\nSkipped rows:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    msg += f"\n... and {len(errors)-10} more"
            messagebox.showinfo("Import", msg)
        except PermissionError as e:
            messagebox.showerror("Update Required", str(e))
        except (FileNotFoundError, PermissionError, OSError, ValueError) as e:
            messagebox.showerror("Import Error", str(e))

    def _show_log(self):
        item_key = self.table.get_selected_key()
        try:
            logs = models.get_stock_log(stock_id=item_key, limit=200)
        except FileNotFoundError:
            messagebox.showinfo("Stock Log", "No workbook open.")
            return
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
            cost = safe_float(r.get("Purchase_Price", 0))
            price = safe_float(r.get("Selling_Price", 0))
            margin = f"{((price - cost) / cost * 100):.0f}%" if cost > 0 else "0%"
            rows.append([r.get("Item_Name"), r.get("Category"), r.get("Quantity"),
                         r.get("Min_Quantity"), cost, price, margin,
                         r.get("supplier_name", "")])
        export_to_csv(rows, headers, "stock_export.csv")

    def _update_alert_count(self):
        try:
            raw = models.get_stock_items()
        except FileNotFoundError:
            raw = []
        low = [s for s in raw if safe_float(s.get("Quantity", 0)) <= safe_float(s.get("Min_Quantity", 0))]
        count = len(low)
        if count > 0:
            self.alert_btn.config(text=f"\uD83D\uDD14 {count} Low Stock", fg="white", bg="#DC2626")
        else:
            self.alert_btn.config(text="\uD83D\uDD14 No Alerts", fg="black", bg="SystemButtonFace")

    def _show_alerts(self):
        try:
            raw = models.get_stock_items()
        except FileNotFoundError:
            messagebox.showinfo("Stock Alerts", "No workbook open. Create or open one first.")
            return
        low = [s for s in raw if safe_float(s.get("Quantity", 0)) <= safe_float(s.get("Min_Quantity", 0))]
        if not low:
            messagebox.showinfo("Stock Alerts", "No low stock items found!")
            return
        msg = "The following items are low in stock:\n\n"
        for s in low:
            qty = safe_float(s.get("Quantity", 0))
            min_q = safe_float(s.get("Min_Quantity", 0))
            msg += f"\u2022 {s['Item_Name']} (Qty: {qty}, Min: {min_q})\n"
        messagebox.showwarning(f"Low Stock Alert ({len(low)} items)", msg)