import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from utils.billing import print_bill
from utils.formatters import safe_float
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class SalesPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Sales",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search sales by item or customer")

        ttk.Label(toolbar, text="Status:").pack(side=tk.LEFT, padx=(5, 2))
        self.status_filter_var = tk.StringVar(value="all")
        self.status_filter = ttk.Combobox(toolbar, textvariable=self.status_filter_var,
                                           values=["all", "paid", "unpaid", "partial"],
                                           state="readonly", width=10)
        self.status_filter.pack(side=tk.LEFT)
        ToolTip(self.status_filter, "Filter by payment status")
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(toolbar, text="From:").pack(side=tk.LEFT, padx=(10, 2))
        self.from_var = tk.StringVar()
        self.from_entry = ttk.Entry(toolbar, textvariable=self.from_var, width=12)
        self.from_entry.pack(side=tk.LEFT)
        ToolTip(self.from_entry, "Start date (YYYY-MM-DD)")
        self.from_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ttk.Label(toolbar, text="To:").pack(side=tk.LEFT, padx=(5, 2))
        self.to_var = tk.StringVar()
        self.to_entry = ttk.Entry(toolbar, textvariable=self.to_var, width=12)
        self.to_entry.pack(side=tk.LEFT)
        ToolTip(self.to_entry, "End date (YYYY-MM-DD)")
        self.to_entry.bind("<KeyRelease>", lambda e: self.refresh())

        add_btn = ttk.Button(toolbar, text="New Sale",
                             command=self._new_sale_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Record a new sale")

        payment_btn = ttk.Button(toolbar, text="Update Payment",
                                 command=self._update_payment)
        payment_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(payment_btn, "Update payment status for selected sale")

        return_btn = ttk.Button(toolbar, text="Return Sale",
                                command=self._return_sale)
        return_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(return_btn, "Return sale and restore stock")

        delete_btn = ttk.Button(toolbar, text="Delete",
                                command=self._delete_sale)
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(delete_btn, "Delete selected sale (stock NOT restored)")

        print_btn = ttk.Button(toolbar, text="Print Bill",
                               command=self._print_bill)
        print_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(print_btn, "Print invoice/bill for selected sale")

        export_btn = ttk.Button(toolbar, text="Export CSV",
                                command=self._export)
        export_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(export_btn, "Export sales to CSV file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDCB5",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No sales yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'New Sale' to record your first sale.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Invoice": 115, "Item": 180, "Category": 110,
                "Customer": 150, "Qty": 75, "Price": 95, "Total": 95,
                "Status": 95, "Paid": 95, "Unpaid": 95, "Date": 160}
        aligns = {"Qty": "e", "Price": "e", "Total": "e", "Paid": "e", "Unpaid": "e"}
        self.table = Table(self._container, columns=cols, key_column="ID",
                           on_double_click=self._print_bill, alignments=aligns)

        self.refresh()

    def _fmt_invoice(self, sale):
        sid = sale.get("ID", 0)
        invoice = models.format_invoice_id(sid) if hasattr(models, 'format_invoice_id') else f"#{sid}"
        sale["_invoice"] = invoice

    def refresh(self):
        try:
            all_data = models.get_sales(
                search=self.search.get(),
                from_date=self.from_var.get().strip(),
                to_date=self.to_var.get().strip(),
            )
        except FileNotFoundError:
            all_data = []
        status_filter = self.status_filter_var.get()
        if status_filter != "all":
            all_data = [r for r in all_data if r.get("Payment_Status", "paid") == status_filter]
        display = []
        for r in all_data:
            self._fmt_invoice(r)
            customer_name = r.get("customer_name", "Walk-in Customer")
            payment_status = r.get("Payment_Status", "paid")
            paid = safe_float(r.get("Paid_Amount", 0))
            unpaid = safe_float(r.get("Unpaid_Amount", 0))
            display.append({
                "ID": r.get("ID"),
                "Invoice": r.get("_invoice"),
                "Item": r.get("item_name", ""),
                "Category": r.get("category", ""),
                "Customer": customer_name,
                "Qty": r.get("Quantity_Sold", 0),
                "Price": r.get("Price", 0),
                "Total": r.get("Total", 0),
                "Status": (payment_status or "paid").capitalize(),
                "Paid": f"{paid:.2f}",
                "Unpaid": f"{unpaid:.2f}",
                "Date": r.get("Sale_Date", ""),
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

    def _new_sale_form(self):
        app = self.winfo_toplevel()
        body = app.show_modal("New Sale", width=500, height=530)

        stock_items = models.get_stock_items()
        item_map = {f"{s['Item_Name']} (Qty: {s['Quantity']})": s["ID"]
                    for s in stock_items}
        item_price_map = {f"{s['Item_Name']} (Qty: {s['Quantity']})": s.get("Selling_Price", 0)
                          for s in stock_items}

        customers = models.get_customers()
        customer_map = {"Walk-in Customer": None}
        customer_map.update({f"{c['Name']} ({c['Contact']})": c["ID"] for c in customers})

        ttk.Label(body, text="Item").grid(row=0, column=0, padx=10,
                                          pady=10, sticky="w")
        item_var = tk.StringVar()
        item_combo = ttk.Combobox(body, textvariable=item_var,
                                   values=list(item_map.keys()),
                                   state="normal", width=35)
        item_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        def on_item_select(*args):
            sel = item_var.get()
            if sel in item_price_map:
                price = item_price_map[sel]
                price_entry.delete(0, tk.END)
                price_entry.insert(0, str(price))
                auto_calc()

        item_combo.bind("<<ComboboxSelected>>", on_item_select)

        ttk.Label(body, text="Customer").grid(row=1, column=0, padx=10,
                                              pady=10, sticky="w")
        customer_var = tk.StringVar(value="Walk-in Customer")
        customer_combo = ttk.Combobox(body, textvariable=customer_var,
                                       values=list(customer_map.keys()),
                                       state="normal", width=35)
        customer_combo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Quantity").grid(row=2, column=0, padx=10,
                                              pady=10, sticky="w")
        qty_entry = ttk.Entry(body, width=35)
        qty_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Selling Price").grid(row=3, column=0, padx=10,
                                                   pady=10, sticky="w")
        price_entry = ttk.Entry(body, width=35)
        price_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Total Amount").grid(row=4, column=0, padx=10,
                                                  pady=10, sticky="w")
        total_var = tk.StringVar()
        total_entry = ttk.Entry(body, textvariable=total_var, width=35,
                                 state="readonly")
        total_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Payment Status").grid(row=5, column=0, padx=10,
                                                     pady=10, sticky="w")
        payment_var = tk.StringVar(value="paid")
        payment_combo = ttk.Combobox(body, textvariable=payment_var,
                                      values=["paid", "unpaid", "partial"],
                                      state="readonly", width=33)
        payment_combo.grid(row=5, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Paid Amount").grid(row=6, column=0, padx=10,
                                                  pady=10, sticky="w")
        paid_var = tk.StringVar()
        paid_entry = ttk.Entry(body, textvariable=paid_var, width=35)
        paid_entry.grid(row=6, column=1, padx=10, pady=10, sticky="ew")

        ttk.Label(body, text="Unpaid Amount").grid(row=7, column=0, padx=10,
                                                    pady=10, sticky="w")
        unpaid_var = tk.StringVar()
        unpaid_entry = ttk.Entry(body, textvariable=unpaid_var, width=35,
                                  state="readonly")
        unpaid_entry.grid(row=7, column=1, padx=10, pady=10, sticky="ew")

        def auto_calc(*args):
            try:
                q = float(qty_entry.get() or 0)
                p = float(price_entry.get() or 0)
                total = q * p
                total_var.set(f"{total:.2f}")
                
                # Update payment fields based on status
                status = payment_var.get()
                if status == "paid":
                    paid_var.set(f"{total:.2f}")
                    unpaid_var.set("0.00")
                elif status == "unpaid":
                    paid_var.set("0.00")
                    unpaid_var.set(f"{total:.2f}")
                else:  # partial
                    paid = float(paid_var.get() or 0)
                    unpaid_var.set(f"{max(0, total - paid):.2f}")
            except ValueError:
                total_var.set("")
                paid_var.set("")
                unpaid_var.set("")

        def on_payment_change(*args):
            auto_calc()

        qty_entry.bind("<KeyRelease>", auto_calc)
        price_entry.bind("<KeyRelease>", auto_calc)
        payment_combo.bind("<<ComboboxSelected>>", on_payment_change)
        paid_var.trace_add("write", lambda *args: auto_calc())

        def record():
            selection = item_var.get()
            if not selection or selection not in item_map:
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
                messagebox.showerror("Input Error", "Please enter a valid number for Selling Price.")
                return
            if qty <= 0 or price <= 0:
                messagebox.showerror("Error", "Quantity and Price must be positive numbers")
                return
            
            customer_id = customer_map.get(customer_var.get())
            payment_status = payment_var.get()
            try:
                paid_amount = float(paid_var.get().strip() or 0) if payment_status == "partial" else None
                unpaid_amount = float(unpaid_var.get().strip() or 0) if payment_status == "partial" else None
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for payment amount.")
                return
            
            try:
                sale_id, receipt_no = models.record_sale(item_map[selection], qty, price, 
                                  customer_id=customer_id,
                                  payment_status=payment_status,
                                  paid_amount=paid_amount,
                                  unpaid_amount=unpaid_amount)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            if messagebox.askyesno("Invoice", f"Sale recorded (Receipt: {receipt_no}). Generate invoice?"):
                sale_data = {
                    "id": sale_id,
                    "invoice_id": f"#{sale_id}",
                    "receipt_no": receipt_no,
                    "item_name": selection.split(" (Qty:")[0],
                    "quantity_sold": qty,
                    "price": price,
                    "total": qty * price,
                    "payment_status": payment_status,
                    "paid_amount": paid_amount or qty * price,
                    "unpaid_amount": unpaid_amount or 0,
                    "customer_name": customer_var.get().split(" (")[0],
                    "sale_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                print_bill(sale_data)
            messagebox.showinfo("Success", f"Sale recorded\nReceipt: {receipt_no}")

        ttk.Button(body, text="Record Sale", command=record).grid(
            row=8, column=0, columnspan=2, pady=15)
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

    def _update_payment(self):
        sel = self.table.get_selected_row()
        if not sel:
            messagebox.showwarning("No Selection", "Select a sale to update payment")
            return
        
        sale_id = sel["key"]
        values = sel["values"]
        total = float(values[5] or 0)  # Total column
        current_status = values[7] if len(values) > 7 else "Paid"  # Status column
        current_paid = float(values[8] or 0) if len(values) > 8 else total  # Paid column
        app = self.winfo_toplevel()
        body = app.show_modal("Update Payment", width=400, height=350)
        
        ttk.Label(body, text=f"Sale: {values[0]}").grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        ttk.Label(body, text=f"Total: ₹{total:.2f}").grid(row=1, column=0, columnspan=2, padx=10, pady=5)
        
        ttk.Label(body, text="Payment Status").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        status_var = tk.StringVar(value=current_status.lower())
        status_combo = ttk.Combobox(body, textvariable=status_var, values=["paid", "unpaid", "partial"], state="readonly", width=35)
        status_combo.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        ttk.Label(body, text="Paid Amount").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        paid_var = tk.StringVar(value=f"{current_paid:.2f}")
        paid_entry = ttk.Entry(body, textvariable=paid_var, width=35)
        paid_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        ttk.Label(body, text="Unpaid Amount").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        unpaid_var = tk.StringVar(value=f"{total - current_paid:.2f}")
        unpaid_entry = ttk.Entry(body, textvariable=unpaid_var, width=35)
        unpaid_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        
        def update_fields(*args):
            status = status_var.get()
            if status == "paid":
                paid_var.set(f"{total:.2f}")
                unpaid_var.set("0.00")
                paid_entry.config(state="readonly")
                unpaid_entry.config(state="readonly")
            elif status == "unpaid":
                paid_var.set("0.00")
                unpaid_var.set(f"{total:.2f}")
                paid_entry.config(state="readonly")
                unpaid_entry.config(state="readonly")
            else:  # partial
                paid_entry.config(state="normal")
                unpaid_entry.config(state="normal")
        
        status_var.trace("w", update_fields)
        update_fields()
        
        def save():
            try:
                status = status_var.get()
                paid = float(paid_var.get() or 0)
                unpaid = float(unpaid_var.get() or 0)
                if status == "partial" and (paid < 0 or unpaid < 0 or abs(paid + unpaid - total) > 0.01):
                    messagebox.showerror("Error", "Paid + Unpaid must equal Total")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid amount")
                return
            
            try:
                models.update_sale_payment(sale_id, status, 
                                         paid_amount=paid if status == "partial" else None,
                                         unpaid_amount=unpaid if status == "partial" else None)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Payment updated")
        
        ttk.Button(body, text="Update", command=save).grid(row=5, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

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
            "customer": values[3] if len(values) > 3 else "Walk-in Customer",
            "quantity_sold": values[4] if len(values) > 4 else 0,
            "price": values[5] if len(values) > 5 else 0,
            "total": values[6] if len(values) > 6 else 0,
            "payment_status": values[7] if len(values) > 7 else "Paid",
            "paid": values[8] if len(values) > 8 else 0,
            "unpaid": values[9] if len(values) > 9 else 0,
            "sale_date": values[10] if len(values) > 10 else "",
        }
        print_bill(sale_data)

    def _export(self):
        data = models.get_sales(
            search=self.search.get(),
            from_date=self.from_var.get().strip(),
            to_date=self.to_var.get().strip(),
        )
        headers = ["Invoice", "Item", "Category", "Customer", "Qty", "Price", "Total", "Status", "Paid", "Unpaid", "Date"]
        rows = []
        for r in data:
            self._fmt_invoice(r)
            customer_name = r.get("customer_name", "Walk-in Customer")
            payment_status = (r.get("Payment_Status") or "paid").capitalize()
            paid = safe_float(r.get("Paid_Amount", 0))
            unpaid = safe_float(r.get("Unpaid_Amount", 0))
            rows.append([r["_invoice"], r["item_name"], r["category"], customer_name,
                         r["Quantity_Sold"], r["Price"], r["Total"], payment_status,
                         f"{paid:.2f}", f"{unpaid:.2f}", r["Sale_Date"]])
        export_to_csv(rows, headers, "sales_export.csv")