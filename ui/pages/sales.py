import tkinter as tk
import os
from datetime import datetime
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from utils.billing import print_bill
from utils.formatters import safe_float
from utils.settings_helper import is_feature_enabled, get_current_vertical
from config import FONT_FAMILY, BG_COLOR, CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_SIZE_MD, FONT_SIZE_XL


class SalesPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._app = self.winfo_toplevel()
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Sales",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        # Optional vertical-specific panel (Coffee Shop / Restaurant)
        if is_feature_enabled("table_orders"):
            self._build_table_panel()

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

        remind_btn = ttk.Button(toolbar, text="\u2709  Remind",
                                command=self._send_reminder)
        remind_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(remind_btn, "Send a payment reminder to the customer of the selected sale")

        return_btn = ttk.Button(toolbar, text="Return Sale",
                                command=self._return_sale)
        return_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(return_btn, "Return sale and restore stock")

        delete_btn = ttk.Button(toolbar, text="Delete",
                                command=self._delete_sale, style="Danger.TButton")
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(delete_btn, "Delete selected sale (stock NOT restored)")

        print_btn = ttk.Button(toolbar, text="Print Bill",
                               command=self._print_bill)
        print_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(print_btn, "Print invoice/bill for selected sale")

        pdf_btn = ttk.Button(toolbar, text="Invoice PDF",
                             command=self._invoice_pdf)
        pdf_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(pdf_btn, "Save a professional PDF invoice for the selected sale")

        email_btn = ttk.Button(toolbar, text="\u2709  Email Invoice",
                               command=self._email_invoice)
        email_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(email_btn, "Email the PDF invoice to the customer (needs opt-in + SMTP setup)")

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

    def _build_table_panel(self):
        panel = tk.Frame(self, bg=CARD_BG, highlightbackground="#CBD5E1",
                         highlightthickness=1)
        panel.pack(fill=tk.X, padx=20, pady=(0, 10))

        vertical = get_current_vertical()
        title = "☕ Coffee Shop / Cafe" if vertical == "coffee_shop" else "🍽️ Restaurant Tables"
        tk.Label(panel, text=title, font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w", padx=12, pady=(10, 4))

        row = tk.Frame(panel, bg=CARD_BG)
        row.pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Label(row, text="Table No.:", font=(FONT_FAMILY, FONT_SIZE_MD),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        self._table_no_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._table_no_var, width=8).pack(side=tk.LEFT, padx=(6, 12))

        tk.Label(row, text="Order Type:", font=(FONT_FAMILY, FONT_SIZE_MD),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        self._order_type_var = tk.StringVar(value="Dine-In")
        ttk.Combobox(row, textvariable=self._order_type_var,
                     values=["Dine-In", "Takeaway", "Delivery"],
                     state="readonly", width=12).pack(side=tk.LEFT, padx=(6, 12))

        if is_feature_enabled("kot"):
            tk.Button(row, text="🖨  Print KOT", font=(FONT_FAMILY, 10, "bold"),
                      bg="#D97706", fg="white", bd=0, padx=12, pady=4,
                      cursor="hand2",
                      command=self._print_kot).pack(side=tk.RIGHT, padx=4)
        if is_feature_enabled("quick_billing"):
            tk.Button(row, text="⚡ Quick Bill", font=(FONT_FAMILY, 10, "bold"),
                      bg="#059669", fg="white", bd=0, padx=12, pady=4,
                      cursor="hand2",
                      command=self._quick_bill).pack(side=tk.RIGHT, padx=4)

        # Open tables overview
        if is_feature_enabled("table_orders"):
            tables_frame = tk.Frame(panel, bg=CARD_BG)
            tables_frame.pack(fill=tk.X, padx=12, pady=(0, 10))
            tk.Label(tables_frame, text="Quick-pick table:", font=(FONT_FAMILY, 9),
                     bg=CARD_BG, fg=TEXT_MUTED).pack(side=tk.LEFT)
            for t in ["T1", "T2", "T3", "T4", "T5", "T6", "Takeaway"]:
                b = tk.Button(tables_frame, text=t, font=(FONT_FAMILY, 9, "bold"),
                              bg="#EFF6FF", fg="#1D4ED8", bd=0, padx=10, pady=2,
                              cursor="hand2",
                              command=lambda v=t: self._table_no_var.set(v))
                b.pack(side=tk.LEFT, padx=2)

    def _print_kot(self):
        table = self._table_no_var.get().strip() or "—"
        order_type = self._order_type_var.get()
        try:
            from utils.billing import print_bill
            sale_data = {
                "id": f"KOT-{table}-{datetime.now().strftime('%H%M%S')}",
                "Invoice_No": f"KOT-{table}",
                "Customer_Name": f"{order_type} · Table {table}",
                "Sale_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Items": [{"name": "(items added in cart)", "qty": 1, "price": 0}],
                "Subtotal": 0,
                "Tax_Amount": 0,
                "Total": 0,
                "is_kot": True,
            }
            print_bill(sale_data)
            # Use a non-blocking toast instead of a modal messagebox so the user
            # doesn't confuse the OK button with the main-window X.
            try:
                self._app.toast.show(f"KOT opened for Table {table}",
                                     "success", 2500)
            except Exception:
                pass
        except Exception as exc:
            try:
                self._app.toast.show(f"KOT failed: {exc}", "error", 4000)
            except Exception:
                pass

    def _quick_bill(self):
        table = self._table_no_var.get().strip() or "Walk-in"
        order_type = self._order_type_var.get()
        try:
            self._app.toast.show(
                f"Quick-bill mode for Table {table} ({order_type}). "
                f"Add items via 'New Sale'.", "info", 3000)
        except Exception:
            pass

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

        def _stock_label(s):
            name = s.get("Item_Name", "")
            cat = s.get("Category", "")
            qty = s.get("Quantity", 0)
            if cat:
                return f"{name} - {cat} (Qty: {qty})"
            return f"{name} (Qty: {qty})"

        item_map = {_stock_label(s): s["ID"] for s in stock_items}
        item_price_map = {_stock_label(s): s.get("Selling_Price", 0)
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

        # Weight-based pricing (kirana/grocery): enter grams -> qty in units.
        weight_entry = None
        if is_feature_enabled("weight_pricing"):
            ttk.Label(body, text="Weight (g)").grid(row=2, column=2, padx=(6, 2),
                                                    pady=10, sticky="w")
            weight_entry = ttk.Entry(body, width=10)
            weight_entry.grid(row=2, column=3, padx=(0, 6), pady=10, sticky="w")

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
            # Weight-based pricing: grams typed -> qty auto-computed in units
            if weight_entry is not None and weight_entry.get().strip():
                try:
                    g = float(weight_entry.get())
                    if g > 0:
                        qty_entry.delete(0, tk.END)
                        qty_entry.insert(0, f"{round(g / 1000, 3):g}")
                except (ValueError, TypeError):
                    pass
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
        if weight_entry is not None:
            weight_entry.bind("<KeyRelease>", auto_calc)

        def record():
            selection = item_var.get()
            if not selection or selection not in item_map:
                messagebox.showerror("Error", "Select a valid item")
                return
            try:
                qty = float(qty_entry.get().strip())
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

            # Drug schedule verification (pharmacy): H/H1/X items need a
            # prescription check before the sale is recorded.
            if is_feature_enabled("schedule_tracking"):
                try:
                    _item = models.get_stock_item(item_map[selection])
                    _sched = str((_item or {}).get("Drug_Schedule", "")).strip().upper()
                    if _sched in ("H", "H1", "X"):
                        if not messagebox.askyesno(
                                f"Schedule {_sched} Item",
                                f"{selection.split(' (Qty:')[0]} is a Schedule {_sched} drug.\n\n"
                                "Dispense only after verifying the prescription. Continue?"):
                            return
                except (FileNotFoundError, OSError):
                    pass

            payment_status = payment_var.get()
            try:
                paid_amount = float(paid_var.get().strip() or 0) if payment_status == "partial" else None
                unpaid_amount = float(unpaid_var.get().strip() or 0) if payment_status == "partial" else None
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for payment amount.")
                return

            # Soft credit-limit check (customer with a configured limit)
            if customer_id:
                try:
                    _cust = models.get_customer(customer_id)
                    _limit = safe_float((_cust or {}).get("Credit_Limit", 0))
                    if _limit > 0:
                        _total = qty * price
                        _this_unpaid = (0.0 if payment_status == "paid"
                                        else _total if payment_status == "unpaid"
                                        else (unpaid_amount if unpaid_amount is not None
                                              else max(0.0, _total - (paid_amount or 0))))
                        _new_due = models.get_customer_due(customer_id) + _this_unpaid
                        if _new_due > _limit:
                            if not messagebox.askyesno(
                                    "Credit Limit Exceeded",
                                    f"This sale takes {customer_var.get().split(' (')[0]}'s outstanding "
                                    f"to {_new_due:,.2f}, over the credit limit of {_limit:,.2f}.\n\n"
                                    "Record the sale anyway?"):
                                return
                except (FileNotFoundError, OSError, ValueError):
                    pass
            
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
            total_amt = qty * price
            if payment_status == "paid":
                s_paid, s_unpaid = total_amt, 0.0
            elif payment_status == "unpaid":
                s_paid, s_unpaid = 0.0, total_amt
            else:
                s_paid = paid_amount or 0.0
                s_unpaid = unpaid_amount if unpaid_amount is not None else max(0.0, total_amt - s_paid)
            self._maybe_notify_sale(customer_id, {
                "receipt_no": receipt_no,
                "item_name": selection.split(" (Qty:")[0],
                "quantity_sold": qty,
                "price": price,
                "total": total_amt,
                "payment_status": payment_status,
                "paid_amount": s_paid,
                "unpaid_amount": s_unpaid,
                "sale_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
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

    def _maybe_notify_sale(self, customer_id, sale_data):
        """Fire post-sale email/WhatsApp notifications per settings + customer
        opt-in. Fully non-blocking (daemon thread), silent no-op when the
        feature is off, unconfigured, or the customer hasn't opted in."""
        try:
            if not customer_id:
                return
            from utils import notifier
            from utils.license import license_mgr
            customer = models.get_customer(customer_id)
            if not customer:
                return
            opted_email = str(customer.get("Notify_Email", "")).strip().lower() in ("yes", "true", "1")
            opted_wa = str(customer.get("Notify_WhatsApp", "")).strip().lower() in ("yes", "true", "1")
            portal_on = str(customer.get("Portal_Enabled", "")).strip().lower() in ("yes", "true", "1")
            if not (opted_email or opted_wa or portal_on):
                return
            notify_ok = (notifier.notifications_enabled()
                         and license_mgr.has_feature("sale_notifications"))
            import threading

            def _run():
                results = notifier.notify_after_sale(customer, sale_data) if notify_ok else []
                try:
                    from utils import portal
                    portal.sync_after_sale(customer)
                except Exception:
                    pass
                if not results:
                    return
                def _done():
                    for channel, ok, msg in results:
                        try:
                            self._app.toast.show(f"{channel.capitalize()}: {msg}",
                                                 "success" if ok else "warning", 4500)
                        except Exception:
                            pass
                self.after(0, _done)

            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            pass

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

    def _send_reminder(self):
        """Send a payment reminder for the selected unpaid/partial sale."""
        sale = self._selected_sale()
        if not sale:
            messagebox.showwarning("Send Reminder", "Select a sale row first.")
            return
        due = safe_float(sale.get("Unpaid_Amount", 0))
        if due <= 0:
            messagebox.showinfo("Send Reminder", "This sale is fully paid — nothing to remind.")
            return
        customer_id = sale.get("Customer_ID")
        if not customer_id:
            messagebox.showinfo("Send Reminder",
                                "This is a walk-in sale with no customer attached.")
            return
        customer = models.get_customer(customer_id)
        import threading

        def _run():
            from utils import notifier
            results = notifier.send_payment_reminder(customer, due, [sale])
            def _done():
                any_ok = any(ok for _, ok, _ in results)
                for channel, ok, msg in results:
                    try:
                        self._app.toast.show(f"{channel.capitalize()}: {msg}",
                                             "success" if ok else "warning", 5000)
                    except Exception:
                        pass
                if not any_ok:
                    messagebox.showinfo("Send Reminder",
                                        results[0][2] if results else "Nothing sent.")
            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

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

    def _selected_sale(self):
        """Full stored record for the currently selected table row."""
        sel = self.table.get_selected_row()
        if not sel:
            return None
        sale_id = sel["key"]
        try:
            return next((s for s in models.get_sales() if s.get("ID") == sale_id), None)
        except (FileNotFoundError, OSError):
            return None

    @staticmethod
    def _sale_to_invoice_data(sale):
        sid = sale.get("ID", 0)
        invoice = models.format_invoice_id(sid) if hasattr(models, "format_invoice_id") else f"#{sid}"
        total = safe_float(sale.get("Total", 0))
        return {
            "id": sid,
            "invoice_id": invoice,
            "receipt_no": sale.get("Receipt_No", ""),
            "item_name": sale.get("item_name", ""),
            "category": sale.get("category", ""),
            "quantity_sold": sale.get("Quantity_Sold", 0),
            "price": safe_float(sale.get("Price", 0)),
            "total": total,
            "payment_status": sale.get("Payment_Status", "paid"),
            "paid_amount": safe_float(sale.get("Paid_Amount", total)),
            "unpaid_amount": safe_float(sale.get("Unpaid_Amount", 0)),
            "customer_name": sale.get("customer_name", "Walk-in Customer"),
            "sale_date": sale.get("Sale_Date", ""),
        }

    def _invoice_pdf(self):
        sale = self._selected_sale()
        if not sale:
            messagebox.showwarning("Invoice PDF", "Select a sale first.")
            return
        from utils.pdf_export import export_sale_invoice, HAVE_REPORTLAB
        if not HAVE_REPORTLAB:
            messagebox.showwarning("Invoice PDF",
                                   "ReportLab is not installed. Run: pip install reportlab")
            return
        sale_data = self._sale_to_invoice_data(sale)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(sale_data["invoice_id"]))
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Save Invoice PDF",
            defaultextension=".pdf",
            initialfile=f"invoice_{safe_id}.pdf",
            filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        ok, msg = export_sale_invoice(sale_data, path)
        if ok:
            try:
                os.startfile(path)
            except OSError:
                pass
            try:
                self._app.toast.show("Invoice PDF saved", "success", 3000)
            except Exception:
                pass
        else:
            messagebox.showerror("Invoice PDF", msg)

    def _email_invoice(self):
        """Generate the invoice PDF and email it to the sale's customer."""
        sale = self._selected_sale()
        if not sale:
            messagebox.showwarning("Email Invoice", "Select a sale first.")
            return
        customer_id = sale.get("Customer_ID")
        if not customer_id:
            messagebox.showinfo("Email Invoice", "Walk-in sale — no customer email on file.")
            return
        customer = models.get_customer(customer_id)
        if not customer:
            messagebox.showinfo("Email Invoice", "Customer record not found.")
            return
        to_email = str(customer.get("Email", "") or "").strip()
        if not to_email:
            messagebox.showinfo("Email Invoice",
                                "Customer has no email address. Edit the customer first.")
            return
        if str(customer.get("Notify_Email", "")).strip().lower() not in ("yes", "true", "1"):
            messagebox.showinfo("Email Invoice",
                                "Customer has not opted in to email notifications.")
            return
        from utils import notifier
        if not notifier.is_email_configured():
            messagebox.showinfo("Email Invoice",
                                "SMTP is not configured. Go to Settings → Notifications first.")
            return
        from utils.feature_gate import require_feature
        if not require_feature("email_invoicing", parent=self, friendly_name="Email Invoices"):
            return
        from utils.pdf_export import export_sale_invoice, HAVE_REPORTLAB
        if not HAVE_REPORTLAB:
            messagebox.showwarning("Email Invoice",
                                   "ReportLab is not installed. Run: pip install reportlab")
            return

        sale_data = self._sale_to_invoice_data(sale)
        customer_name = str(customer.get("Name", "") or "")
        import threading

        def _run():
            import tempfile
            pdf_path = os.path.join(tempfile.gettempdir(),
                                    f"invoice_{sale_data['id']}_{datetime.now():%Y%m%d%H%M%S}.pdf")
            ok, msg = export_sale_invoice(sale_data, pdf_path)
            if ok:
                body = notifier.build_sale_receipt_text(sale_data, customer_name)
                ok, msg = notifier.send_email_gated(
                    feature_id="email_invoicing",
                    to_email=to_email,
                    subject=f"Invoice {sale_data.get('invoice_id', '')} — {customer_name or 'Sale'}",
                    body_text=body + "\n\n(Full invoice attached as PDF.)",
                    attachment_path=pdf_path,
                    attachment_filename=f"invoice_{sale_data.get('receipt_no', sale_data['id'])}.pdf",
                )
            try:
                os.remove(pdf_path)
            except OSError:
                pass
            def _done():
                try:
                    self._app.toast.show(msg, "success" if ok else "error", 5000)
                except Exception:
                    pass
                if not ok:
                    messagebox.showerror("Email Invoice", msg)
            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()
        try:
            self._app.toast.show("Sending invoice email…", "info", 2500)
        except Exception:
            pass

    def _print_bill(self):
        sel = self.table.get_selected_row()
        if not sel:
            messagebox.showwarning("No Selection", "Select a sale to print")
            return
        values = sel["values"]
        inv = values[0] if values else f"#{sel['key']}"
        if not messagebox.askyesno("Print Invoice",
                                   f"Open invoice {inv} in your browser for printing?\n\n"
                                   "(This launches the default browser.)"):
            return
        sale_data = {
            "id": sel["key"],
            "invoice_id": inv,
            "item_name": values[1] if len(values) > 1 else "",
            "category": values[2] if len(values) > 2 else "",
            "customer_name": values[3] if len(values) > 3 else "Walk-in Customer",
            "quantity_sold": values[4] if len(values) > 4 else 0,
            "price": values[5] if len(values) > 5 else 0,
            "total": values[6] if len(values) > 6 else 0,
            "payment_status": values[7] if len(values) > 7 else "Paid",
            "paid_amount": values[8] if len(values) > 8 else 0,
            "unpaid_amount": values[9] if len(values) > 9 else 0,
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