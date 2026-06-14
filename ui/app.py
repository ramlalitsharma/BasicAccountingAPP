import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
from config import (
    APP_NAME, APP_GEOMETRY, VERSION,
    SIDEBAR_BG, SIDEBAR_FG, SIDEBAR_ACTIVE_BG, SIDEBAR_ACTIVE_FG,
    SIDEBAR_HOVER_BG, SIDEBAR_ACCENT,
    BG_COLOR, BG_DARK, CARD_BG, CARD_BORDER, HEADER_BG,
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    FONT_SIZE_XL, FONT_SIZE_XXL,
    ACCENT_COLOR, ACCENT_LIGHT, ACCENT_DARK,
    PRIMARY_COLOR, PRIMARY_LIGHT,
    DANGER_COLOR, DANGER_LIGHT,
    WARNING_COLOR, WARNING_LIGHT,
    SUCCESS_COLOR, SUCCESS_LIGHT,
    INFO_COLOR, INFO_LIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    MODAL_OVERLAY, PADDING_SM, PADDING_MD, PADDING_LG, RADIUS,
    DATA_DIR, ICON_PATH, get_setting,
)
from database import models
from database.backup import backup_database
from ui.pages.dashboard import DashboardPage
from ui.pages.suppliers import SuppliersPage
from ui.pages.stock import StockPage
from ui.pages.sales import SalesPage
from ui.pages.reports import ReportsPage
from ui.pages.settings import SettingsPage
from ui.pages.customers import CustomersPage
from ui.pages.purchases import PurchasesPage
from ui.widgets.toast import Toast
from utils.update_checker import (
    check_for_update_async, get_update_status, mark_notified,
    update_available_info, is_update_available,
    skip_version, download_update_async,
    needs_auto_check, RELEASE_BASE_URL,
)

logger = logging.getLogger(__name__)

