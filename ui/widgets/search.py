import tkinter as tk
from tkinter import ttk


class SearchBar(ttk.Frame):
    def __init__(self, parent, placeholder="Search...", callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.callback = callback
        self._placeholder = placeholder
        self._ready = False
        self._has_placeholder = True
        self.var = tk.StringVar()
        self.var.trace_add("write", self._on_change)

        ttk.Label(self, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.entry = ttk.Entry(self, textvariable=self.var, width=30)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.insert(0, placeholder)
        self.entry.bind("<FocusIn>", lambda e: self._clear_placeholder())
        self.entry.bind("<FocusOut>", lambda e: self._restore_placeholder())

        clear_btn = ttk.Button(self, text="Clear", command=self.clear)
        clear_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.after(100, self._mark_ready)

    def _mark_ready(self):
        self._ready = True

    def _on_change(self, *args):
        if self.callback and self._ready:
            self.callback(self.var.get())

    def clear(self):
        self.var.set("")

    def _clear_placeholder(self):
        if self._has_placeholder:
            self.var.set("")
            self._has_placeholder = False

    def _restore_placeholder(self):
        if not self.var.get():
            self.var.set(self._placeholder)
            self._has_placeholder = True

    def get(self):
        v = self.var.get()
        return "" if v == self._placeholder else v
