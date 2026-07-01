import tkinter as tk
from tkinter import ttk, messagebox
from database import models
from ui.widgets.table import Table
from ui.widgets.search import SearchBar
from ui.widgets.tooltip import ToolTip
from utils.export import export_to_csv
from config import FONT_FAMILY, BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_MD, FONT_SIZE_XL


class PurchasesPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Purchase Orders",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.search = SearchBar(toolbar, callback=self._on_search)
        self.search.pack(side=tk.LEFT)
        ToolTip(self.search.entry, "Search purchases by item or supplier")

        add_btn = ttk.Button(toolbar, text="New Purchase",
                   command=self._add_form)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(add_btn, "Record a new purchase")

        exp_btn = ttk.Button(toolbar, text="Export CSV",
                   command=self._export)
        exp_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(exp_btn, "Export purchases to CSV file")

        self._container = tk.Frame(self, bg=BG_COLOR)
        self._container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._empty_state = tk.Frame(self._container, bg=BG_COLOR)
        self._empty_lbl = tk.Label(self._empty_state, text="\uD83D\uDED2",
                                   font=("Segoe UI Emoji", 48), bg=BG_COLOR, fg="#CCCCCC")
        self._empty_lbl.pack(pady=(40, 10))
        tk.Label(self._empty_state, text="No purchase orders yet",
                 font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack()
        tk.Label(self._empty_state, text="Click 'New Purchase' to record your first order.",
                 font=(FONT_FAMILY, FONT_SIZE_MD), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()

        cols = {"Item": 160, "Supplier": 150, "Qty": 70, "Cost": 90,
                "Total": 100, "Date": 150}
        self.table = Table(self._container, columns=cols, key_column="ID")

        self.refresh()

    def refresh(self):
        try:
            data = models.get_purchases(search=self.search.get())
        except FileNotFoundError:
            data = []
        display = []
        for r in data:
            display.append({
                "ID": r.get("ID"),
                "Item": r.get("item_name", ""),
                "Supplier": r.get("supplier_name", ""),
                "Qty": r.get("Quantity", 0),
                "Cost": r.get("Cost_Price", 0),
                "Total": r.get("Total_Cost", 0),
                "Date": r.get("Purchase_Date", ""),
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
        body = app.show_modal("Record Purchase", width=500, height=300)

        stock_items = models.get_stock_items()
        item_map = {s["Item_Name"]: s["ID"] for s in stock_items}

        ttk.Label(body, text="Item").grid(row=0, column=0, padx=10,
                                          pady=8, sticky="w")
        item_var = tk.StringVar()
        ttk.Combobox(body, textvariable=item_var,
                     values=list(item_map.keys()),
                     state="normal", width=35).grid(row=0, column=1, padx=10, pady=8)

        suppliers = models.get_suppliers()
        sup_map = {s["Name"]: s["ID"] for s in suppliers}
        ttk.Label(body, text="Supplier").grid(row=1, column=0, padx=10,
                                              pady=8, sticky="w")
        sup_var = tk.StringVar()
        ttk.Combobox(body, textvariable=sup_var,
                     values=[""] + list(sup_map.keys()),
                     state="normal", width=35).grid(row=1, column=1, padx=10, pady=8)

        ttk.Label(body, text="Quantity").grid(row=2, column=0, padx=10,
                                              pady=8, sticky="w")
        qty_entry = ttk.Entry(body, width=35)
        qty_entry.grid(row=2, column=1, padx=10, pady=8)

        ttk.Label(body, text="Cost per Unit").grid(row=3, column=0, padx=10,
                                                   pady=8, sticky="w")
        cost_entry = ttk.Entry(body, width=35)
        cost_entry.grid(row=3, column=1, padx=10, pady=8)

        def save():
            item_name = item_var.get()
            sup_name = sup_var.get()
            if item_name not in item_map:
                messagebox.showerror("Error", "Select a valid item")
                return
            try:
                qty = int(qty_entry.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Quantity.")
                return
            try:
                cost = float(cost_entry.get().strip())
            except (ValueError, TypeError):
                messagebox.showerror("Input Error", "Please enter a valid number for Cost.")
                return
            if qty <= 0 or cost <= 0:
                messagebox.showerror("Error", "Quantity and Cost must be positive numbers")
                return
            try:
                models.record_purchase(item_map[item_name],
                                       sup_map.get(sup_name), qty, cost)
            except PermissionError as e:
                messagebox.showerror("Update Required", str(e))
                return
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            app.close_modal()
            self.refresh()
            messagebox.showinfo("Success", "Purchase recorded")

        ttk.Button(body, text="Record Purchase", command=save).grid(
            row=4, column=0, columnspan=2, pady=15)
        body.grid_columnconfigure(1, weight=1)

    def _export(self):
        data = models.get_purchases()
        headers = ["Item", "Supplier", "Quantity", "Cost", "Total", "Date"]
        rows = [[r["item_name"], r["supplier_name"], r["Quantity"],
                 r["Cost_Price"], r["Total_Cost"], r["Purchase_Date"]]
                for r in data]
        export_to_csv(rows, headers, "purchases_export.csv")