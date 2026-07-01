import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class ExtraIncomePage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Extra Income",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search income by source or description")

        from_label = ttk.Label(toolbar, text="From:")
        from_label.pack(side=tk.LEFT, padx=(10, 2))
        self.from_var = tk.StringVar()
        from_entry = ttk.Entry(toolbar, textvariable=self.from_var, width=12)
        from_entry.pack(side=tk.LEFT)
        ToolTip(from_entry, "Start date (YYYY-MM-DD)")
        from_entry.bind("<KeyRelease>", lambda e: self.refresh())

        to_label = ttk.Label(toolbar, text="To:")
        to_label.pack(side=tk.LEFT, padx=(5, 2))
        self.to_var = tk.StringVar()
        to_entry = ttk.Entry(toolbar, textvariable=self.to_var, width=12)
        to_entry.pack(side=tk.LEFT)
        ToolTip(to_entry, "End date (YYYY-MM-DD)")
        to_entry.bind("<KeyRelease>", lambda e: self.refresh())

        add_btn = ttk.Button(toolbar, text="Add Income",
                   command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Add a new extra income entry")

        edit_btn = ttk.Button(toolbar, text="Edit",
                   command=self._edit_form)
        edit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(edit_btn, "Edit selected income entry")

        del_btn = ttk.Button(toolbar, text="Delete",
                   command=self._delete)
        del_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(del_btn, "Delete selected income entry")

        exp_btn = ttk.Button(toolbar, text="Export CSV",
                   command=self._export)
        exp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(exp_btn, "Export income data to CSV file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\u2726",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No extra income entries yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'Add Income' to record extra earnings.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Source": 160, "Description": 200, "Amount": 100,
                "Category": 120, "Method": 100, "Ref No": 120, "Date": 150}
        self.table = Table(self._container, columns=cols, key_column="ID",
                           on_double_click=self._edit_form)

        self.refresh()

    def refresh(self):
        try:
            data = models.get_extra_income(
                search=self.search.get(),
                from_date=self.from_var.get().strip(),
                to_date=self.to_var.get().strip(),
            )
        except FileNotFoundError:
            data = []
        display = []
        for r in data:
            display.append({
                "ID": r.get("ID"),
                "Source": r.get("Source", ""),
                "Description": r.get("Description", ""),
                "Amount": r.get("Amount", 0),
                "Category": r.get("Category", ""),
                "Method": r.get("Payment_Method", ""),
                "Ref No": r.get("Reference_No", ""),
                "Date": r.get("Created_At", ""),
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
        body = app.show_modal("Add Extra Income", width=450, height=320)

        fields = {}
        labels = [("Source", "Source"), ("Description", "Description"),
                  ("Amount", "Amount"), ("Category", "Category"),
                  ("Payment Method", "Payment_Method"),
                  ("Reference No.", "Reference_No")]
        for i, (label, key) in enumerate(labels):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = ttk.Entry(body, width=40)
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry

        def save():
            source = fields["Source"].get().strip()
            if not source:
                messagebox.showerror("Error", "Source is required")
                return
            try:
                amount = float(fields["Amount"].get() or 0)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Amount must be a positive number")
                return
            try:
                models.add_extra_income(
                    source, fields["Description"].get(), amount,
                    fields["Category"].get(), fields["Payment_Method"].get(),
                    fields["Reference_No"].get())
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Extra income added")

        ttk.Button(body, text="Save", command=save).grid(
            row=6, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)
        fields["Source"].focus()

    def _edit_form(self):
        sid = self.table.get_selected_key()
        if not sid:
            messagebox.showwarning("No Selection", "Select an income entry first")
            return
        incomes = models.get_extra_income()
        item = next((r for r in incomes if r.get("ID") == sid), None)
        if not item:
            return

        app = self.winfo_toplevel()
        body = app.show_modal("Edit Extra Income", width=450, height=320)

        fields = {}
        labels = [("Source", "Source"), ("Description", "Description"),
                  ("Amount", "Amount"), ("Category", "Category"),
                  ("Payment Method", "Payment_Method"),
                  ("Reference No.", "Reference_No")]
        for i, (label, key) in enumerate(labels):
            ttk.Label(body, text=label).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = ttk.Entry(body, width=40)
            entry.insert(0, item.get(key, "") or "")
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="ew")
            fields[key] = entry

        def save():
            source = fields["Source"].get().strip()
            if not source:
                messagebox.showerror("Error", "Source is required")
                return
            try:
                amount = float(fields["Amount"].get() or 0)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Amount must be a positive number")
                return
            try:
                models.update_extra_income(
                    sid, source, fields["Description"].get(), amount,
                    fields["Category"].get(), fields["Payment_Method"].get(),
                    fields["Reference_No"].get())
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Extra income updated")

        ttk.Button(body, text="Update", command=save).grid(
            row=6, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _delete(self):
        sid = self.table.get_selected_key()
        if not sid:
            messagebox.showwarning("No Selection", "Select an income entry first")
            return
        if messagebox.askyesno("Confirm", "Delete this income entry?"):
            try:
                models.delete_extra_income(sid)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.refresh()

    def _export(self):
        data = models.get_extra_income(
            search=self.search.get(),
            from_date=self.from_var.get().strip(),
            to_date=self.to_var.get().strip(),
        )
        headers = ["Source", "Description", "Amount", "Category", "Payment Method", "Ref No", "Date"]
        rows = []
        for r in data:
            rows.append([r["Source"], r["Description"], r["Amount"],
                         r["Category"], r["Payment_Method"],
                         r.get("Reference_No", ""), r["Created_At"]])
        export_to_csv(rows, headers, "extra_income_export.csv")
