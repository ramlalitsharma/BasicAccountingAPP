import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from utils.formatters import format_currency
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class PreordersPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Preorders",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search preorders by customer or item")

        ttk.Label(toolbar, text="Status:").pack(side=tk.LEFT, padx=(5, 2))
        self.status_filter_var = tk.StringVar(value="all")
        self.status_filter = ttk.Combobox(toolbar, textvariable=self.status_filter_var,
                                           values=["all", "pending", "completed", "cancelled"],
                                           state="readonly", width=12)
        self.status_filter.pack(side=tk.LEFT)
        ToolTip(self.status_filter, "Filter by preorder status")
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        add_btn = ttk.Button(toolbar, text="New Preorder",
                   command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Create a new preorder")

        edit_btn = ttk.Button(toolbar, text="Edit",
                   command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(edit_btn, "Edit selected preorder")

        comp_btn = ttk.Button(toolbar, text="Complete",
                   command=self._complete)
        comp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(comp_btn, "Mark preorder as completed")

        cancel_btn = ttk.Button(toolbar, text="Cancel",
                   command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(cancel_btn, "Cancel selected preorder")

        exp_btn = ttk.Button(toolbar, text="Export CSV",
                   command=self._export)
        exp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(exp_btn, "Export preorders to CSV file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDCCB",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No preorders yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'New Preorder' to create one.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Order ID": 70, "Customer": 140, "Item": 150,
                "Qty": 60, "Price": 80, "Total": 90,
                "Delivery": 90, "Status": 90, "Date": 140}
        self.table = Table(self._container, columns=cols, key_column="ID",
                           on_double_click=self._edit_form)

        self.refresh()

    def refresh(self):
        status = self.status_filter_var.get()
        if status == "all":
            status = ""
        try:
            data = models.get_preorders(search=self.search.get(), status=status)
        except FileNotFoundError:
            data = []
        display = []
        for r in data:
            display.append({
                "ID": r.get("ID"),
                "Order ID": r.get("ID"),
                "Customer": r.get("customer_name", ""),
                "Item": r.get("item_name", ""),
                "Qty": r.get("Quantity", 0),
                "Price": format_currency(r.get("Preorder_Price", 0) or 0),
                "Total": format_currency(r.get("Total", 0) or 0),
                "Delivery": r.get("Delivery_Date") or "",
                "Status": (r.get("Status") or "pending").capitalize(),
                "Date": (r.get("Created_At") or "")[:10],
            })
        self.table.populate(display)
        if not display:
            self.table.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
        else:
            self._empty_state.pack_forget()
            self.table.pack(fill=tk.BOTH, expand=True)

    def _on_search(self, text):
        self.refresh()

    def _add_form(self):
        app = self.winfo_toplevel()
        body = app.show_modal("New Preorder", width=550, height=520)

        customers = models.get_customers()
        customer_map = {f"{c['Name']} ({c['Contact']})": c["ID"] for c in customers}

        stock_items = models.get_stock_items()
        item_map = {s["Item_Name"]: s["ID"] for s in stock_items}

        ttk.Label(body, text="Customer").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        customer_var = tk.StringVar()
        customer_combo = ttk.Combobox(body, textvariable=customer_var,
                                        values=list(customer_map.keys()),
                                        state="normal", width=38)
        customer_combo.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Item").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        item_var = tk.StringVar()
        item_combo = ttk.Combobox(body, textvariable=item_var,
                                    values=list(item_map.keys()),
                                    state="normal", width=38)
        item_combo.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        def on_item_select(*args):
            sel = item_var.get()
            if sel in item_map:
                item = next((s for s in stock_items if s["ID"] == item_map[sel]), None)
                if item:
                    price_entry.delete(0, tk.END)
                    price_entry.insert(0, str(item.get("Selling_Price", 0)))

        item_combo.bind("<<ComboboxSelected>>", on_item_select)

        ttk.Label(body, text="Quantity").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        qty_entry = ttk.Entry(body, width=38)
        qty_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Preorder Price").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        price_entry = ttk.Entry(body, width=38)
        price_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Delivery Date").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        delivery_var = tk.StringVar()
        delivery_entry = ttk.Entry(body, textvariable=delivery_var, width=38)
        delivery_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Delivery Address").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        address_entry = ttk.Entry(body, width=38)
        address_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Notes").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        notes_entry = ttk.Entry(body, width=38)
        notes_entry.grid(row=6, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Advance Payment").grid(row=7, column=0, padx=10, pady=8, sticky="w")
        advance_type_var = tk.StringVar(value="none")
        advance_type_combo = ttk.Combobox(body, textvariable=advance_type_var,
                                           values=["none", "full", "partial"],
                                           state="readonly", width=36)
        advance_type_combo.grid(row=7, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Advance Amount").grid(row=8, column=0, padx=10, pady=8, sticky="w")
        advance_amt_entry = ttk.Entry(body, width=38)
        advance_amt_entry.grid(row=8, column=1, padx=10, pady=8, sticky="ew")

        def on_advance_type_change(*args):
            at = advance_type_var.get()
            if at == "none" or at == "full":
                advance_amt_entry.config(state="readonly")
                if at == "full":
                    try:
                        q = float(qty_entry.get() or 0)
                        p = float(price_entry.get() or 0)
                        advance_amt_entry.config(state="normal")
                        advance_amt_entry.delete(0, tk.END)
                        advance_amt_entry.insert(0, f"{q * p:.2f}")
                        advance_amt_entry.config(state="readonly")
                    except ValueError:
                        pass
                else:
                    advance_amt_entry.config(state="normal")
                    advance_amt_entry.delete(0, tk.END)
                    advance_amt_entry.config(state="readonly")
            else:
                advance_amt_entry.config(state="normal")
                advance_amt_entry.delete(0, tk.END)

        advance_type_combo.bind("<<ComboboxSelected>>", on_advance_type_change)

        def save():
            cust_name = customer_var.get()
            item_name = item_var.get()
            if cust_name not in customer_map:
                messagebox.showerror("Error", "Select a valid customer")
                return
            if item_name not in item_map:
                messagebox.showerror("Error", "Select a valid item")
                return
            try:
                qty = int(qty_entry.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Quantity.")
                return
            try:
                price = float(price_entry.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Price.")
                return
            if qty <= 0 or price <= 0:
                messagebox.showerror("Error", "Quantity and Price must be positive numbers")
                return
            delivery = delivery_var.get().strip()
            address = address_entry.get().strip()
            advance_type = advance_type_var.get()
            advance_amt = 0
            if advance_type != "none":
                try:
                    advance_amt_entry.config(state="normal")
                    advance_amt = float(advance_amt_entry.get() or 0)
                    if advance_type != "none" and advance_amt < 0:
                        raise ValueError
                    if advance_type == "full" and advance_amt != qty * price:
                        messagebox.showerror("Error", "Full advance amount must equal total")
                        return
                except ValueError:
                    messagebox.showerror("Input Error", "Please enter a valid advance amount.")
                    return
            try:
                models.add_preorder(
                    customer_map[cust_name], item_map[item_name],
                    qty, price, delivery, notes_entry.get(),
                    delivery_address=address,
                    advance_amount=advance_amt, advance_type=advance_type)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Preorder created")

        ttk.Button(body, text="Create Preorder", command=save).grid(
            row=9, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _edit_form(self):
        oid = self.table.get_selected_key()
        if not oid:
            messagebox.showwarning("No Selection", "Select a preorder first")
            return
        preorder = models.get_preorder(oid)
        if not preorder:
            return
        if preorder.get("Status") != "pending":
            messagebox.showwarning("Cannot Edit", "Only pending preorders can be edited")
            return

        app = self.winfo_toplevel()
        body = app.show_modal("Edit Preorder", width=550, height=520)

        customers = models.get_customers()
        customer_map = {f"{c['Name']} ({c['Contact']})": c["ID"] for c in customers}
        customer_rev = {v: k for k, v in customer_map.items()}

        stock_items = models.get_stock_items()
        item_map = {s["Item_Name"]: s["ID"] for s in stock_items}
        item_rev = {v: k for k, v in item_map.items()}

        ttk.Label(body, text="Customer").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        customer_var = tk.StringVar(value=customer_rev.get(preorder.get("Customer_ID"), ""))
        ttk.Combobox(body, textvariable=customer_var,
                      values=list(customer_map.keys()),
                      state="normal", width=38).grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Item").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        item_var = tk.StringVar(value=item_rev.get(preorder.get("Stock_ID"), ""))
        ttk.Combobox(body, textvariable=item_var,
                      values=list(item_map.keys()),
                      state="normal", width=38).grid(row=1, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Quantity").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        qty_entry = ttk.Entry(body, width=38)
        qty_entry.insert(0, str(preorder.get("Quantity", 0)))
        qty_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Preorder Price").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        price_entry = ttk.Entry(body, width=38)
        price_entry.insert(0, str(preorder.get("Preorder_Price", 0)))
        price_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Delivery Date").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        delivery_var = tk.StringVar(value=preorder.get("Delivery_Date", ""))
        ttk.Entry(body, textvariable=delivery_var, width=38).grid(row=4, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Delivery Address").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        address_entry = ttk.Entry(body, width=38)
        address_entry.insert(0, preorder.get("Delivery_Address", ""))
        address_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Notes").grid(row=6, column=0, padx=10, pady=8, sticky="w")
        notes_entry = ttk.Entry(body, width=38)
        notes_entry.insert(0, preorder.get("Notes", ""))
        notes_entry.grid(row=6, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Advance Payment").grid(row=7, column=0, padx=10, pady=8, sticky="w")
        advance_type_var = tk.StringVar(value=preorder.get("Advance_Payment_Type", "none"))
        advance_type_combo = ttk.Combobox(body, textvariable=advance_type_var,
                                           values=["none", "full", "partial"],
                                           state="readonly", width=36)
        advance_type_combo.grid(row=7, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(body, text="Advance Amount").grid(row=8, column=0, padx=10, pady=8, sticky="w")
        advance_amt_entry = ttk.Entry(body, width=38)
        advance_amt_entry.insert(0, str(preorder.get("Advance_Amount", 0)))
        advance_amt_entry.grid(row=8, column=1, padx=10, pady=8, sticky="ew")

        def save():
            cust_name = customer_var.get()
            item_name = item_var.get()
            if cust_name not in customer_map:
                messagebox.showerror("Error", "Select a valid customer")
                return
            if item_name not in item_map:
                messagebox.showerror("Error", "Select a valid item")
                return
            try:
                qty = int(qty_entry.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Quantity.")
                return
            try:
                price = float(price_entry.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Price.")
                return
            if qty <= 0 or price <= 0:
                messagebox.showerror("Error", "Quantity and Price must be positive numbers")
                return
            advance_type = advance_type_var.get()
            advance_amt = 0
            if advance_type != "none":
                try:
                    advance_amt = float(advance_amt_entry.get() or 0)
                    if advance_type != "none" and advance_amt < 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Input Error", "Please enter a valid advance amount.")
                    return
            try:
                models.update_preorder(oid,
                    customer_map[cust_name], item_map[item_name],
                    qty, price, delivery_var.get().strip(), notes_entry.get(),
                    delivery_address=address_entry.get().strip(),
                    advance_amount=advance_amt, advance_type=advance_type)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Preorder updated")

        ttk.Button(body, text="Update", command=save).grid(
            row=9, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _complete(self):
        oid = self.table.get_selected_key()
        if not oid:
            messagebox.showwarning("No Selection", "Select a preorder to complete")
            return
        preorder = models.get_preorder(oid)
        if not preorder:
            return
        if preorder.get("Status") != "pending":
            messagebox.showwarning("Cannot Complete", f"Only pending preorders can be completed. Current status: {preorder['Status']}")
            return

        item_name = preorder.get("item_name", "Unknown")
        qty = preorder.get("Quantity", 0)
        total = preorder.get("Total", 0)
        advance_amt = float(preorder.get("Advance_Amount", 0) or 0)
        advance_type = preorder.get("Advance_Payment_Type", "none")
        payment_note = "unpaid"
        if advance_amt > 0 and advance_type == "full":
            payment_note = f"paid (₹{advance_amt:.2f} advance already received)"
        elif advance_amt > 0 and advance_type == "partial":
            payment_note = f"partial - ₹{advance_amt:.2f} paid, ₹{max(0, total - advance_amt):.2f} due"
        msg = (f"Complete this preorder?\n\n"
               f"Item: {item_name}\n"
               f"Quantity: {qty}\n"
               f"Total: {format_currency(total)}\n"
               f"Advance: {format_currency(advance_amt)} ({advance_type})\n\n"
               f"This will:\n"
               f"  - Deduct {qty} units from stock\n"
               f"  - Record a sale as {payment_note}\n"
               f"  - Mark preorder as completed")
        if not messagebox.askyesno("Confirm Complete", msg):
            return

        try:
            sale_id, receipt_no = models.complete_preorder(oid)
            self.refresh()
            messagebox.showinfo("Success",
                f"Preorder completed!\n"
                f"Sale ID: {sale_id}\n"
                f"Receipt: {receipt_no}\n\n"
                f"Go to Sales > Update Payment to record payment.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except PermissionError as e:
            messagebox.showerror("Update Required", str(e))

    def _cancel(self):
        oid = self.table.get_selected_key()
        if not oid:
            messagebox.showwarning("No Selection", "Select a preorder to cancel")
            return
        preorder = models.get_preorder(oid)
        if not preorder:
            return
        if preorder.get("Status") != "pending":
            messagebox.showwarning("Cannot Cancel", f"Only pending preorders can be cancelled. Current status: {preorder['Status']}")
            return
        if messagebox.askyesno("Confirm Cancel", "Cancel this preorder?"):
            try:
                models.cancel_preorder(oid)
                self.refresh()
                messagebox.showinfo("Success", "Preorder cancelled")
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def _export(self):
        status = self.status_filter_var.get()
        if status == "all":
            status = ""
        try:
            data = models.get_preorders(search=self.search.get(), status=status)
        except FileNotFoundError:
            data = []
        headers = ["Order ID", "Customer", "Item", "Qty", "Price", "Total",
                   "Delivery Date", "Delivery Address", "Advance Amount",
                   "Advance Type", "Status", "Date"]
        rows = []
        for r in data:
            rows.append([
                r.get("ID"), r.get("customer_name", ""), r.get("item_name", ""),
                r.get("Quantity", 0), r.get("Preorder_Price", 0) or 0,
                r.get("Total", 0) or 0, r.get("Delivery_Date", ""),
                r.get("Delivery_Address", ""),
                r.get("Advance_Amount", 0) or 0,
                r.get("Advance_Payment_Type", "none"),
                r.get("Status", "pending"), r.get("Created_At", "")[:10]])
        export_to_csv(rows, headers, "preorders_export.csv")
