import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from utils.export import export_to_csv


class SuppliersPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Suppliers",
                           font=("Segoe UI", 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Add Supplier",
                   command=self._add_form).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(toolbar, text="Edit",
                   command=self._edit_form).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(toolbar, text="Delete",
                   command=self._delete).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(toolbar, text="Import CSV",
                   command=self._import_csv).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(toolbar, text="Export CSV",
                   command=self._export).pack(side=tk.RIGHT, padx=(5, 0))

        cols = {"Name": 180, "Contact": 150, "Address": 250, "Created_At": 150}
        self.table = Table(self, columns=cols, on_double_click=self._edit_form)
        self.table.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.refresh()

    def refresh(self):
        data = models.get_suppliers(search=self.search.get())
        self.table.populate(data)

    def _on_search(self, text):
        self.refresh()

    def _add_form(self):
        app = self.winfo_toplevel()
        body = app.show_modal("Add Supplier", width=450, height=250)

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
                models.add_supplier(name, fields["contact"].get(), fields["address"].get())
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
            row=3, column=0, columnspan=2, pady=15)
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
        body = app.show_modal("Edit Supplier", width=450, height=250)

        fields = {}
        for i, (label, key) in enumerate([("Name", "Name"), ("Contact", "Contact"),
                                          ("Address", "Address")]):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = ttk.Entry(body, width=40)
            entry.insert(0, sup.get(key, "") or "")
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry

        def save():
            name = fields["Name"].get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                models.update_supplier(sid, name, fields["Contact"].get(), fields["Address"].get())
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
            row=3, column=0, columnspan=2, pady=15)
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
                    models.add_supplier(
                        row.get("Name", row.get("name", "")),
                        row.get("Contact", row.get("contact", "")),
                        row.get("Address", row.get("address", "")),
                    )
                    count += 1
            self.refresh()
            messagebox.showinfo("Import", f"Imported {count} suppliers")
        except PermissionError as e:
            messagebox.showerror("Update Required", str(e))
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def _export(self):
        data = models.get_suppliers()
        headers = ["Name", "Contact", "Address", "Created At"]
        rows = [[r["Name"], r["Contact"], r["Address"], r["Created_At"]] for r in data]
        export_to_csv(rows, headers, "suppliers_export.csv")