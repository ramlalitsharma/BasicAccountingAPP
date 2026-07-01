import tkinter as tk
from tkinter import ttk
from config import CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, FONT_FAMILY, APP_NAME, VERSION


class WelcomePage(ttk.Frame):
    def __init__(self, parent, on_new_file=None, on_open_file=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_new_file = on_new_file or (lambda: None)
        self.on_open_file = on_open_file or (lambda: None)
        self._build()

    def _build(self):
        container = tk.Frame(self, bg=CARD_BG)
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(container, text="📊", font=("Segoe UI", 64), bg=CARD_BG).pack()

        tk.Label(container, text=APP_NAME, font=(FONT_FAMILY, 24, "bold"),
                bg=CARD_BG, fg=TEXT_PRIMARY).pack(pady=(10, 0))

        tk.Label(container, text=f"Version {VERSION}", font=(FONT_FAMILY, 10),
                bg=CARD_BG, fg=TEXT_SECONDARY).pack()

        tk.Label(container, text="Professional Accounting & Inventory Management",
                font=(FONT_FAMILY, 11), bg=CARD_BG, fg=TEXT_SECONDARY).pack(pady=(5, 20))

        btn_frame = tk.Frame(container, bg=CARD_BG)
        btn_frame.pack()

        ttk.Button(btn_frame, text="📁  New File", command=self.on_new_file,
                  width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂  Open File", command=self.on_open_file,
                  width=20).pack(side=tk.LEFT, padx=5)

        tips_frame = tk.Frame(container, bg=CARD_BG)
        tips_frame.pack(pady=30)

        tk.Label(tips_frame, text="Quick Tips", font=(FONT_FAMILY, 10, "bold"),
                bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")

        tips = [
            "• Start by creating or opening a company file (.xlsx)",
            "• Add suppliers, stock items, and customers",
            "• Record sales, purchases, and track payments",
            "• Generate reports and invoices",
            "• Use Alt+1 through Alt+9 for quick navigation",
        ]
        for tip in tips:
            tk.Label(tips_frame, text=tip, font=(FONT_FAMILY, 9),
                    bg=CARD_BG, fg=TEXT_SECONDARY, anchor="w").pack(fill=tk.X)
