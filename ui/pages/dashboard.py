import tkinter as tk
from tkinter import ttk
from database import models
from config import CARD_BG, ACCENT_COLOR, BG_COLOR, FONT_FAMILY, \
    SUCCESS_COLOR, DANGER_COLOR, INFO_COLOR, WARNING_COLOR, APP_NAME
from utils.formatters import format_currency


class DashboardPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header_frame = tk.Frame(self, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=25, pady=(25, 5))

        tk.Label(header_frame, text="Dashboard",
                 font=(FONT_FAMILY, 22, "bold"),
                 bg=BG_COLOR, fg="#2c3e50").pack(anchor="w")

        tk.Label(header_frame, text="Business overview at a glance",
                 font=(FONT_FAMILY, 10),
                 bg=BG_COLOR, fg="#95a5a6").pack(anchor="w")

        cards_section = ttk.Frame(self)
        cards_section.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)

        self.cards = {}
        cards_data = [
            ("Total Items", "total_items", "\u25A3", ACCENT_COLOR,
             "#e8f4fd"),
            ("Low Stock Items", "low_stock", "\u26A0", DANGER_COLOR,
             "#fde8e8"),
            ("Stock Value", "stock_value", "\u20B9", SUCCESS_COLOR,
             "#e8f8f0"),
            ("Today's Sales", "sales_today", "\u2191", INFO_COLOR,
             "#e8f4fd"),
        ]

        for i, (label, key, icon, color, card_bg) in enumerate(cards_data):
            card = self._create_card(cards_section, label, icon, color, card_bg)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            self.cards[key] = card

        cards_section.grid_columnconfigure((0, 1, 2, 3), weight=1)

        refresh_frame = ttk.Frame(self)
        refresh_frame.pack(pady=10)
        ttk.Button(refresh_frame, text="\u21BB  Refresh Dashboard",
                   command=self.refresh).pack()

        self.refresh()

    def _create_card(self, parent, label, icon, color, card_bg):
        frame = tk.Frame(parent, bg="white",
                         highlightbackground="#e0e0e0",
                         highlightthickness=1, padx=20, pady=20)

        icon_frame = tk.Frame(frame, bg=card_bg, width=44, height=44)
        icon_frame.pack_propagate(False)
        icon_frame.grid(row=0, column=0, rowspan=2, padx=(0, 15), sticky="nw")

        tk.Label(icon_frame, text=icon, font=(FONT_FAMILY, 20),
                 bg=card_bg, fg=color).place(relx=0.5, rely=0.5,
                                              anchor="center")

        tk.Label(frame, text=label, font=(FONT_FAMILY, 10),
                 bg="white", fg="#7f8c8d").grid(row=0, column=1,
                                                sticky="sw", pady=(2, 0))

        self.cards[label] = tk.Label(
            frame, text="--", font=(FONT_FAMILY, 22, "bold"),
            bg="white", fg=color
        )
        self.cards[label].grid(row=1, column=1, sticky="nw", pady=(2, 0))

        frame.grid_columnconfigure(1, weight=1)
        return frame

    def refresh(self):
        try:
            stats = models.get_dashboard_stats()
        except Exception:
            stats = {"total_items": 0, "low_stock": 0,
                     "stock_value": 0, "sales_today": 0}

        for key, card_frame in self.cards.items():
            val = stats.get(key, 0)
            text = str(val)
            if key in ("stock_value", "sales_today"):
                text = format_currency(val)
            card_frame.config(text=text)
