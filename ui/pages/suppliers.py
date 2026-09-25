import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from config import FONT_FAMILY, CARD_BG, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class SuppliersPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Suppliers",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search suppliers by name, contact, or address")

        add_btn = ttk.Button(toolbar, text="Add Supplier",
                   command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Add a new supplier (Ctrl+N)")

        edit_btn = ttk.Button(toolbar, text="Edit",
                   command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(edit_btn, "Edit selected supplier")

        del_btn = ttk.Button(toolbar, text="Delete",
                   command=self._delete)
        del_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(del_btn, "Delete selected supplier")

        imp_btn = ttk.Button(toolbar, text="Import CSV",
                   command=self._import_csv)
        imp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(imp_btn, "Import suppliers from CSV file")

        exp_btn = ttk.Button(toolbar, text="Export CSV",
                   command=self._export)
        exp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(exp_btn, "Export suppliers to CSV file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDC65",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No suppliers yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'Add Supplier' to add one.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Name": 180, "Contact": 140, "Address": 220, "Email": 180,
                "Phone": 130, "Notify_Email": 100, "Notify_WhatsApp": 110,
                "Created_At": 140}
        self.table = Table(self._container, columns=cols, key_column="ID", on_double_click=self._edit_form)

        self.refresh()

    def refresh(self):
        try:
            data = models.get_suppliers(search=self.search.get())
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
        body = app.show_modal("Add Supplier", width=500, height=420)

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

        notify_email_var = tk.BooleanVar(value=False)
        notify_wa_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="Notify via Email",
                        variable=notify_email_var).grid(row=5, column=1, padx=10, pady=4, sticky="w")
        ttk.Checkbutton(body, text="Notify via WhatsApp",
                        variable=notify_wa_var).grid(row=6, column=1, padx=10, pady=4, sticky="w")

        def save():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                models.add_supplier(
                    name,
                    fields["contact"].get(),
                    fields["address"].get(),
                    fields["email"].get().strip(),
                    fields["phone"].get().strip(),
                    notify_email_var.get(),
                    notify_wa_var.get(),
                )
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Supplier added")

        ttk.Button(body, text="Save", command=save).grid(
            row=7, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)
        fields["name"].focus()

    def _edit_form(self):
        sid = self.table.get_selected_key()
        if not sid:
            messagebox.showwarning("No Selection", "Select a supplier first")
            return
        sup = models.get_supplier(sid)
        if not sup:
            return

        app = self.winfo_toplevel()
        body = app.show_modal("Edit Supplier", width=500, height=420)

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
            entry.insert(0, sup.get(key, "") or "")
            entry.grid(row=i, column=1, padx=10, pady=6, sticky="ew")
            fields[key] = entry

        notify_email_var = tk.BooleanVar(value=str(sup.get("Notify_Email", "")).lower() in ("yes", "true", "1"))
        notify_wa_var = tk.BooleanVar(value=str(sup.get("Notify_WhatsApp", "")).lower() in ("yes", "true", "1"))
        ttk.Checkbutton(body, text="Notify via Email",
                        variable=notify_email_var).grid(row=5, column=1, padx=10, pady=4, sticky="w")
        ttk.Checkbutton(body, text="Notify via WhatsApp",
                        variable=notify_wa_var).grid(row=6, column=1, padx=10, pady=4, sticky="w")

        def save():
            name = fields["Name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                models.update_supplier(
                    sid,
                    name,
                    fields["Contact"].get(),
                    fields["Address"].get(),
                    fields["Email"].get().strip(),
                    fields["Phone"].get().strip(),
                    notify_email_var.get(),
                    notify_wa_var.get(),
                )
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Supplier updated")

        ttk.Button(body, text="Update", command=save).grid(
            row=7, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _delete(self):
        sid = self.table.get_selected_key()
        if not sid:
            messagebox.showwarning("No Selection", "Select a supplier first")
            return
        if messagebox.askyesno("Confirm", "Delete this supplier?"):
            try:
                models.delete_supplier(sid)
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
                    models.add_supplier(
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
            messagebox.showinfo("Import", f"Imported {count} suppliers")
        except PermissionError as e:
            messagebox.showerror("Update Required", str(e))
        except (FileNotFoundError, PermissionError, OSError, ValueError) as e:
            messagebox.showerror("Import Error", str(e))

    def _export(self):
        data = models.get_suppliers()
        headers = ["Name", "Contact", "Address", "Email", "Phone",
                   "Notify_Email", "Notify_WhatsApp", "Created At"]
        rows = [[r.get("Name", ""), r.get("Contact", ""), r.get("Address", ""),
                 r.get("Email", ""), r.get("Phone", ""),
                 r.get("Notify_Email", ""), r.get("Notify_WhatsApp", ""),
                 r.get("Created_At", "")] for r in data]
        export_to_csv(rows, headers, "suppliers_export.csv")