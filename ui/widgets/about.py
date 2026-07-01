import tkinter as tk
from tkinter import ttk
from config import VERSION, APP_NAME, FONT_FAMILY, CARD_BG, TEXT_PRIMARY, TEXT_SECONDARY, FONT_SIZE_LG


class AboutDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"About {APP_NAME}")
        self.resizable(False, False)
        self.configure(bg=CARD_BG)

        w, h = 420, 400
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{px}+{py}")

        self._build()
        self.grab_set()

    def _build(self):
        icon_frame = tk.Frame(self, bg=CARD_BG, height=80)
        icon_frame.pack(fill=tk.X, pady=(30, 0))

        tk.Label(icon_frame, text="📊", font=("Segoe UI", 40), bg=CARD_BG).pack()

        tk.Label(self, text=APP_NAME, font=(FONT_FAMILY, 18, "bold"),
                bg=CARD_BG, fg=TEXT_PRIMARY).pack(pady=(10, 0))

        tk.Label(self, text=f"Version {VERSION}", font=(FONT_FAMILY, FONT_SIZE_LG),
                bg=CARD_BG, fg=TEXT_SECONDARY).pack()

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=40, pady=15)

        desc = ("Professional accounting and inventory management\n"
                "software for small and medium businesses.\n\n"
                "Features:\n"
                "• Dashboard with visual analytics\n"
                "• Supplier & customer management\n"
                "• Stock & inventory tracking\n"
                "• Sales & purchase recording\n"
                "• Invoice generation\n"
                "• Comprehensive reporting\n"
                "• Preorder management\n"
                "• Extra income tracking")
        tk.Label(self, text=desc, font=(FONT_FAMILY, 9),
                bg=CARD_BG, fg=TEXT_PRIMARY, justify=tk.LEFT).pack(padx=40)

        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=40, pady=15)

        tk.Label(self, text="Licensed to: Unregistered",
                font=(FONT_FAMILY, 8), bg=CARD_BG, fg=TEXT_SECONDARY).pack()

        btn = ttk.Button(self, text="Close", command=self.destroy)
        btn.pack(pady=(10, 20))
