import tkinter as tk
from tkinter import ttk
from database import models
from config import (
    CARD_BG, ACCENT_COLOR, BG_COLOR, BG_DARK, FONT_FAMILY,
    SUCCESS_COLOR, DANGER_COLOR, INFO_COLOR, WARNING_COLOR, APP_NAME,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CARD_BORDER,
    FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL,
    PADDING_SM, PADDING_MD, PADDING_LG,
)
from utils.formatters import format_currency


class DashboardPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()

    def _build_ui(self):
        header_frame = tk.Frame(self, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=PADDING_LG, pady=(PADDING_LG, 4))

        tk.Label(header_frame, text="Dashboard",
                 font=(FONT_FAMILY, FONT_SIZE_XXL, "bold"),
                 bg=BG_COLOR, fg=TEXT_PRIMARY).pack(anchor="w")

        tk.Label(header_frame, text="Business overview at a glance",
                 font=(FONT_FAMILY, FONT_SIZE_MD),
                 bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")

        cards_section = ttk.Frame(self)
        cards_section.pack(fill=tk.BOTH, expand=True, padx=PADDING_LG, pady=PADDING_MD)

        self.cards = {}
        cards_data = [
            ("Total Items", "total_items", "\u25A3", "#2563EB", "#EFF6FF"),
            ("Low Stock Items", "low_stock", "\u26A0", "#DC2626", "#FEF2F2"),
            ("Stock Value", "stock_value", "\u20B9", "#059669", "#ECFDF5"),
            ("Today's Sales", "sales_today", "\u2191", "#0284C7", "#F0F9FF"),
        ]

        for i, (label, key, icon, color, card_bg) in enumerate(cards_data):
            card = self._create_card(cards_section, label, icon, color, card_bg)
            card.grid(row=0, column=i, padx=6, pady=6, sticky="nsew")
            self.cards[key] = card

        cards_section.grid_columnconfigure((0, 1, 2, 3), weight=1)

        refresh_frame = ttk.Frame(self)
        refresh_frame.pack(pady=PADDING_MD)
        ttk.Button(refresh_frame, text="\u21BB  Refresh Dashboard",
                   command=self.refresh).pack()

        self.refresh()

    def _create_card(self, parent, label, icon, color, card_bg):
        frame = tk.Frame(parent, bg=CARD_BG,
                         highlightbackground=CARD_BORDER,
                         highlightthickness=1, padx=PADDING_LG, pady=PADDING_LG)

        icon_frame = tk.Frame(frame, bg=card_bg, width=46, height=46)
        icon_frame.pack_propagate(False)
        icon_frame.grid(row=0, column=0, rowspan=2, padx=(0, PADDING_MD), sticky="nw")

        tk.Label(icon_frame, text=icon, font=(FONT_FAMILY, 22),
                 bg=card_bg, fg=color).place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text=label, font=(FONT_FAMILY, FONT_SIZE_SM),
                 bg=CARD_BG, fg=TEXT_SECONDARY).grid(row=0, column=1, sticky="sw", pady=(2, 0))

        self.cards[label] = tk.Label(
            frame, text="--", font=(FONT_FAMILY, 24, "bold"),
            bg=CARD_BG, fg=color
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