NAV_ITEMS = [
    ("dashboard", "\u25A3  Dashboard"),
    ("suppliers", "\u25C8  Suppliers"),
    ("purchases", "\u21BB  Purchases"),
    ("stock", "\u25A1  Stock"),
    ("sales", "\u20B9  Sales"),
    ("customers", "\u25CF  Customers"),
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
        try:
            if ICON_PATH and Path(ICON_PATH).exists():
                from pathlib import Path
                self.iconbitmap(default=ICON_PATH)
        except Exception:
            pass

        self._pages = {}
        self._current_page = None
        self._nav_buttons = {}
        self.toast = Toast(self)

        self._setup_custom_titlebar()
        self._setup_sidebar()
        self._setup_content()
        self._setup_styles()
        self._setup_keyboard_shortcuts()

        self._update_auto_check_id = None
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
            from pathlib import Path
            from config import ICON_PNG_PATH
            if ICON_PNG_PATH and Path(ICON_PNG_PATH).exists():
                sm_icon = tk.PhotoImage(file=ICON_PNG_PATH).subsample(3, 3)
                logo_lbl = tk.Label(tb, image=sm_icon, bg=PRIMARY_COLOR,
                                    cursor="fleur")
                logo_lbl.image = sm_icon
                logo_lbl.pack(side=tk.LEFT, padx=(8, 4))
                logo_lbl.bind("<Button-1>", self._start_move)
                logo_lbl.bind("<B1-Motion>", self._do_move)
        except Exception:
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

        self.status_bar = tk.Frame(self, bg=BG_DARK, height=26)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_text = tk.StringVar(value="Ready")
        tk.Label(self.status_bar, textvariable=self.status_text,
                 font=(FONT_FAMILY, FONT_SIZE_SM),
                 bg=BG_DARK, fg=TEXT_SECONDARY,
                 anchor="w", padx=12).pack(side=tk.LEFT)

        tk.Label(self.status_bar, text=f"v{VERSION}",
                 font=(FONT_FAMILY, FONT_SIZE_SM),
                 bg=BG_DARK, fg=TEXT_MUTED,
                 anchor="e", padx=12).pack(side=tk.RIGHT)


    def _on_nav_hover(self, btn, indicator):
        if btn.cget("bg") != SIDEBAR_ACTIVE_BG:
            btn.configure(bg=SIDEBAR_HOVER_BG, fg="white")

    def _on_nav_leave(self, btn, indicator):
        if btn.cget("bg") != SIDEBAR_ACTIVE_BG:
            btn.configure(bg=SIDEBAR_BG, fg=SIDEBAR_FG)

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
            self.update_bar, text="\u2715",
            font=(FONT_FAMILY, FONT_SIZE_MD), bg=WARNING_COLOR, fg="white",
            padx=8, cursor="hand2")
        self.dismiss_btn.pack(side=tk.RIGHT)
        self.update_bar.pack_forget()

        content_wrapper = tk.Frame(self, bg=BG_COLOR)
        content_wrapper.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.content = tk.Frame(content_wrapper, bg=BG_COLOR)
        self.content.pack(fill=tk.BOTH, expand=True)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        font_family = FONT_FAMILY

        style.configure(".", font=(font_family, FONT_SIZE_MD))

        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_PRIMARY,
                        font=(font_family, FONT_SIZE_MD))
        style.configure("Heading.TLabel", font=(font_family, FONT_SIZE_XXL, "bold"),
                        foreground=TEXT_PRIMARY)
        style.configure("SubHeading.TLabel", font=(font_family, FONT_SIZE_XL, "bold"),
                        foreground=TEXT_PRIMARY)
        style.configure("Muted.TLabel", foreground=TEXT_MUTED)
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_PRIMARY)

        style.configure("TFrame", background=BG_COLOR)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabelframe", background=CARD_BG, foreground=TEXT_PRIMARY)
        style.configure("TLabelframe.Label", background=CARD_BG, foreground=TEXT_PRIMARY,
                        font=(font_family, FONT_SIZE_MD, "bold"))

        style.configure("TButton", font=(font_family, FONT_SIZE_MD),
                        padding=(14, 7), background=ACCENT_COLOR,
                        foreground="white", borderwidth=0, focusthickness=0)
        style.map("TButton",
                  background=[("active", ACCENT_LIGHT), ("pressed", ACCENT_DARK)],
                  foreground=[("active", "white")])
        style.configure("Secondary.TButton", background=TEXT_SECONDARY)
        style.map("Secondary.TButton",
                   background=[("active", TEXT_MUTED)])

        style.configure("Treeview", background=CARD_BG, foreground=TEXT_PRIMARY,
                        fieldbackground=CARD_BG, font=(font_family, FONT_SIZE_MD),
                        rowheight=32, borderwidth=0)
        style.configure("Treeview.Heading", font=(font_family, FONT_SIZE_MD, "bold"),
                        background=ACCENT_COLOR, foreground="white",
                        relief="flat", borderwidth=0)
        style.map("Treeview.Heading",
                  background=[("active", ACCENT_LIGHT)])
        style.configure("Treeview", bordercolor=CARD_BORDER,
                        lightcolor=CARD_BORDER, darkcolor=CARD_BORDER)

        style.configure("TEntry", font=(font_family, FONT_SIZE_MD),
                        padding=6, fieldbackground=CARD_BG,
                        foreground=TEXT_PRIMARY, borderwidth=1)
        style.map("TEntry", fieldbackground=[("focus", "#FFFFFF")])

        style.configure("TCombobox", font=(font_family, FONT_SIZE_MD),
                        padding=4, fieldbackground=CARD_BG,
                        foreground=TEXT_PRIMARY)
        style.map("TCombobox", fieldbackground=[("focus", "#FFFFFF")])

        style.configure("TScrollbar", gripcount=0, background=BG_DARK,
                        troughcolor=BG_COLOR, borderwidth=0, arrowcolor=TEXT_MUTED)
        style.map("TScrollbar", background=[("active", ACCENT_LIGHT)])

    def _setup_keyboard_shortcuts(self):
        self.bind("<Control-q>", lambda e: self._on_close())
        self.bind("<Control-Q>", lambda e: self._on_close())
        for i, (key, _) in enumerate(NAV_ITEMS):
            num = i + 1
            if num < 10:
                self.bind(f"<Alt-Key-{num}>",
                          lambda e, k=key: self._navigate(k))

    def _navigate(self, page_key):
        for widget in self.content.winfo_children():
            widget.destroy()

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
            "reports": ReportsPage,
            "settings": SettingsPage,
        }

        page_class = page_map.get(page_key)
        if page_class:
            self._current_page = page_key
            page = page_class(self.content)
            page.pack(fill=tk.BOTH, expand=True)
            self._pages[page_key] = page
    def _update_file_label(self):
        fp = models.get_active_file()
        if fp:
            import os
            base = os.path.basename(fp)
            self.file_label.config(text=f"\u25C9  {base}")
        else:
            self.file_label.config(text="No file open")

    def _initial_file_setup(self):
        logger.info("Initial file setup")

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
                check_for_update_async(callback=self._on_update_check)
                return
            except Exception as e:
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
            except Exception as e:
                logger.error(f"Failed to create workbook: {e}")
                messagebox.showerror("Error", f"Failed to create workbook: {e}")
        else:
            self._open_file_dialog()

        self._update_file_label()

        self._navigate("dashboard")
        self.toast.show(f"Welcome to {APP_NAME}", "success", 3000)

        self._schedule_auto_update_check()
        check_for_update_async(callback=self._on_update_check)

    def _schedule_auto_update_check(self):
        if self._update_auto_check_id:
            self.after_cancel(self._update_auto_check_id)
        self._update_auto_check_id = self.after(3600000, self._do_auto_update_check)

    def _do_auto_update_check(self):
        if needs_auto_check():
            check_for_update_async(callback=self._on_update_check)
        self._schedule_auto_update_check()

    def check_updates_now(self, show_result=True):
        self._hide_update_bar()
        self.update_side_lbl.configure(text="\u231B  Checking...", bg=INFO_COLOR)
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        check_for_update_async(callback=lambda r: self._on_update_check(r, manual=show_result))

    def _on_update_check(self, result, manual=False):
        if not result:
            if manual:
                self.toast.show("No internet connection. Will retry later.", "warning", 4000)
            self._update_sidebar_offline()
            self._check_force_update()
            return

        latest = result.get("latest_version", "")
        if latest:
            update_available_info(
                latest,
                result.get("download_url", ""),
                result.get("changelog", ""),
                result.get("release_date", ""),
                result.get("file_size_mb", 0),
            )

        if is_update_available():
            self._show_update_bar()
            if manual:
                self._show_update_details_modal()
            mark_notified()
        else:
            if manual:
                self.toast.show(f"You're up to date (v{VERSION})", "success", 3000)
            self._update_sidebar_current()

        self._check_force_update()

    def _update_sidebar_current(self):
        self.update_side_lbl.pack_forget()

    def _update_sidebar_offline(self):
        self.update_side_lbl.configure(text="\u26A0  Offline - tap to retry", bg=WARNING_COLOR)
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.update_side_lbl.bind("<Button-1>", lambda e: self.check_updates_now(show_result=False))

    def _hide_update_bar(self):
        self.update_bar.pack_forget()

    def _check_force_update(self):
        status = get_update_status()
        if status["force_update"]:
            mark_notified()
            self._show_sidebar_update_badge(status)
            self._show_force_update_dialog(status)

    def _show_update_bar(self):
        status = get_update_status()
        ver = status["latest_version"]
        self.update_text.set(
            f"  \u2B06  Update v{ver} available  |  "
            f"Your version: v{VERSION}"
        )
        self.update_btn.configure(text="View Update", command=self._show_update_details_modal)
        self.update_btn.bind("<Button-1>", lambda e: self._show_update_details_modal())
        self.update_btn.bind("<Enter>", lambda e: self.update_btn.configure(bg="#e67e22"))
        self.update_btn.bind("<Leave>", lambda e: self.update_btn.configure(bg="#d35400"))
        self.dismiss_btn.bind("<Button-1>", lambda e: self._dismiss_update())
        self.update_bar.pack(side=tk.TOP, fill=tk.X, before=self.content)
        self._show_sidebar_update_badge(status)

    def _show_update_details_modal(self):
        status = get_update_status()
        body = self.show_modal(f"Update Available - v{status['latest_version']}", width=520, height=420)

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
            self._download_and_update(status)

        def skip():
            skip_version(status["latest_version"])
            self.close_modal()
            self._dismiss_update()
            self._update_sidebar_current()
            self.toast.show(f"Skipped v{status['latest_version']}", "info", 3000)

        ttk.Button(btn_frame, text="\u2B07  Download & Install", command=do_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="\u2716  Skip This Version", command=skip).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="\u2197  Open Browser", command=lambda: self._open_update_url(status["download_url"])).pack(side=tk.LEFT, padx=5)

    def _show_sidebar_update_badge(self, status):
        ver = status["latest_version"]
        text = f"\u2B06  Update v{ver}"
        self.update_side_lbl.configure(text=text)
        if status["force_update"]:
            self.update_side_lbl.configure(bg=DANGER_COLOR, text=f"\u26A0  UPDATE REQUIRED")
        else:
            days = status.get("days_remaining", 15)
            self.update_side_lbl.configure(
                bg=WARNING_COLOR if days > 3 else DANGER_COLOR,
                text=f"\u2B06  Update v{ver} ({days}d)")
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.update_side_lbl.bind("<Button-1>", lambda e: self._show_update_details_modal())

    def _dismiss_update(self):
        self._hide_update_bar()
        self.update_side_lbl.pack_forget()

    def _download_and_update(self, status):
        url = status.get("download_url", "")
        if not url:
            self._open_update_url("")
            return

        body = self.show_modal("Downloading Update...", width=450, height=160)
        tk.Label(body, text=f"Downloading v{status['latest_version']}...",
                 font=(FONT_FAMILY, 11, "bold"),
                 bg=CARD_BG, fg="#2c3e50").pack(pady=(10, 5))
        tk.Label(body, text="Please wait while the update is downloaded.",
                 font=(FONT_FAMILY, 9), bg=CARD_BG, fg="#777").pack()

        progress_frame = tk.Frame(body, bg=CARD_BG)
        progress_frame.pack(fill=tk.X, pady=(15, 0))

        progress_var = tk.IntVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var,
                                       maximum=100, length=380)
        progress_bar.pack(pady=5)

        status_lbl = tk.Label(progress_frame, text="Starting...",
                              font=(FONT_FAMILY, 8), bg=CARD_BG, fg="#999")
        status_lbl.pack()

        def poll_progress():
            state = get_update_status()
            prog = state.get("download_progress", 0)
            progress_var.set(prog)
            status_lbl.config(text=f"{prog}%")
            if prog < 100:
                self.after(200, poll_progress)

        def on_download_complete(result):
            if result.get("success"):
                progress_var.set(100)
                status_lbl.config(text="Download complete!")
                self.after(800, lambda: self._prompt_install(result["path"], status))
            else:
                status_lbl.config(text="Download failed")
                self.toast.show("Download failed. Try opening in browser.", "error", 4000)
                self.close_modal()
                self._open_update_url(url)

        poll_progress()
        download_update_async(url, callback=on_download_complete)

    def _prompt_install(self, filepath, status):
        self.close_modal()
        body = self.show_modal("Update Ready", width=420, height=160)
        tk.Label(body, text=f"v{status['latest_version']} downloaded!",
                 font=(FONT_FAMILY, 12, "bold"),
                 bg=CARD_BG, fg=SUCCESS_COLOR).pack(pady=(15, 5))
        tk.Label(body, text="The application will close to install the update.",
                 font=(FONT_FAMILY, 9), bg=CARD_BG, fg="#777").pack()

        btn_frame = tk.Frame(body, bg=CARD_BG)
        btn_frame.pack(pady=(15, 0))

        def do_install():
            self.close_modal()
            import subprocess
            try:
                subprocess.Popen([filepath], shell=True)
            except Exception:
                pass
            self._on_close()

        def install_later():
            self.close_modal()
            self.toast.show("Update will install on next launch", "info", 3000)

        ttk.Button(btn_frame, text="\u25B6  Install Now", command=do_install).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Later", command=install_later).pack(side=tk.LEFT, padx=5)

    def _open_update_url(self, url):
        import webbrowser
        if url:
            webbrowser.open(url)
        else:
            webbrowser.open(RELEASE_BASE_URL)

    def _show_force_update_dialog(self, status):
        self._dismiss_update()
        body = self.show_modal("Update Required", width=460, height=200)
        tk.Label(body, text="\u26A0  Your version is no longer supported",
                 font=(FONT_FAMILY, 12, "bold"),
                 bg=CARD_BG, fg=DANGER_COLOR).pack(pady=(12, 5))
        tk.Label(body,
                 text=f"v{status['current_version']} \u2192 v{status['latest_version']}\n\n"
                      "You must update to continue using this application.",
                 font=(FONT_FAMILY, 10), bg=CARD_BG, fg="#555", justify=tk.LEFT).pack(pady=5)

        def do_update():
            self.close_modal()
            self._download_and_update(status)

        def close_app():
            self.close_modal()
            self._on_close()

        btn_frame = tk.Frame(body, bg=CARD_BG)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="\u2B07  Update Now", command=do_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="\u2716  Exit", command=close_app).pack(side=tk.LEFT, padx=5)

    def show_modal(self, title, width=500, height=400):
        overlay = tk.Frame(self, bg=MODAL_OVERLAY)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        overlay.bind("<Button-1>", lambda e: "break")
        overlay.bind("<ButtonRelease-1>", lambda e: "break")
        overlay.bind("<Key>", lambda e: "break")
        overlay.focus_set()
        overlay.grab_set()

        dialog = tk.Frame(overlay, bg=CARD_BG,
                           highlightbackground=CARD_BORDER,
                           highlightthickness=1,
                           highlightcolor=CARD_BORDER)
        dialog.place(relx=0.5, rely=0.5, anchor="center")
        dialog.configure(width=width, height=height)
        dialog.pack_propagate(False)

        title_frame = tk.Frame(dialog, bg=PRIMARY_COLOR, height=36)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        accent_line = tk.Frame(title_frame, bg=SIDEBAR_ACCENT, height=2)
        accent_line.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(title_frame, text=title,
                 font=(FONT_FAMILY, FONT_SIZE_LG, "bold"),
                 bg=PRIMARY_COLOR, fg="white").pack(side=tk.LEFT, padx=14, pady=4)
        close_btn = tk.Label(title_frame, text="\u2715",
                             font=(FONT_FAMILY, FONT_SIZE_LG),
                             bg=PRIMARY_COLOR, fg="white",
                             padx=12, cursor="hand2")
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.close_modal())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(bg=DANGER_COLOR))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(bg=PRIMARY_COLOR))

        body = tk.Frame(dialog, bg=CARD_BG, padx=20, pady=15)
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
            except Exception:
                pass
            try:
                self._modal_overlay.destroy()
            except Exception:
                pass
            self._modal_overlay = None
            self._modal_dialog = None
            self._modal_body = None

    def _open_file_dialog(self):
        path = filedialog.askopenfilename(
            title="Select Excel Workbook",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if path:
            try:
                models.open_workbook(path)
                self._update_file_label()
                logger.info(f"Opened workbook: {path}")
                for page in self._pages.values():
                    if hasattr(page, "refresh"):
                        page.refresh()
                self.toast.show("Workbook loaded successfully", "success")
            except Exception as e:
                logger.error(f"Failed to open workbook: {e}")
                messagebox.showerror("Error", f"Failed to open workbook: {e}")

    def _do_backup(self):
        if not models.get_active_file():
            messagebox.showwarning("No File", "Open a workbook first!")
            return
        try:
            path = backup_database()
            if path:
                logger.info(f"Backup created: {path}")
                messagebox.showinfo("Backup", f"Backed up to:\n{path}")
            else:
                messagebox.showerror("Error", "Backup failed")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            messagebox.showerror("Error", f"Backup failed: {e}")

    def _iconify(self):
        self.iconify()

    def _on_close(self):
        logger.info("Application shutting down")
        try:
            from utils.single_instance import release_lock
            release_lock()
        except Exception:
            pass
        try:
            if models.get_active_file():
                backup_database()
        except Exception as e:
            logger.warning(f"Backup on exit failed: {e}")
        self.destroy()
