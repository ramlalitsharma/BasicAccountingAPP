import tkinter as tk
from tkinter import ttk
from config import (
    ACCENT_COLOR, CARD_BG, BG_COLOR, BG_DARK, FONT_FAMILY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CARD_BORDER,
    FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, PADDING_MD,
)
from ui.widgets.tooltip import ToolTip

ALT_ROW_BG = "#F8FAFC"
LOW_STOCK_BG = "#FEF2F2"


class Table(ttk.Frame):
    def __init__(self, parent, columns, key_column="id", page_size=50,
                 on_double_click=None, search_all_cols=False, **kwargs):
        super().__init__(parent, **kwargs)
        self.columns = columns
        self.key_column = key_column
        self.page_size = page_size
        self.on_double_click = on_double_click
        self.search_all_cols = search_all_cols
        self._all_rows = []
        self._row_map = {}
        self._page = 0
        self._total_pages = 0
        self._sort_col = None
        self._sort_reverse = False
        self._build_widget()

    def _build_widget(self):
        col_list = list(self.columns.keys())
        self.tree = ttk.Treeview(self, columns=col_list,
                                 show="headings", selectmode="browse")
        col_width = max(900, len(col_list) * 100)
        for col, width in self.columns.items():
            heading = col.replace("_", " ").title()
            self.tree.heading(col, text=heading,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, minwidth=70)

        if self.on_double_click:
            self.tree.bind("<Double-1>", lambda e: self.on_double_click())

        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=0)
        scroll_y.grid(row=0, column=4, sticky="ns")
        scroll_x.grid(row=1, column=0, columnspan=4, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.nav_frame = ttk.Frame(self)
        self.nav_frame.grid(row=2, column=0, columnspan=4, pady=6, sticky="ew")

        self.info_lbl = ttk.Label(self.nav_frame, text="",
                                  font=(FONT_FAMILY, FONT_SIZE_SM),
                                  foreground=TEXT_SECONDARY)
        self.info_lbl.pack(side=tk.LEFT, padx=PADDING_MD)

        btn_frame = ttk.Frame(self.nav_frame)
        btn_frame.pack(side=tk.RIGHT, padx=10)

        self.first_btn = ttk.Button(btn_frame, text="\u23EE", width=3,
                                    command=self._first_page)
        self.first_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.first_btn, "First page")

        self.prev_btn = ttk.Button(btn_frame, text="\u25C0", width=3,
                                   command=self._prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.prev_btn, "Previous page")

        self.page_lbl = ttk.Label(btn_frame, text="", font=(FONT_FAMILY, FONT_SIZE_SM))
        self.page_lbl.pack(side=tk.LEFT, padx=8)

        self.next_btn = ttk.Button(btn_frame, text="\u25B6", width=3,
                                   command=self._next_page)
        self.next_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.next_btn, "Next page")

        self.last_btn = ttk.Button(btn_frame, text="\u23ED", width=3,
                                   command=self._last_page)
        self.last_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.last_btn, "Last page")

    def _sort_by(self, col):
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        def sort_key(r):
            v = r.get(col, "")
            try:
                return (0, float(v))
            except (ValueError, TypeError):
                return (1, str(v).lower())

        try:
            self._all_rows.sort(key=sort_key, reverse=self._sort_reverse)
        except (TypeError, ValueError, tk.TclError):
            pass
        self._render_page()

    def populate(self, rows):
        self._all_rows = rows
        self._row_map.clear()
        self._page = 0
        total = len(rows)
        self._total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        self._render_page()

    def _render_page(self):
        self.clear()
        start = self._page * self.page_size
        end = start + self.page_size
        page_rows = self._all_rows[start:end]

        self.tree.tag_configure("evenrow", background=ALT_ROW_BG)
        self.tree.tag_configure("oddrow", background=CARD_BG)
        self.tree.tag_configure("low_stock", background=LOW_STOCK_BG)

        for idx, row in enumerate(page_rows):
            values = [row.get(col, "") for col in self.columns]
            item_id = self.tree.insert("", tk.END, values=values)
            key = row.get(self.key_column)
            if key is not None:
                self._row_map[item_id] = key

            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            qty = row.get("Quantity")
            min_q = row.get("Min_Quantity")
            try:
                if qty is not None and min_q is not None and int(qty) <= int(min_q):
                    tag = "low_stock"
            except (ValueError, TypeError):
                pass
            self.tree.item(item_id, tags=(tag,))

        total = len(self._all_rows)
        showing = f"{start + 1}-{min(end, total)}" if total > 0 else "0"
        self.info_lbl.config(text=f"Showing {showing} of {total} records")
        self.page_lbl.config(
            text=f"Page {self._page + 1} of {self._total_pages}")

        disable = tk.DISABLED
        normal = tk.NORMAL
        self.first_btn.config(state=normal if self._page > 0 else disable)
        self.prev_btn.config(state=normal if self._page > 0 else disable)
        self.next_btn.config(
            state=normal if self._page < self._total_pages - 1 else disable)
        self.last_btn.config(
            state=normal if self._page < self._total_pages - 1 else disable)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _first_page(self):
        self._page = 0
        self._render_page()

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        if self._page < self._total_pages - 1:
            self._page += 1
            self._render_page()

    def _last_page(self):
        self._page = self._total_pages - 1
        self._render_page()

    def get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        return {
            "values": self.tree.item(item_id, "values"),
            "key": self._row_map.get(item_id),
        }

    def get_selected_key(self):
        row = self.get_selected_row()
        return row["key"] if row else None
