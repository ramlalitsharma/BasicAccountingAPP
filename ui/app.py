import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
import queue
from datetime import datetime
from config import (
    APP_NAME, VERSION,
    SIDEBAR_BG, SIDEBAR_FG, SIDEBAR_ACTIVE_BG, SIDEBAR_ACTIVE_FG,
    SIDEBAR_HOVER_BG, SIDEBAR_ACCENT,
    BG_COLOR, BG_DARK, CARD_BG, CARD_BORDER,
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    FONT_SIZE_XL, FONT_SIZE_XXL,
    ACCENT_COLOR, ACCENT_LIGHT, ACCENT_DARK,
    PRIMARY_COLOR,
    DANGER_COLOR,
    WARNING_COLOR,
    SUCCESS_COLOR,
    INFO_COLOR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    MODAL_OVERLAY, PADDING_MD, PADDING_LG,
    DATA_DIR, ICON_PATH, get_setting, set_setting,
    get_color, _get_current_theme,
)
from database import models
from database.backup import backup_database, create_backup, start_auto_backup, stop_auto_backup
from ui.pages.dashboard import DashboardPage
from ui.pages.suppliers import SuppliersPage
from ui.pages.stock import StockPage
from ui.pages.sales import SalesPage
from ui.pages.reports import ReportsPage
from ui.pages.settings import SettingsPage
from ui.pages.customers import CustomersPage
from ui.pages.purchases import PurchasesPage
from ui.pages.preorders import PreordersPage
from ui.pages.extra_income import ExtraIncomePage
from ui.widgets.toast import Toast
from ui.widgets.about import AboutDialog
from ui.pages.welcome import WelcomePage
from utils.update_checker import (
    check_for_update_async, get_update_status,
    update_available_info, is_update_available,
    download_update_async, must_update_now,
    needs_auto_check, auto_update_on_launch,
    install_update, verify_download,
)
from config import RELEASE_BASE_URL

logger = logging.getLogger(__name__)

NAV_ITEMS = [
    ("dashboard", "\u25A3  Dashboard"),
    ("suppliers", "\u25C8  Suppliers"),
    ("purchases", "\u21BB  Purchases"),
    ("stock", "\u25A1  Stock"),
    ("sales", "\u20B9  Sales"),
    ("customers", "\u25CF  Customers"),
    ("extra_income", "\u20B9  Extra Income"),
    ("preorders", "\u25CB  Preorders"),
    ("reports", "\u25A4  Reports"),
    ("settings", "\u2699  Settings"),
]


class AccountingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self._x, self._y = 0, 0
        self._maximized = False
        self._normal_geometry = None

        self.title(APP_NAME)
        self.configure(bg=PRIMARY_COLOR)
        self.minsize(900, 600)
        saved_geo = get_setting("window_geometry", None)
        if saved_geo:
            try:
                self.geometry(saved_geo)
            except tk.TclError:
                pass
        try:
            if ICON_PATH and os.path.exists(ICON_PATH):
                self.iconbitmap(default=ICON_PATH)
        except (FileNotFoundError, OSError):
            pass

        self._pages = {}
        self._current_page = None
        self._nav_buttons = {}
        self.toast = Toast(self)

        self._setup_custom_titlebar()
        self._setup_sidebar()
        self._setup_content()
        self._apply_theme()
        self._setup_status_bar()
        self._setup_shortcuts()

        self._update_auto_check_id = None
        self._ui_queue = queue.Queue()
        self._poll_ui_queue()
        backup_interval = get_setting("backup_interval_minutes", 30)
        start_auto_backup(backup_interval)
        self.after(300, self._initial_file_setup)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_custom_titlebar(self):
        tb = tk.Frame(self, bg=PRIMARY_COLOR, height=34)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)

        tb.bind("<Button-1>", self._start_move)
        tb.bind("<B1-Motion>", self._do_move)
        tb.bind("<Double-Button-1>", self._toggle_maximize)

        try:
            from config import ICON_PNG_PATH
            if ICON_PNG_PATH and os.path.exists(ICON_PNG_PATH):
                sm_icon = tk.PhotoImage(file=ICON_PNG_PATH).subsample(3, 3)
                logo_lbl = tk.Label(tb, image=sm_icon, bg=PRIMARY_COLOR,
                                    cursor="fleur")
                logo_lbl.image = sm_icon
                logo_lbl.pack(side=tk.LEFT, padx=(8, 4))
                logo_lbl.bind("<Button-1>", self._start_move)
                logo_lbl.bind("<B1-Motion>", self._do_move)
        except (FileNotFoundError, OSError):
            pass

        title_lbl = tk.Label(tb, text=f"  {APP_NAME}  v{VERSION}",
                             font=(FONT_FAMILY, 10, "bold"),
                             bg=PRIMARY_COLOR, fg="white", cursor="fleur")
        title_lbl.pack(side=tk.LEFT)
        title_lbl.bind("<Button-1>", self._start_move)
        title_lbl.bind("<B1-Motion>", self._do_move)

        accent_bar = tk.Frame(tb, bg=SIDEBAR_ACCENT, height=2)
        accent_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self._titlebar = tb

        btn_frame = tk.Frame(tb, bg=PRIMARY_COLOR)
        btn_frame.pack(side=tk.RIGHT, padx=6)

        self._create_title_button(btn_frame, "\u2014", 14, self._iconify,
                                  PRIMARY_COLOR, "#2C3E6B")
        self._max_btn = self._create_title_button(
            btn_frame, "\u25A1", 11, self._toggle_maximize,
            PRIMARY_COLOR, "#2C3E6B"
        )
        self._create_title_button(btn_frame, "\u2715", 13, self._on_close,
                                  "#DC2626", "#EF4444")

    def _create_title_button(self, parent, text, font_size, cmd, bg, hover_bg):
        btn = tk.Label(parent, text=text, font=(FONT_FAMILY, font_size),
                       bg=bg, fg="white", padx=10, pady=2, cursor="hand2")
        btn.pack(side=tk.LEFT, padx=1)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    def _start_move(self, event):
        self._x = event.x_root - self.winfo_x()
        self._y = event.y_root - self.winfo_y()

    def _do_move(self, event):
        if not self._maximized:
            self.geometry(f"+{event.x_root - self._x}+{event.y_root - self._y}")
        else:
            self._toggle_maximize()
            self._x = event.x_root - self.winfo_x()
            self._y = event.y_root - self.winfo_y()

    def _toggle_maximize(self, event=None):
        if self._maximized:
            if self._normal_geometry:
                self.geometry(self._normal_geometry)
            self._maximized = False
            self._max_btn.configure(text="\u25A1")
        else:
            self._normal_geometry = self.geometry()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{sw}x{sh}+0+0")
            self._maximized = True
            self._max_btn.configure(text="\u25A0")

    def _setup_sidebar(self):
        sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        header_frame = tk.Frame(sidebar, bg=SIDEBAR_BG, height=56)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="\u25A3  Accounting Pro",
                 font=(FONT_FAMILY, 14, "bold"),
                 bg=SIDEBAR_BG, fg="white").pack(pady=16)

        sep = tk.Frame(sidebar, bg=SIDEBAR_ACCENT, height=2)
        sep.pack(fill=tk.X)

        nav_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        nav_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        self._nav_indicators = {}
        for key, label in NAV_ITEMS:
            item_frame = tk.Frame(nav_frame, bg=SIDEBAR_BG)
            item_frame.pack(fill=tk.X, padx=0, pady=0)

            indicator = tk.Frame(item_frame, bg=SIDEBAR_BG, width=3)
            indicator.pack(side=tk.LEFT, fill=tk.Y)

            btn = tk.Label(
                item_frame, text=label,
                font=(FONT_FAMILY, FONT_SIZE_LG),
                bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                anchor="w", padx=18, pady=10,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            btn.bind("<Button-1>", lambda e, k=key: self._navigate(k))
            btn.bind("<Enter>", lambda e, b=btn, ind=indicator: self._on_nav_hover(b, ind))
            btn.bind("<Leave>", lambda e, b=btn, ind=indicator: self._on_nav_leave(b, ind))

            self._nav_buttons[key] = btn
            self._nav_indicators[key] = indicator

        bottom_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        for icon, text, cmd in [
            ("\u2B07", "  Open File", self._open_file_dialog),
            ("\u21BA", "  Backup", self._do_backup),
            ("\u21BB", "  Check Updates", lambda: self.check_updates_now(True)),
            ("\u2139", "  About", lambda: AboutDialog(self)),
        ]:
            item_frame = tk.Frame(bottom_frame, bg=SIDEBAR_BG)
            item_frame.pack(fill=tk.X)
            btn = tk.Label(item_frame, text=f"{icon}{text}",
                           font=(FONT_FAMILY, FONT_SIZE_MD),
                           bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                           anchor="w", padx=20, pady=8,
                           cursor="hand2")
            btn.pack(fill=tk.X)
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=SIDEBAR_HOVER_BG, fg="white"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=SIDEBAR_BG, fg=SIDEBAR_FG))

        sep2 = tk.Frame(bottom_frame, bg="#1E293B", height=1)
        sep2.pack(fill=tk.X)

        self.file_label = tk.Label(bottom_frame, text="No file open",
                                   font=(FONT_FAMILY, FONT_SIZE_SM),
                                   bg=SIDEBAR_BG, fg=TEXT_MUTED,
                                   anchor="w", padx=20, pady=4)
        self.file_label.pack(fill=tk.X)

        self.update_side_lbl = tk.Label(bottom_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
            bg=WARNING_COLOR, fg="white",
            anchor="center", padx=10, pady=6,
            cursor="hand2")
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.update_side_lbl.pack_forget()

    def _setup_status_bar(self):
        self.status_bar = tk.Frame(self, bg=BG_DARK, height=28)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        sep = tk.Frame(self.status_bar, height=1)
        sep.configure(bg=CARD_BORDER)
        sep.pack(fill=tk.X)

        inner = tk.Frame(self.status_bar, bg=BG_DARK)
        inner.pack(fill=tk.X, expand=True, padx=8, pady=2)

        self.status_file_lbl = tk.Label(inner, text="No file open",
            font=(FONT_FAMILY, FONT_SIZE_SM), bg=BG_DARK, fg=TEXT_SECONDARY, anchor="w")
        self.status_file_lbl.pack(side=tk.LEFT, padx=(4, 12))

        sep1 = tk.Frame(inner, bg=TEXT_MUTED, width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        self.status_records_lbl = tk.Label(inner, text="0 records loaded",
            font=(FONT_FAMILY, FONT_SIZE_SM), bg=BG_DARK, fg=TEXT_SECONDARY, anchor="w")
        self.status_records_lbl.pack(side=tk.LEFT, padx=12)

        sep2 = tk.Frame(inner, bg=TEXT_MUTED, width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        self.status_time_lbl = tk.Label(inner, text="",
            font=(FONT_FAMILY, FONT_SIZE_SM), bg=BG_DARK, fg=TEXT_SECONDARY, anchor="w")
        self.status_time_lbl.pack(side=tk.LEFT, padx=12)

        sep3 = tk.Frame(inner, bg=TEXT_MUTED, width=1)
        sep3.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        self.status_message_lbl = tk.Label(inner, text="Ready",
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"), bg=BG_DARK, fg=SUCCESS_COLOR, anchor="w")
        self.status_message_lbl.pack(side=tk.LEFT, padx=12)

        version_lbl = tk.Label(inner, text=f"v{VERSION}",
            font=(FONT_FAMILY, FONT_SIZE_SM), bg=BG_DARK, fg=TEXT_MUTED, anchor="e")
        version_lbl.pack(side=tk.RIGHT, padx=4)

        self._update_clock()

    def _update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_time_lbl.config(text=now)
        self.after(1000, self._update_clock)

    def set_status(self, message, status_type="info"):
        colors = {"info": TEXT_PRIMARY, "success": SUCCESS_COLOR, "warning": WARNING_COLOR, "error": DANGER_COLOR}
        color = colors.get(status_type, TEXT_PRIMARY)
        self.status_message_lbl.config(text=message, fg=color)

    def _setup_shortcuts(self):
        self.bind("<Control-n>", lambda e: self._new_file())
        self.bind("<Control-N>", lambda e: self._new_file())
        self.bind("<Control-o>", lambda e: self._open_file_dialog())
        self.bind("<Control-O>", lambda e: self._open_file_dialog())
        self.bind("<Control-w>", lambda e: self._close_file())
        self.bind("<Control-W>", lambda e: self._close_file())
        self.bind("<Control-q>", lambda e: self._on_close())
        self.bind("<Control-Q>", lambda e: self._on_close())
        self.bind("<F5>", lambda e: self._refresh_current_page())
        self.bind("<Control-s>", lambda e: self._do_backup())
        self.bind("<Control-S>", lambda e: self._do_backup())
        self.bind("<Control-e>", lambda e: self.set_status("Edit selected item", "info"))
        self.bind("<Control-E>", lambda e: self.set_status("Edit selected item", "info"))
        self.bind("<Control-f>", lambda e: self.set_status("Search", "info"))
        self.bind("<Control-F>", lambda e: self.set_status("Search", "info"))
        self.bind("<Escape>", lambda e: self.close_modal())

        for i, (key, _) in enumerate(NAV_ITEMS):
            num = i + 1
            if num < 10:
                self.bind(f"<Alt-Key-{num}>", lambda e, k=key: self._navigate(k))

    def _new_file(self):
        try:
            path = models.create_new_workbook()
            self._update_file_label()
            self.set_status("New workbook created", "success")
            messagebox.showinfo("Success", f"New workbook created:\n{path}")
        except (FileNotFoundError, OSError) as e:
            messagebox.showerror("Error", f"Failed to create workbook: {e}")

    def _close_file(self):
        if not models.get_active_file():
            return
        if messagebox.askyesno("Close File", "Close the current workbook?"):
            models.set_active_file("")
            self._update_file_label()
            self.set_status("File closed", "info")
            for page in self._pages.values():
                if hasattr(page, "refresh"):
                    page.refresh()

    def _refresh_current_page(self):
        if self._current_page and self._current_page in self._pages:
            page = self._pages[self._current_page]
            if hasattr(page, "refresh"):
                page.refresh()
                self.set_status("Refreshed", "success")
            self.toast.show("Page refreshed", "success", 2000)

    def set_record_count(self, count):
        self.status_records_lbl.config(text=f"{count} records loaded")

    def show_loading(self, message="Loading..."):
        overlay = tk.Toplevel(self.content)
        overlay.overrideredirect(True)
        overlay.attributes("-alpha", 0.3)
        overlay.configure(bg="#000000")
        overlay.geometry(f"{self.content.winfo_width()}x{self.content.winfo_height()}+{self.content.winfo_rootx()}+{self.content.winfo_rooty()}")
        overlay.transient(self)
        overlay.grab_set()
        overlay.lift()

        label = tk.Label(overlay, text=message,
            font=(FONT_FAMILY, FONT_SIZE_XL, "bold"),
            bg="#000000", fg="white")
        label.place(relx=0.5, rely=0.5, anchor="center")

        self._loading_overlay = overlay
        self._loading_label = label

    def hide_loading(self):
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            try:
                self._loading_overlay.grab_release()
                self._loading_overlay.destroy()
            except tk.TclError:
                pass
            self._loading_overlay = None
            self._loading_label = None

    def _on_nav_hover(self, btn, indicator):
        if btn.cget("bg") != get_color("SIDEBAR_ACTIVE_BG"):
            btn.configure(bg=get_color("SIDEBAR_HOVER_BG"), fg="white")

    def _on_nav_leave(self, btn, indicator):
        if btn.cget("bg") != get_color("SIDEBAR_ACTIVE_BG"):
            btn.configure(bg=get_color("SIDEBAR_BG"), fg=get_color("SIDEBAR_FG"))

    def _setup_content(self):
        self.update_bar = tk.Frame(self, bg=WARNING_COLOR, height=32)
        self.update_text = tk.StringVar()
        self.update_lbl = tk.Label(
            self.update_bar, textvariable=self.update_text,
            font=(FONT_FAMILY, FONT_SIZE_MD), bg=WARNING_COLOR, fg="white", anchor="w")
        self.update_lbl.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)
        self.update_btn = tk.Label(
            self.update_bar, text="View Update \u2197",
            font=(FONT_FAMILY, FONT_SIZE_MD, "bold"), bg="#d35400", fg="white",
            padx=10, cursor="hand2")
        self.update_btn.pack(side=tk.RIGHT, padx=4)
        self.dismiss_btn = tk.Label(
            self.update_bar, text="",
            font=(FONT_FAMILY, FONT_SIZE_MD), bg=WARNING_COLOR, fg="white",
            padx=0, cursor="hand2")
        self.dismiss_btn.pack_forget()
        self.update_bar.pack_forget()

        content_wrapper = tk.Frame(self, bg=BG_COLOR)
        content_wrapper.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.content = tk.Frame(content_wrapper, bg=BG_COLOR)
        self.content.pack(fill=tk.BOTH, expand=True)

    def _apply_theme(self):
        is_dark = _get_current_theme() == "Dark"
        bg = get_color("BG_COLOR")
        bg_dark = get_color("BG_DARK")
        card_bg = get_color("CARD_BG")
        card_border = get_color("CARD_BORDER")
        text_primary = get_color("TEXT_PRIMARY")
        text_secondary = get_color("TEXT_SECONDARY")
        text_muted = get_color("TEXT_MUTED")
        accent = get_color("ACCENT_COLOR")
        accent_light = get_color("ACCENT_LIGHT")
        accent_dark = get_color("ACCENT_DARK")
        sidebar_bg = get_color("SIDEBAR_BG")
        sidebar_fg = get_color("SIDEBAR_FG")
        sidebar_active_bg = get_color("SIDEBAR_ACTIVE_BG")
        sidebar_active_fg = get_color("SIDEBAR_ACTIVE_FG")
        sidebar_hover_bg = get_color("SIDEBAR_HOVER_BG")
        sidebar_accent = get_color("SIDEBAR_ACCENT")
        primary = get_color("PRIMARY_COLOR")
        warning = get_color("WARNING_COLOR")
        border_color = get_color("BORDER_COLOR")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=(FONT_FAMILY, FONT_SIZE_MD))
        style.configure("TLabel", background=bg, foreground=text_primary)
        style.configure("Heading.TLabel", font=(FONT_FAMILY, FONT_SIZE_XXL, "bold"), foreground=text_primary)
        style.configure("SubHeading.TLabel", font=(FONT_FAMILY, FONT_SIZE_XL, "bold"), foreground=text_primary)
        style.configure("Muted.TLabel", foreground=text_muted)
        style.configure("Card.TLabel", background=card_bg, foreground=text_primary)
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card_bg)
        style.configure("TLabelframe", background=card_bg, foreground=text_primary)
        style.configure("TLabelframe.Label", background=card_bg, foreground=text_primary)
        style.configure("TButton", padding=(14, 7), background=accent, foreground="white", borderwidth=0, focusthickness=0)
        style.map("TButton", background=[("active", accent_light), ("pressed", accent_dark)], foreground=[("active", "white")])
        style.configure("Secondary.TButton", background=text_secondary)
        style.map("Secondary.TButton", background=[("active", text_muted)])
        style.configure("Treeview", background=border_color, foreground=text_primary,
                        fieldbackground=card_bg, rowheight=32, borderwidth=1, relief="solid")
        style.map("Treeview", background=[("selected", accent_dark)], foreground=[("selected", "white")])
        style.map("Treeview", fieldbackground=[("selected", accent_dark)])
        style.configure("Treeview.Heading", font=(FONT_FAMILY, FONT_SIZE_MD, "bold"),
                        background=accent, foreground="white", relief="solid", borderwidth=2)
        style.map("Treeview.Heading", background=[("active", accent_light)])
        style.layout("Treeview.Heading", [
            ("Treeheading.cell", {"sticky": "nswe", "children": [
                ("Treeheading.border", {"sticky": "nswe", "children": [
                    ("Treeheading.padding", {"sticky": "nswe", "children": [
                        ("Treeheading.label", {"sticky": "nswe"})
                    ]})
                ]})
            ]})
        ])
        style.layout("Treeview", [
            ("Treeview.field", {"sticky": "nswe", "children": [
                ("Treeview.treearea", {"sticky": "nswe"})
            ]})
        ])
        style.configure("TEntry", padding=6, fieldbackground=card_bg, foreground=text_primary, borderwidth=1)
        style.map("TEntry", fieldbackground=[("focus", card_bg)])
        style.configure("TCombobox", padding=4, fieldbackground=card_bg, foreground=text_primary)
        style.map("TCombobox", fieldbackground=[("focus", card_bg)])
        style.configure("TScrollbar", gripcount=0, background=bg_dark, troughcolor=bg, borderwidth=0, arrowcolor=text_muted)
        style.map("TScrollbar", background=[("active", accent_light)])
        style.configure("TNotebook", background=bg, foreground=text_primary)
        style.configure("TNotebook.Tab", background=bg_dark, foreground=text_secondary, padding=[12, 4])
        style.map("TNotebook.Tab", background=[("selected", card_bg)], foreground=[("selected", text_primary)])

        self.configure(bg=primary if not is_dark else sidebar_bg)
        if hasattr(self, '_titlebar') and self._titlebar.winfo_exists():
            self._titlebar.configure(bg=primary)
        if hasattr(self, 'content') and self.content.winfo_exists():
            self.content.configure(bg=bg)
        if hasattr(self, 'status_bar') and self.status_bar.winfo_exists():
            self.status_bar.configure(bg=bg_dark)
        if hasattr(self, 'update_bar') and self.update_bar.winfo_exists():
            self.update_bar.configure(bg=warning)

        self._recolor_sidebar(sidebar_bg, sidebar_fg, sidebar_active_bg, sidebar_active_fg, sidebar_hover_bg)
        self._recolor_widget_tree(self.content, bg, card_bg, bg_dark, text_primary, text_secondary, text_muted)
        if hasattr(self, 'status_bar') and self.status_bar.winfo_exists():
            self._recolor_widget_tree(self.status_bar, bg, card_bg, bg_dark, text_primary, text_secondary, text_muted)
        if hasattr(self, 'update_bar') and self.update_bar.winfo_exists():
            self._recolor_widget_tree(self.update_bar, bg, card_bg, bg_dark, text_primary, text_secondary, text_muted)

    def _recolor_sidebar(self, sidebar_bg, sidebar_fg, sidebar_active_bg, sidebar_active_fg, sidebar_hover_bg):
        if not hasattr(self, '_nav_buttons'):
            return
        for key, btn in self._nav_buttons.items():
            if self._current_page == key:
                btn.configure(bg=sidebar_active_bg, fg=sidebar_active_fg)
            else:
                btn.configure(bg=sidebar_bg, fg=sidebar_fg)
        for ind in self._nav_indicators.values():
            ind.configure(bg=sidebar_bg)
        try:
            for child in self.winfo_children():
                self._recolor_sidebar_children(child, sidebar_bg, sidebar_fg, sidebar_hover_bg)
        except tk.TclError:
            pass

    def _recolor_sidebar_children(self, widget, sidebar_bg, sidebar_fg, sidebar_hover_bg):
        if isinstance(widget, tk.Label):
            try:
                cbg = widget.cget("bg")
                cfg = widget.cget("fg")
                if cbg in ("#0F172A", "#020617") or cfg in ("#94A3B8", "#64748B"):
                    widget.configure(bg=sidebar_bg, fg=sidebar_fg)
                    widget.bind("<Enter>", lambda e, b=widget: b.configure(bg=sidebar_hover_bg, fg="white"))
                    widget.bind("<Leave>", lambda e, b=widget: b.configure(bg=sidebar_bg, fg=sidebar_fg))
            except tk.TclError:
                pass
        elif isinstance(widget, tk.Frame):
            try:
                cbg = widget.cget("bg")
                if cbg in ("#0F172A", "#020617", "#1E293B"):
                    widget.configure(bg=sidebar_bg)
            except tk.TclError:
                pass
        try:
            for child in widget.winfo_children():
                self._recolor_sidebar_children(child, sidebar_bg, sidebar_fg, sidebar_hover_bg)
        except tk.TclError:
            pass

    def _recolor_widget_tree(self, widget, bg, card_bg, bg_dark, text_primary, text_secondary, text_muted):
        success = get_color("SUCCESS_COLOR")
        warning = get_color("WARNING_COLOR")
        danger = get_color("DANGER_COLOR")
        bg_map = {"#F1F5F9": bg, "#FFFFFF": card_bg, "#E2E8F0": bg_dark, "#F8FAFC": card_bg,
                  "#0F172A": bg, "#1E293B": card_bg, "#334155": bg_dark, "#020617": bg}
        fg_map = {"#1E293B": text_primary, "#64748B": text_secondary, "#94A3B8": text_muted,
                  "#555": text_secondary, "#777": text_muted, "#2c3e50": text_primary,
                  "#F1F5F9": text_primary, "#FFFFFF": text_primary, "#CCCCCC": text_muted,
                  "#059669": success, "#10B981": success,
                  "#D97706": warning, "#F59E0B": warning,
                  "#DC2626": danger, "#EF4444": danger}
        try:
            if isinstance(widget, (tk.Frame, tk.Label, tk.Button, tk.Canvas, tk.Text)):
                cbg = widget.cget("bg")
                if cbg in bg_map:
                    widget.configure(bg=bg_map[cbg])
                cfg = widget.cget("fg")
                if cfg in fg_map:
                    widget.configure(fg=fg_map[cfg])
        except tk.TclError:
            pass
        try:
            for child in widget.winfo_children():
                self._recolor_widget_tree(child, bg, card_bg, bg_dark, text_primary, text_secondary, text_muted)
        except tk.TclError:
            pass

    def reload_current_page(self):
        if self._current_page:
            key = self._current_page
            if key in self._pages:
                del self._pages[key]
            for widget in self.content.winfo_children():
                widget.destroy()
            self._navigate(key)

    def _navigate(self, page_key):
        for widget in self.content.winfo_children():
            widget.destroy()

        if not models.get_active_file():
            page = WelcomePage(self.content,
                               on_new_file=self._new_file,
                               on_open_file=self._open_file_dialog)
            page.pack(fill=tk.BOTH, expand=True)
            self._current_page = None
            self.set_status("No file open - create or open a workbook", "info")
            return

        for key, btn in self._nav_buttons.items():
            btn.configure(bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                          font=(FONT_FAMILY, FONT_SIZE_LG))
            ind = self._nav_indicators.get(key)
            if ind:
                ind.configure(bg=SIDEBAR_BG)

        if page_key in self._nav_buttons:
            self._nav_buttons[page_key].configure(
                bg=SIDEBAR_ACTIVE_BG, fg=SIDEBAR_ACTIVE_FG,
                font=(FONT_FAMILY, FONT_SIZE_LG, "bold"))
            ind = self._nav_indicators.get(page_key)
            if ind:
                ind.configure(bg=SIDEBAR_ACCENT)

        page_map = {
            "dashboard": DashboardPage,
            "suppliers": SuppliersPage,
            "purchases": PurchasesPage,
            "stock": StockPage,
            "sales": SalesPage,
            "customers": CustomersPage,
            "extra_income": ExtraIncomePage,
            "preorders": PreordersPage,
            "reports": ReportsPage,
            "settings": SettingsPage,
        }

        page_class = page_map.get(page_key)
        if page_class:
            self._current_page = page_key
            page = page_class(self.content)
            page.pack(fill=tk.BOTH, expand=True)
            self._pages[page_key] = page

        nav_name = dict(NAV_ITEMS).get(page_key, page_key.capitalize())
        self.set_status(f"Navigated to {nav_name.split('  ')[-1]}", "info")

    def _update_file_label(self):
        fp = models.get_active_file()
        if fp:
            import os
            base = os.path.basename(fp)
            self.file_label.config(text=f"\u25C9  {base}")
            parent = os.path.dirname(fp)
            full = os.path.join(parent, base)
            truncated = full if len(full) <= 60 else f"...{full[-57:]}"
            self.status_file_lbl.config(text=truncated)
        else:
            self.file_label.config(text="No file open")
            self.status_file_lbl.config(text="No file open")

    def _initial_file_setup(self):
        logger.info("Initial file setup")

        if auto_update_on_launch():
            logger.info("Cached update found, auto-installing and exiting")
            self.after(500, self._force_quit_for_update)
            return

        last_file = get_setting("last_file", "")
        if last_file and os.path.exists(last_file):
            try:
                models.open_workbook(last_file)
                self._update_file_label()
                self._navigate("dashboard")
                self.toast.show(
                    f"Welcome back! Loaded: {os.path.basename(last_file)}",
                    "success", 3000)
                self._schedule_auto_update_check()
                self.after(2000, lambda: check_for_update_async(
                    callback=lambda r: self._queue_ui(self._on_update_check, r, False)))
                return
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning(f"Auto-open failed: {e}")

        choice = messagebox.askquestion(
            f"Welcome to {APP_NAME}",
            "Do you want to create a NEW Excel workbook?\n\n"
            "Click 'Yes' to create new, 'No' to browse existing.")
        if choice == "yes":
            try:
                path = models.create_new_workbook()
                messagebox.showinfo("Success", f"New workbook created:\n{path}")
                logger.info(f"Created new workbook: {path}")
            except (FileNotFoundError, OSError) as e:
                logger.exception("Failed to create workbook")
                messagebox.showerror("Error", f"Failed to create workbook: {e}")
        else:
            self._open_file_dialog()

        self._update_file_label()

        if models.get_active_file():
            self._navigate("dashboard")
            self.toast.show(f"Welcome to {APP_NAME}", "success", 3000)
            self._schedule_auto_update_check()
            self.after(2000, lambda: check_for_update_async(
                callback=lambda r: self._queue_ui(self._on_update_check, r, False)))

    def _schedule_auto_update_check(self):
        if self._update_auto_check_id:
            self.after_cancel(self._update_auto_check_id)
        self._update_auto_check_id = self.after(3600000, self._do_auto_update_check)

    def _poll_ui_queue(self):
        try:
            while True:
                func, args = self._ui_queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        self.after(100, self._poll_ui_queue)

    def _queue_ui(self, func, *args):
        self._ui_queue.put((func, args))

    def _do_auto_update_check(self):
        if needs_auto_check():
            check_for_update_async(callback=lambda r: self._queue_ui(self._on_update_check, r, False))
        self._schedule_auto_update_check()

    def check_updates_now(self, show_result=True):
        self._hide_update_bar()
        self.update_side_lbl.configure(text="\u231B  Checking...", bg=INFO_COLOR)
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        check_for_update_async(callback=lambda r: self._queue_ui(self._on_update_check, r, show_result))

    def _on_update_check(self, result, manual=False):
        if not result:
            if manual:
                self.toast.show("No internet connection. Will retry later.", "warning", 4000)
            self._update_sidebar_offline()
            return

        latest = result.get("latest_version", "")
        if latest:
            update_available_info(
                latest,
                result.get("download_url", ""),
                result.get("changelog", ""),
                result.get("release_date", ""),
                result.get("file_size_mb", 0),
                result.get("sha256_hash", ""),
            )

        if is_update_available():
            if must_update_now():
                self._force_auto_update(result)
            else:
                self._show_update_bar()
                if manual:
                    self._show_update_details_modal()
        else:
            if manual:
                self.toast.show(f"You're up to date (v{VERSION})", "success", 3000)
            self._update_sidebar_current()

    def _update_sidebar_current(self):
        self.update_side_lbl.pack_forget()

    def _update_sidebar_offline(self):
        self.update_side_lbl.configure(text="\u26A0  Offline - tap to retry", bg=WARNING_COLOR)
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.update_side_lbl.bind("<Button-1>", lambda e: self.check_updates_now(show_result=False))

    def _hide_update_bar(self):
        self.update_bar.pack_forget()

    def _force_auto_update(self, result):
        status = get_update_status()
        url = status.get("download_url", "")
        if not url:
            url = result.get("download_url", "") if result else ""

        self._show_sidebar_update_badge(status)
        self._force_download_and_install(status)

    def _force_download_and_install(self, status):
        url = status.get("download_url", "")
        if not url:
            self._open_update_url("")
            self._force_quit_for_update()
            return

        body = self.show_modal("Mandatory Update", width=500, height=220)
        tk.Label(body, text=f"A critical update (v{status['latest_version']}) is available.",
                 font=(FONT_FAMILY, 12, "bold"),
                 bg=CARD_BG, fg=DANGER_COLOR).pack(pady=(12, 4))
        tk.Label(body, text="This update is mandatory. Downloading now...\n"
                            "The app will restart automatically when ready.",
                 font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_SECONDARY,
                 justify=tk.LEFT).pack(pady=(0, 8))

        progress_frame = tk.Frame(body, bg=CARD_BG)
        progress_frame.pack(fill=tk.X, pady=5)

        progress_var = tk.IntVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var,
                                       maximum=100, length=420)
        progress_bar.pack(pady=5)

        status_lbl = tk.Label(progress_frame, text="Starting download...",
                              font=(FONT_FAMILY, 9), bg=CARD_BG, fg=TEXT_MUTED)
        status_lbl.pack()

        def poll_progress():
            state = get_update_status()
            prog = state.get("download_progress", 0)
            progress_var.set(prog)
            status_lbl.config(text=f"Downloading... {prog}%")
            if prog < 100:
                self.after(300, poll_progress)

        def on_download_complete(result):
            if result.get("success"):
                def _do_install():
                    progress_var.set(100)
                    status_lbl.config(text="Download complete! Verifying...")
                    filepath = result["path"]
                    expected_hash = status.get("sha256_hash", "")
                    if expected_hash and not verify_download(filepath, expected_hash):
                        messagebox.showerror("Verification Failed",
                                             "Downloaded file is corrupted or tampered with.\n"
                                             "Please download manually from our website.")
                        self.close_modal()
                        return
                    status_lbl.config(text="Installing update...")
                    self.after(800, lambda: self._apply_update_and_quit(filepath))
                self._queue_ui(_do_install)
            else:
                def _show_fail():
                    status_lbl.config(text="Download failed. Opening browser...")
                    self.toast.show("Auto-update failed. Opening download page.", "error", 5000)
                    self.close_modal()
                    self._open_update_url(url)
                    self.after(3000, self._force_quit_for_update)
                self._queue_ui(_show_fail)

        poll_progress()
        download_update_async(url, callback=on_download_complete)

    def _apply_update_and_quit(self, filepath):
        set_setting("window_geometry", self.geometry())
        try:
            from utils.single_instance import release_lock
            release_lock()
        except (FileNotFoundError, PermissionError, OSError):
            pass
        install_update(filepath)
        self.after(3000, self._force_quit_for_update)

    def _force_quit_for_update(self):
        logger.info("Quitting for update installation")
        set_setting("window_geometry", self.geometry())
        try:
            from utils.single_instance import release_lock
            release_lock()
        except (FileNotFoundError, PermissionError, OSError):
            pass
        stop_auto_backup()
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _show_update_bar(self):
        status = get_update_status()
        ver = status["latest_version"]
        self.update_text.set(
            f"  \u2B06  Update v{ver} available  |  "
            f"Your version: v{VERSION}  |  "
            f"Click 'Download & Install' to update automatically"
        )
        self.update_btn.configure(text="\u2B07  Download & Install",
                                  command=lambda: self._direct_download_and_install(status))
        self.update_btn.bind("<Button-1>", lambda e: self._direct_download_and_install(status))
        self.update_btn.bind("<Enter>", lambda e: self.update_btn.configure(bg="#e67e22"))
        self.update_btn.bind("<Leave>", lambda e: self.update_btn.configure(bg="#d35400"))
        self.update_bar.pack(side=tk.TOP, fill=tk.X, before=self.content)
        self._show_sidebar_update_badge(status)

    def _direct_download_and_install(self, status):
        self._hide_update_bar()
        self._force_download_and_install(status)

    def _show_update_details_modal(self):
        status = get_update_status()
        body = self.show_modal(f"Update Available - v{status['latest_version']}", width=520, height=400)

        info_frame = tk.Frame(body, bg=CARD_BG, padx=10, pady=10)
        info_frame.pack(fill=tk.X)

        info_items = [
            ("Current Version", f"v{status['current_version']}"),
            ("Latest Version", f"v{status['latest_version']}"),
        ]
        if status.get("release_date"):
            info_items.append(("Release Date", status["release_date"]))
        if status.get("file_size_mb"):
            info_items.append(("File Size", f"{status['file_size_mb']} MB"))
        if status.get("min_version") and status.get("min_version") != "":
            info_items.append(("Minimum Version", f"v{status['min_version']} (mandatory)"))

        for i, (label, value) in enumerate(info_items):
            tk.Label(info_frame, text=label + ":", font=(FONT_FAMILY, 10, "bold"),
                     bg=CARD_BG, fg="#555").grid(row=i, column=0, sticky="w", pady=2, padx=(0, 10))
            tk.Label(info_frame, text=value, font=(FONT_FAMILY, 10),
                     bg=CARD_BG, fg="#2c3e50").grid(row=i, column=1, sticky="w", pady=2)

        changelog = status.get("changelog", "")
        if changelog:
            sep = tk.Frame(body, bg="#e0e0e0", height=1)
            sep.pack(fill=tk.X, pady=8)
            tk.Label(body, text="What's new:", font=(FONT_FAMILY, 10, "bold"),
                     bg=CARD_BG, fg="#555").pack(anchor="w", padx=10)
            text_box = tk.Text(body, font=(FONT_FAMILY, 9), bg=CARD_BG,
                               fg="#2c3e50", wrap=tk.WORD, height=6,
                               relief=tk.FLAT, borderwidth=0)
            text_box.insert("1.0", changelog)
            text_box.configure(state="disabled")
            text_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        btn_frame = tk.Frame(body, bg=CARD_BG)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        def do_update():
            self.close_modal()
            self._force_download_and_install(status)

        if must_update_now():
            tk.Label(btn_frame, text="Mandatory update - you must update to continue",
                     font=(FONT_FAMILY, 9, "bold"), bg=CARD_BG, fg=DANGER_COLOR).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="\u2B07  Download & Install Now", command=do_update).pack(side=tk.RIGHT, padx=5)
        else:
            ttk.Button(btn_frame, text="\u2B07  Download & Install", command=do_update).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="\u2197  Open Browser", command=lambda: self._open_update_url(status.get("download_url", ""))).pack(side=tk.LEFT, padx=5)

    def _show_sidebar_update_badge(self, status):
        ver = status.get("latest_version", "")
        mandatory = must_update_now()
        if mandatory:
            self.update_side_lbl.configure(
                bg=DANGER_COLOR, text=f"\u26A0  UPDATE REQUIRED v{ver}")
        else:
            self.update_side_lbl.configure(
                bg=WARNING_COLOR, text=f"\u2B06  Update v{ver} available")
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.update_side_lbl.bind("<Button-1>", lambda e: self._show_update_details_modal())

    def _dismiss_update(self):
        self._hide_update_bar()
        self.update_side_lbl.pack_forget()

    def _open_update_url(self, url):
        import webbrowser
        if url:
            webbrowser.open(url)
        else:
            webbrowser.open(RELEASE_BASE_URL)

    def show_modal(self, title, width=500, height=400):
        card_bg = get_color("CARD_BG")
        card_border = get_color("CARD_BORDER")
        primary = get_color("PRIMARY_COLOR")
        sidebar_accent = get_color("SIDEBAR_ACCENT")
        danger = get_color("DANGER_COLOR")

        overlay = tk.Frame(self, bg=MODAL_OVERLAY)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        overlay.bind("<Button-1>", lambda e: "break")
        overlay.bind("<ButtonRelease-1>", lambda e: "break")
        overlay.bind("<Key>", lambda e: "break")
        overlay.focus_set()
        overlay.grab_set()

        dialog = tk.Frame(overlay, bg=card_bg,
                           highlightbackground=card_border,
                           highlightthickness=1,
                           highlightcolor=card_border)
        dialog.place(relx=0.5, rely=0.5, anchor="center")
        dialog.configure(width=width, height=height)
        dialog.pack_propagate(False)

        title_frame = tk.Frame(dialog, bg=primary, height=36)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        accent_line = tk.Frame(title_frame, bg=sidebar_accent, height=2)
        accent_line.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(title_frame, text=title,
                 font=(FONT_FAMILY, FONT_SIZE_LG, "bold"),
                 bg=primary, fg="white").pack(side=tk.LEFT, padx=14, pady=4)
        close_btn = tk.Label(title_frame, text="\u2715",
                             font=(FONT_FAMILY, FONT_SIZE_LG),
                             bg=primary, fg="white",
                             padx=12, cursor="hand2")
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.close_modal())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(bg=danger))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(bg=primary))

        body = tk.Frame(dialog, bg=card_bg, padx=20, pady=15)
        body.pack(fill=tk.BOTH, expand=True)

        def on_escape(e):
            self.close_modal()
        dialog.bind("<Escape>", on_escape)
        body.bind("<Escape>", on_escape)

        self._modal_overlay = overlay
        self._modal_dialog = dialog
        self._modal_body = body
        return body

    def close_modal(self):
        if hasattr(self, '_modal_overlay') and self._modal_overlay:
            try:
                self._modal_overlay.grab_release()
            except tk.TclError:
                pass
            try:
                self._modal_overlay.destroy()
            except tk.TclError:
                pass
            self._modal_overlay = None
            self._modal_dialog = None
            self._modal_body = None

    def _open_file_dialog(self):
        path = filedialog.askopenfilename(
            title="Select Excel Workbook",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if path:
            self.show_loading("Opening workbook...")
            try:
                models.open_workbook(path)
                self._update_file_label()
                logger.info(f"Opened workbook: {path}")
                for page in self._pages.values():
                    if hasattr(page, "refresh"):
                        page.refresh()
                self.toast.show("Workbook loaded successfully", "success")
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.exception("Failed to open workbook")
                messagebox.showerror("Error", f"Failed to open workbook: {e}")
            finally:
                self.hide_loading()

    def _do_backup(self):
        if not models.get_active_file():
            messagebox.showwarning("No File", "Open a workbook first!")
            return
        self.show_loading("Creating backup...")
        try:
            path = backup_database()
            if path:
                logger.info(f"Backup created: {path}")
                messagebox.showinfo("Backup", f"Backed up to:\n{path}")
            else:
                messagebox.showerror("Error", "Backup failed")
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.exception("Backup failed")
            messagebox.showerror("Error", f"Backup failed: {e}")
        finally:
            self.hide_loading()

    def _iconify(self):
        self.iconify()

    def _on_close(self):
        if not messagebox.askokcancel("Quit", f"Are you sure you want to quit {APP_NAME}?"):
            return
        logger.info("Application shutting down")
        set_setting("window_geometry", self.geometry())
        try:
            create_backup()
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"Backup on exit failed: {e}")
        stop_auto_backup()
        try:
            from utils.single_instance import release_lock
            release_lock()
        except (FileNotFoundError, PermissionError, OSError):
            pass
        try:
            if models.get_active_file():
                backup_database()
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"Backup on exit failed: {e}")
        self.destroy()
