import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from utils.billing import print_bill
from utils.formatters import format_currency, safe_float
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


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

        edit_btn = ttk.Button(toolbar, text="Edit",
                   command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(edit_btn, "Edit selected customer")

        del_btn = ttk.Button(toolbar, text="Delete",
                   command=self._delete)
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

        cols = {"Name": 200, "Contact": 160, "Address": 260, "Created_At": 160}
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
        body = app.show_modal("Add Customer", width=450, height=250)

        fields = {}
        for i, (label, key) in enumerate([("Name", "name"), ("Contact", "contact"),
                                          ("Address", "address")]):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = ttk.Entry(body, width=40)
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry

        def save():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                models.add_customer(name, fields["contact"].get(), fields["address"].get())
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
            row=3, column=0, columnspan=2, pady=15)
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
        body = app.show_modal("Edit Customer", width=450, height=250)

        fields = {}
        for i, (label, key) in enumerate([("Name", "Name"), ("Contact", "Contact"),
                                          ("Address", "Address")]):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = ttk.Entry(body, width=40)
            entry.insert(0, cust.get(key, "") or "")
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry

        def save():
            name = fields["Name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                models.update_customer(cid, name, fields["Contact"].get(), fields["Address"].get())
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
            row=3, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

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
                    models.add_customer(
                        row.get("Name", row.get("name", "")),
                        row.get("Contact", row.get("contact", "")),
                        row.get("Address", row.get("address", "")),
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
        headers = ["Name", "Contact", "Address", "Created At"]
        rows = [[r["Name"], r["Contact"], r["Address"], r["Created_At"]] for r in data]
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

        total_purchases = len(cust_sales)
        total_spent = sum(safe_float(s.get("Total", 0)) for s in cust_sales)
        total_paid = sum(safe_float(s.get("Paid_Amount", 0)) for s in cust_sales)
        total_unpaid = sum(safe_float(s.get("Unpaid_Amount", 0)) for s in cust_sales)

        ttk.Label(info_frame, text=f"Total Transactions: {total_purchases}").grid(row=1, column=0, sticky="w", padx=5, pady=(5, 0))
        ttk.Label(info_frame, text=f"Total Spent: {format_currency(total_spent)}").grid(row=1, column=1, sticky="w", padx=20, pady=(5, 0))
        ttk.Label(info_frame, text=f"Total Paid: {format_currency(total_paid)}").grid(row=1, column=2, sticky="w", padx=20, pady=(5, 0))
        ttk.Label(info_frame, text=f"Total Unpaid: {format_currency(total_unpaid)}").grid(row=1, column=3, sticky="w", padx=20, pady=(5, 0))

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