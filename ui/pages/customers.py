import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from utils.billing import print_bill
from utils.formatters import format_currency, safe_float
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL, CARD_BG, DANGER_COLOR


class CustomersPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Customers",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search customers by name or contact")

        add_btn = ttk.Button(toolbar, text="Add Customer",
                   command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Add a new customer")

        profile_btn = ttk.Button(toolbar, text="View Profile",
                   command=self._view_profile)
        profile_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(profile_btn, "View customer details and transaction history")

        stmt_btn = ttk.Button(toolbar, text="Statement",
                   command=self._show_statement)
        stmt_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(stmt_btn, "Account statement with running balance for selected customer")

        portal_btn = ttk.Button(toolbar, text="Portal Access",
                   command=self._portal_access)
        portal_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(portal_btn, "Give the customer login to the online Customer Portal and sync their statement")

        edit_btn = ttk.Button(toolbar, text="Edit",
                   command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(edit_btn, "Edit selected customer")

        del_btn = ttk.Button(toolbar, text="Delete",
                   command=self._delete, style="Danger.TButton")
        del_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(del_btn, "Delete selected customer")

        imp_btn = ttk.Button(toolbar, text="Import CSV",
                   command=self._import_csv)
        imp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(imp_btn, "Import customers from CSV file")

        exp_btn = ttk.Button(toolbar, text="Export CSV",
                   command=self._export)
        exp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(exp_btn, "Export customers to CSV file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDC64",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No customers yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'Add Customer' to add one.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Name": 180, "Contact": 140, "Address": 220, "Email": 180,
                "Phone": 130, "Notify_Email": 100, "Notify_WhatsApp": 110,
                "Created_At": 140}
        self.table = Table(self._container, columns=cols, key_column="ID", on_double_click=self._view_profile)

        self.refresh()

    def refresh(self):
        try:
            data = models.get_customers(search=self.search.get())
        except FileNotFoundError:
            data = []
        self.table.populate(data)
        if not data:
            self.table.pack_forget()
            self._empty_state.pack(fill=tk.BOTH, expand=True)
        else:
            self._empty_state.pack_forget()
            self.table.pack(fill=tk.BOTH, expand=True)

    def _on_search(self, text):
        self.refresh()

    def _add_form(self):
        app = self.winfo_toplevel()
        from utils.settings_helper import get_active_customer_field_defs
        cust_defs = get_active_customer_field_defs()
        body = app.show_modal("Add Customer", width=500,
                              height=min(420 + 40 * len(cust_defs), 700))

        fields = {}
        rows = [
            ("Name", "name"),
            ("Contact", "contact"),
            ("Address", "address"),
            ("Email", "email"),
            ("Phone", "phone"),
        ]
        for i, (label, key) in enumerate(rows):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=6, sticky="w")
            entry = ttk.Entry(body, width=44)
            entry.grid(row=i, column=1, padx=10, pady=6, sticky="ew")
            fields[key] = entry

        row = len(rows)
        ttk.Label(body, text="Credit Limit (0 = none)").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        credit_var = tk.StringVar(value="0")
        ttk.Entry(body, textvariable=credit_var, width=14).grid(row=row, column=1, padx=10, pady=6, sticky="w")
        row += 1
        extra_vars = {}
        for _key, d in cust_defs:
            ttk.Label(body, text=d["label"]).grid(row=row, column=0, padx=10, pady=6, sticky="w")
            var = tk.StringVar()
            ttk.Entry(body, textvariable=var, width=44).grid(row=row, column=1, padx=10, pady=6, sticky="ew")
            extra_vars[d["column"]] = var
            row += 1

        notify_email_var = tk.BooleanVar(value=False)
        notify_wa_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Notify via Email",
                        variable=notify_email_var).grid(row=row, column=1, padx=10, pady=4, sticky="w")
        ttk.Checkbutton(body, text="Notify via WhatsApp",
                        variable=notify_wa_var).grid(row=row + 1, column=1, padx=10, pady=4, sticky="w")

        def save():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            extras = {c: v.get().strip() for c, v in extra_vars.items()}
            try:
                extras["Credit_Limit"] = float(credit_var.get().strip() or 0)
            except ValueError:
                messagebox.showerror("Input Error", "Credit Limit must be a number (0 = no limit).")
                return
            try:
                models.add_customer(
                    name,
                    fields["contact"].get(),
                    fields["address"].get(),
                    fields["email"].get().strip(),
                    fields["phone"].get().strip(),
                    notify_email_var.get(),
                    notify_wa_var.get(),
                    extras=extras,
                )
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Customer added")

        ttk.Button(body, text="Save", command=save).grid(
            row=row + 2, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)
        fields["name"].focus()

    def _edit_form(self):
        cid = self.table.get_selected_key()
        if not cid:
            messagebox.showwarning("No Selection", "Select a customer first")
            return
        cust = models.get_customer(cid)
        if not cust:
            return

        app = self.winfo_toplevel()
        from utils.settings_helper import get_active_customer_field_defs
        cust_defs = get_active_customer_field_defs()
        body = app.show_modal("Edit Customer", width=500,
                              height=min(420 + 40 * len(cust_defs), 700))

        fields = {}
        rows = [
            ("Name", "Name"),
            ("Contact", "Contact"),
            ("Address", "Address"),
            ("Email", "Email"),
            ("Phone", "Phone"),
        ]
        for i, (label, key) in enumerate(rows):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=6, sticky="w")
            entry = ttk.Entry(body, width=44)
            entry.insert(0, cust.get(key, "") or "")
            entry.grid(row=i, column=1, padx=10, pady=6, sticky="ew")
            fields[key] = entry

        row = len(rows)
        ttk.Label(body, text="Credit Limit (0 = none)").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        credit_var = tk.StringVar(value=str(cust.get("Credit_Limit", 0) or 0))
        ttk.Entry(body, textvariable=credit_var, width=14).grid(row=row, column=1, padx=10, pady=6, sticky="w")
        row += 1
        extra_vars = {}
        for _key, d in cust_defs:
            ttk.Label(body, text=d["label"]).grid(row=row, column=0, padx=10, pady=6, sticky="w")
            var = tk.StringVar(value=str(cust.get(d["column"], "") or ""))
            w = ttk.Entry(body, textvariable=var, width=44)
            w.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
            extra_vars[d["column"]] = var
            row += 1

        notify_email_var = tk.BooleanVar(value=str(cust.get("Notify_Email", "")).lower() in ("yes", "true", "1"))
        notify_wa_var = tk.BooleanVar(value=str(cust.get("Notify_WhatsApp", "")).lower() in ("yes", "true", "1"))
        ttk.Checkbutton(body, text="Notify via Email",
                        variable=notify_email_var).grid(row=row, column=1, padx=10, pady=4, sticky="w")
        ttk.Checkbutton(body, text="Notify via WhatsApp",
                        variable=notify_wa_var).grid(row=row + 1, column=1, padx=10, pady=4, sticky="w")

        def save():
            name = fields["Name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            extras = {c: v.get().strip() for c, v in extra_vars.items()}
            try:
                extras["Credit_Limit"] = float(credit_var.get().strip() or 0)
            except ValueError:
                messagebox.showerror("Input Error", "Credit Limit must be a number (0 = no limit).")
                return
            try:
                models.update_customer(
                    cid,
                    name,
                    fields["Contact"].get(),
                    fields["Address"].get(),
                    fields["Email"].get().strip(),
                    fields["Phone"].get().strip(),
                    notify_email_var.get(),
                    notify_wa_var.get(),
                    extras=extras,
                )
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Customer updated")

        ttk.Button(body, text="Update", command=save).grid(
            row=row + 2, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _show_statement(self):
        """Account statement: every sale for the customer with running balance."""
        cid = self.table.get_selected_key()
        if not cid:
            messagebox.showwarning("Statement", "Select a customer first")
            return
        cust = models.get_customer(cid)
        if not cust:
            return
        try:
            rows = models.get_customer_statement(cid)
        except (FileNotFoundError, OSError):
            rows = []

        app = self.winfo_toplevel()
        name = cust.get("Name", f"Customer #{cid}")
        body = app.show_modal(f"Account Statement — {name}", width=820, height=520)

        credit_limit = safe_float(cust.get("Credit_Limit", 0))
        total_due = safe_float(rows[-1]["running_balance"]) if rows else 0.0

        head = tk.Frame(body, bg=CARD_BG)
        head.pack(fill=tk.X, pady=(0, 8))
        tk.Label(head, text=f"{name}", font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack(side=tk.LEFT)
        info = f"Total billed: {format_currency(sum(safe_float(r.get('Total', 0)) for r in rows))}   |   " \
               f"Balance due: {format_currency(total_due)}"
        if credit_limit > 0:
            info += f"   |   Credit limit: {format_currency(credit_limit)}"
        tk.Label(head, text=info, font=(FONT_FAMILY, FONT_SIZE_MD),
                 bg=CARD_BG,
                 fg=(DANGER_COLOR if (credit_limit > 0 and total_due > credit_limit) else TEXT_SECONDARY)
                 ).pack(side=tk.LEFT, padx=(14, 0))
        if credit_limit > 0 and total_due > credit_limit:
            tk.Label(body, text="⚠  Customer is OVER their credit limit!",
                     font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
                     bg=CARD_BG, fg=DANGER_COLOR).pack(anchor="w", pady=(0, 6))

        if not rows:
            tk.Label(body, text="No sales recorded for this customer yet.",
                     font=(FONT_FAMILY, FONT_SIZE_MD), bg=CARD_BG,
                     fg=TEXT_SECONDARY).pack(pady=24)
            return

        cols = ("date", "receipt", "item", "qty", "total", "paid", "balance", "status")
        tree = ttk.Treeview(body, columns=cols, show="headings", height=15)
        for col, txt, w, anchor in [("date", "Date", 95, "center"),
                                    ("receipt", "Receipt", 100, "w"),
                                    ("item", "Item", 190, "w"),
                                    ("qty", "Qty", 50, "e"),
                                    ("total", "Total", 90, "e"),
                                    ("paid", "Paid", 90, "e"),
                                    ("balance", "Balance", 100, "e"),
                                    ("status", "Status", 75, "center")]:
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor=anchor)
        scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for r in rows:
            tree.insert("", tk.END, values=(
                str(r.get("Sale_Date") or "")[:10],
                r.get("Receipt_No", ""),
                r.get("item_name", ""),
                r.get("Quantity_Sold", 0),
                format_currency(r.get("Total", 0)),
                format_currency(r.get("Paid_Amount", 0)),
                format_currency(r.get("running_balance", 0)),
                (r.get("Payment_Status") or "paid").capitalize(),
            ), tags=("due",) if safe_float(r.get("Unpaid_Amount", 0)) > 0 else ())
        tree.tag_configure("due", foreground="#DC2626")

        def _export_stmt():
            headers = ["Date", "Receipt", "Item", "Qty", "Total", "Paid", "Balance", "Status"]
            data = [[str(r.get("Sale_Date") or "")[:10], r.get("Receipt_No", ""),
                     r.get("item_name", ""), r.get("Quantity_Sold", 0),
                     safe_float(r.get("Total", 0)), safe_float(r.get("Paid_Amount", 0)),
                     r.get("running_balance", 0),
                     (r.get("Payment_Status") or "paid")] for r in rows]
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            export_to_csv(data, headers, f"statement_{safe_name}.csv")

        btn_row = tk.Frame(body, bg=CARD_BG)
        btn_row.pack(anchor="w", pady=(8, 0))
        ttk.Button(btn_row, text="Export CSV", command=_export_stmt).pack(side=tk.LEFT)

    def _portal_access(self):
        """Invite the selected customer to the online portal (or re-sync /
        reset their PIN if already invited)."""
        cid = self.table.get_selected_key()
        if not cid:
            messagebox.showwarning("Portal Access", "Select a customer first")
            return
        cust = models.get_customer(cid)
        if not cust:
            return
        from utils import portal
        from utils.feature_gate import require_feature
        if not require_feature("customer_notifications", parent=self,
                               friendly_name="Customer Portal"):
            return
        if not portal.portal_enabled():
            messagebox.showinfo("Portal Access",
                                "The customer portal is disabled — enable it in "
                                "Settings → Notifications.")
            return
        if not portal.is_licensed_for_portal():
            messagebox.showinfo("Portal Access",
                                "Activate a license first (Settings → License).")
            return

        enabled = str(cust.get("Portal_Enabled", "")).strip().lower() in ("yes", "true", "1")
        from tkinter import simpledialog
        pin = simpledialog.askstring(
            "Portal PIN",
            ("PIN for the customer to log in with their phone number.\n"
             "Leave blank to auto-generate a 6-digit PIN.")
            + ("\n\n(They already have portal access — a new PIN will REPLACE the old one.)"
               if enabled else ""),
            parent=self)
        if pin is None:
            return  # cancelled
        pin = pin.strip()
        if pin and not (4 <= len(pin) <= 6 and pin.isdigit()):
            messagebox.showerror("Portal PIN", "PIN must be 4-6 digits.")
            return

        def _invite():
            ok, msg, used_pin = portal.invite_customer(cust, pin or None)
            if not ok:
                self.after(0, lambda: messagebox.showerror("Portal Invite", msg))
                return
            # Mark the customer as portal-enabled and push their first snapshot.
            try:
                models.update_customer(
                    cust["ID"], cust.get("Name", ""), cust.get("Contact", ""),
                    cust.get("Address", ""), cust.get("Email", "") or "",
                    cust.get("Phone", "") or "",
                    str(cust.get("Notify_Email", "")).lower() in ("yes", "true", "1"),
                    str(cust.get("Notify_WhatsApp", "")).lower() in ("yes", "true", "1"),
                    extras={"Portal_Enabled": "Yes",
                            "Credit_Limit": cust.get("Credit_Limit", 0) or 0,
                            "Doctor_Name": cust.get("Doctor_Name", "") or "",
                            "Prescription_No": cust.get("Prescription_No", "") or "",
                            "Measurements": cust.get("Measurements", "") or "",
                            "Table_No": cust.get("Table_No", "") or ""},
                )
            except Exception:
                pass
            portal.sync_customer(cust)
            self.after(0, lambda: self._show_portal_share(cust, used_pin))

        import threading
        threading.Thread(target=_invite, daemon=True).start()

    def _show_portal_share(self, cust, pin):
        """Show the credentials and one-click share buttons."""
        from utils import portal, notifier
        app = self.winfo_toplevel()
        text = portal.build_share_text(cust, pin)
        body = app.show_modal(f"Portal Access — {cust.get('Name','')}", width=560, height=330)
        tk.Label(body, text="Share these login details with the customer:",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=CARD_BG, fg=TEXT_SECONDARY
                 ).pack(anchor="w", pady=(0, 8))
        txt = tk.Text(body, height=8, width=62, font=(FONT_FAMILY, 10))
        txt.insert("1.0", text)
        txt.config(state="disabled")
        txt.pack(fill=tk.X)

        btn_row = tk.Frame(body, bg=CARD_BG)
        btn_row.pack(anchor="w", pady=(10, 0))

        def _copy():
            app.clipboard_clear()
            app.clipboard_append(text)
            try:
                app.toast.show("Credentials copied", "success", 2500)
            except Exception:
                pass

        def _wa():
            ok, msg = notifier.send_whatsapp(
                to_phone=str(cust.get("Phone", "") or cust.get("Contact", "")),
                message=text)
            try:
                app.toast.show(msg, "success" if ok else "error", 4000)
            except Exception:
                pass

        def _email():
            to = str(cust.get("Email", "") or "").strip()
            if not to:
                messagebox.showinfo("Email", "Customer has no email address.")
                return
            ok, msg = notifier.send_email(
                to_email=to,
                subject=f"Your customer portal login — {cust.get('Name','')}",
                body_text=text)
            try:
                app.toast.show(msg, "success" if ok else "error", 4000)
            except Exception:
                pass

        ttk.Button(btn_row, text="📋  Copy", command=_copy).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="🟢  WhatsApp", command=_wa).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="✉  Email", command=_email).pack(side=tk.LEFT)

    def _delete(self):
        cid = self.table.get_selected_key()
        if not cid:
            messagebox.showwarning("No Selection", "Select a customer first")
            return
        if messagebox.askyesno("Confirm", "Delete this customer?"):
            try:
                models.delete_customer(cid)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.refresh()

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        import csv
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    def _flag(*keys):
                        for k in keys:
                            v = row.get(k, "")
                            if str(v).strip().lower() in ("yes", "true", "1"):
                                return True
                            if str(v).strip().lower() in ("no", "false", "0"):
                                return False
                        return False
                    models.add_customer(
                        row.get("Name", row.get("name", "")),
                        row.get("Contact", row.get("contact", "")),
                        row.get("Address", row.get("address", "")),
                        row.get("Email", row.get("email", "")),
                        row.get("Phone", row.get("phone", "")),
                        _flag("Notify_Email", "notify_email"),
                        _flag("Notify_WhatsApp", "notify_whatsapp"),
                    )
                    count += 1
            self.refresh()
            messagebox.showinfo("Import", f"Imported {count} customers")
        except PermissionError as e:
            messagebox.showerror("Update Required", str(e))
        except (FileNotFoundError, PermissionError, OSError, ValueError) as e:
            messagebox.showerror("Import Error", str(e))

    def _export(self):
        data = models.get_customers()
        headers = ["Name", "Contact", "Address", "Email", "Phone",
                   "Notify_Email", "Notify_WhatsApp", "Created At"]
        rows = [[r.get("Name", ""), r.get("Contact", ""), r.get("Address", ""),
                 r.get("Email", ""), r.get("Phone", ""),
                 r.get("Notify_Email", ""), r.get("Notify_WhatsApp", ""),
                 r.get("Created_At", "")] for r in data]
        export_to_csv(rows, headers, "customers_export.csv")

    def _view_profile(self):
        cid = self.table.get_selected_key()
        if not cid:
            messagebox.showwarning("No Selection", "Select a customer first")
            return
        cust = models.get_customer(cid)
        if not cust:
            return

        try:
            sales = models.get_sales()
        except FileNotFoundError:
            sales = []
        cust_sales = [s for s in sales if s.get("Customer_ID") == cid]

        app = self.winfo_toplevel()
        body = app.show_modal(f"Customer Profile - {cust['Name']}", width=850, height=600)

        # Info section
        info_frame = ttk.LabelFrame(body, text="Customer Details", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(info_frame, text=f"Name: {cust.get('Name', '')}", font=(FONT_FAMILY, 12, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, text=f"Contact: {cust.get('Contact', 'N/A')}").grid(row=0, column=1, sticky="w", padx=20)
        ttk.Label(info_frame, text=f"Address: {cust.get('Address', 'N/A')}").grid(row=0, column=2, sticky="w", padx=20)
        ttk.Label(info_frame, text=f"Email: {cust.get('Email') or 'N/A'}").grid(row=1, column=0, sticky="w", padx=5, pady=(5, 0))
        ttk.Label(info_frame, text=f"Phone: {cust.get('Phone') or 'N/A'}").grid(row=1, column=1, sticky="w", padx=20, pady=(5, 0))
        notify_flags = []
        if str(cust.get("Notify_Email", "")).lower() in ("yes", "true", "1"):
            notify_flags.append("Email")
        if str(cust.get("Notify_WhatsApp", "")).lower() in ("yes", "true", "1"):
            notify_flags.append("WhatsApp")
        notify_text = "Notify: " + (", ".join(notify_flags) if notify_flags else "None")
        ttk.Label(info_frame, text=notify_text).grid(row=1, column=2, sticky="w", padx=20, pady=(5, 0))

        total_purchases = len(cust_sales)
        total_spent = sum(safe_float(s.get("Total", 0)) for s in cust_sales)
        total_paid = sum(safe_float(s.get("Paid_Amount", 0)) for s in cust_sales)
        total_unpaid = sum(safe_float(s.get("Unpaid_Amount", 0)) for s in cust_sales)

        ttk.Label(info_frame, text=f"Total Transactions: {total_purchases}").grid(row=2, column=0, sticky="w", padx=5, pady=(5, 0))
        ttk.Label(info_frame, text=f"Total Spent: {format_currency(total_spent)}").grid(row=2, column=1, sticky="w", padx=20, pady=(5, 0))
        ttk.Label(info_frame, text=f"Total Paid: {format_currency(total_paid)}").grid(row=2, column=2, sticky="w", padx=20, pady=(5, 0))
        ttk.Label(info_frame, text=f"Total Unpaid: {format_currency(total_unpaid)}").grid(row=2, column=3, sticky="w", padx=20, pady=(5, 0))

        # Transactions section
        trans_frame = ttk.LabelFrame(body, text="Transaction History", padding=10)
        trans_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        cols = ["Invoice", "Item", "Qty", "Price", "Total", "Status", "Paid", "Unpaid", "Date"]
        tree = ttk.Treeview(trans_frame, columns=cols, show="headings", height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=90, anchor="center")
        tree.column("Item", width=150, anchor="w")
        tree.column("Invoice", width=100)

        scroll = ttk.Scrollbar(trans_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        try:
            stock = {r["ID"]: r for r in models.get_stock_items()}
        except FileNotFoundError:
            stock = {}

        def open_invoice():
            sel = tree.selection()
            if not sel:
                return
            values = tree.item(sel[0], "values")
            sale_id = None
            for s in cust_sales:
                invoice = models.format_invoice_id(s.get("ID", 0))
                if invoice == values[0]:
                    sale_id = s.get("ID")
                    break
            if not sale_id:
                sale_id = values[0].replace("INV-", "").lstrip("0")
                try:
                    sale_id = int(sale_id)
                except ValueError:
                    return
            sale_data = next((s for s in cust_sales if s.get("ID") == sale_id), None)
            if sale_data:
                item_data = stock.get(sale_data.get("Stock_ID"), {})
                print_data = {
                    "id": sale_id,
                    "invoice_id": values[0],
                    "receipt_no": sale_data.get("Receipt_No", ""),
                    "item_name": values[1],
                    "quantity_sold": values[2],
                    "price": values[3],
                    "total": values[4],
                    "payment_status": values[5].lower(),
                    "paid_amount": float(values[6] or 0),
                    "unpaid_amount": float(values[7] or 0),
                    "customer_name": cust.get("Name", ""),
                    "sale_date": values[8],
                }
                print_bill(print_data)

        tree.bind("<Double-1>", lambda e: open_invoice())

        for s in cust_sales:
            item = stock.get(s.get("Stock_ID"), {})
            tree.insert("", tk.END, values=(
                models.format_invoice_id(s.get("ID", 0)),
                item.get("Item_Name", "Unknown"),
                s.get("Quantity_Sold", 0),
                format_currency(s.get("Price", 0)),
                format_currency(s.get("Total", 0)),
                (s.get("Payment_Status") or "paid").capitalize(),
                format_currency(s.get("Paid_Amount", 0)),
                format_currency(s.get("Unpaid_Amount", 0)),
                s.get("Sale_Date", ""),
            ))

        # Export button
        btn_frame = ttk.Frame(body)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def export_transactions():
            headers = ["Invoice", "Item", "Qty", "Price", "Total", "Status", "Paid", "Unpaid", "Date"]
            rows = []
            for s in cust_sales:
                item = stock.get(s.get("Stock_ID"), {})
                rows.append([
                    models.format_invoice_id(s.get("ID", 0)),
                    item.get("Item_Name", "Unknown"),
                    s.get("Quantity_Sold", 0),
                    s.get("Price", 0),
                    s.get("Total", 0),
                    s.get("Payment_Status", "paid"),
                    s.get("Paid_Amount", 0),
                    s.get("Unpaid_Amount", 0),
                    s.get("Sale_Date", ""),
                ])
            export_to_csv(rows, headers, f"customer_{cust['Name']}_transactions.csv")

        ttk.Button(btn_frame, text="Export Transactions", command=export_transactions).pack(side=tk.RIGHT)
        ttk.Label(btn_frame, text="Double-click a transaction to view invoice").pack(side=tk.LEFT)