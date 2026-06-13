import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
from config import (
    APP_NAME, APP_GEOMETRY,
    SIDEBAR_BG, SIDEBAR_FG, SIDEBAR_ACTIVE, SIDEBAR_HOVER,
    BG_COLOR, CARD_BG, FONT_FAMILY, ACCENT_COLOR,
    PRIMARY_COLOR, PRIMARY_LIGHT, ACCENT_LIGHT,
    DANGER_COLOR, WARNING_COLOR, SUCCESS_COLOR,
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

        self.after(300, self._initial_file_setup)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_custom_titlebar(self):
        tb = tk.Frame(self, bg=PRIMARY_COLOR, height=32)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)

        tb.bind("<Button-1>", self._start_move)
        tb.bind("<B1-Motion>", self._do_move)
        tb.bind("<Double-Button-1>", self._toggle_maximize)

        icon_lbl = tk.Label(tb, text="\u25A3", font=(FONT_FAMILY, 12),
                            bg=PRIMARY_COLOR, fg=ACCENT_COLOR, padx=8)
        icon_lbl.pack(side=tk.LEFT)
        icon_lbl.bind("<Button-1>", self._start_move)
        icon_lbl.bind("<B1-Motion>", self._do_move)

        try:
            from pathlib import Path
            from config import ICON_PNG_PATH
            if ICON_PNG_PATH and Path(ICON_PNG_PATH).exists():
                sm_icon = tk.PhotoImage(file=ICON_PNG_PATH).subsample(4, 4)
                logo_lbl = tk.Label(tb, image=sm_icon, bg=PRIMARY_COLOR)
                logo_lbl.image = sm_icon
                logo_lbl.pack(side=tk.LEFT, padx=(0, 4))
                logo_lbl.bind("<Button-1>", self._start_move)
                logo_lbl.bind("<B1-Motion>", self._do_move)
        except Exception:
            pass

        title_lbl = tk.Label(tb, text=f"  {APP_NAME}",
                             font=(FONT_FAMILY, 10, "bold"),
                             bg=PRIMARY_COLOR, fg="white")
        title_lbl.pack(side=tk.LEFT)
        title_lbl.bind("<Button-1>", self._start_move)
        title_lbl.bind("<B1-Motion>", self._do_move)

        self._titlebar = tb

        btn_frame = tk.Frame(tb, bg=PRIMARY_COLOR)
        btn_frame.pack(side=tk.RIGHT, padx=4)

        self._create_title_button(btn_frame, "\u2014", 12, self._iconify,
                                  "#2d2d44", "#3d3d5c")
        self._max_btn = self._create_title_button(
            btn_frame, "\u25A1", 10, self._toggle_maximize,
            "#2d2d44", "#3d3d5c"
        )
        self._create_title_button(btn_frame, "\u2715", 12, self._on_close,
                                  "#c0392b", "#e74c3c")

    def _create_title_button(self, parent, text, font_size, cmd, bg, hover_bg):
        btn = tk.Label(parent, text=text, font=(FONT_FAMILY, font_size),
                       bg=bg, fg="white", padx=8, pady=2, cursor="hand2")
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
        sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=210)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        header_frame = tk.Frame(sidebar, bg=PRIMARY_COLOR, height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="\u25A3  Accounting Pro",
                 font=(FONT_FAMILY, 13, "bold"),
                 bg=PRIMARY_COLOR, fg="white").pack(pady=12)

        nav_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        nav_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        for key, label in NAV_ITEMS:
            btn = tk.Label(
                nav_frame, text=label,
                font=(FONT_FAMILY, 11),
                bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                anchor="w", padx=20, pady=10,
                cursor="hand2",
            )
            btn.pack(fill=tk.X)
            btn.bind("<Button-1>", lambda e, k=key: self._navigate(k))
            btn.bind("<Enter>", lambda e, b=btn: self._on_nav_hover(b))
            btn.bind("<Leave>", lambda e, b=btn: self._on_nav_leave(b))
            self._nav_buttons[key] = btn

        bottom_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        for icon, text, cmd in [
            ("\u2B07", "  Open File", self._open_file_dialog),
            ("\u21BA", "  Backup", self._do_backup),
        ]:
            btn = tk.Label(bottom_frame, text=f"{icon}{text}",
                           font=(FONT_FAMILY, 10),
                           bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                           anchor="w", padx=20, pady=8,
                           cursor="hand2")
            btn.pack(fill=tk.X)
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=SIDEBAR_HOVER, fg="white"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=SIDEBAR_BG, fg=SIDEBAR_FG))

        self.file_label = tk.Label(bottom_frame, text="No file open",
                                   font=(FONT_FAMILY, 8),
                                   bg=SIDEBAR_BG, fg="#666",
                                   anchor="w", padx=20, pady=2)
        self.file_label.pack(fill=tk.X)

        self.update_side_lbl = tk.Label(bottom_frame, text="",
            font=(FONT_FAMILY, 9, "bold"),
            bg=WARNING_COLOR, fg="white",
            anchor="center", padx=10, pady=6,
            cursor="hand2")
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.update_side_lbl.pack_forget()



    def _on_nav_hover(self, btn):
        if btn.cget("bg") != SIDEBAR_ACTIVE:
            btn.configure(bg=SIDEBAR_HOVER, fg="white")

    def _on_nav_leave(self, btn):
        if btn.cget("bg") != SIDEBAR_ACTIVE:
            btn.configure(bg=SIDEBAR_BG, fg=SIDEBAR_FG)

    def _setup_content(self):
        self.update_bar = tk.Frame(self, bg=WARNING_COLOR, height=32)
        self.update_text = tk.StringVar()
        self.update_lbl = tk.Label(
            self.update_bar, textvariable=self.update_text,
            font=(FONT_FAMILY, 9), bg=WARNING_COLOR, fg="white", anchor="w")
        self.update_lbl.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)
        self.update_btn = tk.Label(
            self.update_bar, text="Update Now \u2197",
            font=(FONT_FAMILY, 9, "bold"), bg="#d35400", fg="white",
            padx=10, cursor="hand2")
        self.update_btn.pack(side=tk.RIGHT, padx=4)
        self.dismiss_btn = tk.Label(
            self.update_bar, text="\u2715",
            font=(FONT_FAMILY, 9), bg=WARNING_COLOR, fg="white",
            padx=8, cursor="hand2")
        self.dismiss_btn.pack(side=tk.RIGHT)
        self.update_bar.pack_forget()

        self.content = tk.Frame(self, bg=BG_COLOR)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TLabel", background=BG_COLOR, foreground="#2c3e50",
                        font=(FONT_FAMILY, 10))
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabelframe", background=BG_COLOR, foreground="#2c3e50")
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground="#2c3e50",
                        font=(FONT_FAMILY, 10, "bold"))
        style.configure("TButton", font=(FONT_FAMILY, 10), padding=(12, 6))
        style.configure("Treeview", background=CARD_BG, foreground="#2c3e50",
                        fieldbackground=CARD_BG, font=(FONT_FAMILY, 10),
                        rowheight=30)
        style.configure("Treeview.Heading", font=(FONT_FAMILY, 10, "bold"),
                        background=ACCENT_COLOR, foreground="white",
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[("active", ACCENT_LIGHT)])
        style.map("TButton",
                  background=[("active", ACCENT_LIGHT)],
                  foreground=[("active", "white")])
        style.configure("TEntry", font=(FONT_FAMILY, 10), padding=4)
        style.configure("TCombobox", font=(FONT_FAMILY, 10), padding=4)

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
                          font=(FONT_FAMILY, 11))

        if page_key in self._nav_buttons:
            self._nav_buttons[page_key].configure(
                bg=SIDEBAR_ACTIVE, fg="white",
                font=(FONT_FAMILY, 11, "bold"))

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

        check_for_update_async(callback=self._on_update_check)

    def _on_update_check(self, result):
        if not result:
            self._check_force_update()
            return
        latest = result.get("latest_version", "")
        if latest:
            update_available_info(
                latest,
                result.get("download_url", ""),
                result.get("changelog", ""),
            )
        self._check_force_update()
        if is_update_available():
            self._show_update_bar()

    def _check_force_update(self):
        status = get_update_status()
        if status["force_update"]:
            mark_notified()
            self._show_sidebar_update_badge(status)
            self._show_force_update_dialog(status)

    def _show_update_bar(self):
        status = get_update_status()
        days = status["days_remaining"]
        ver = status["latest_version"]
        self.update_text.set(
            f"  Update available: v{ver}  |  "
            f"Must update within {days} days"
        )
        self.update_btn.bind(
            "<Button-1>", lambda e: self._download_update(status["download_url"]))
        self.update_btn.bind(
            "<Enter>", lambda e: self.update_btn.configure(bg="#e67e22"))
        self.update_btn.bind(
            "<Leave>", lambda e: self.update_btn.configure(bg="#d35400"))
        self.dismiss_btn.bind("<Button-1>", lambda e: self._dismiss_update())
        self.update_bar.pack(side=tk.TOP, fill=tk.X, before=self.content)
        self._show_sidebar_update_badge(status)
        mark_notified()

    def _show_sidebar_update_badge(self, status):
        ver = status["latest_version"]
        days = status["days_remaining"]
        text = f"\u26A0  Update v{ver}"
        self.update_side_lbl.configure(text=text)
        if status["force_update"]:
            self.update_side_lbl.configure(bg=DANGER_COLOR,
                text=f"\u26A0  UPDATE REQUIRED")
        else:
            self.update_side_lbl.configure(
                bg=WARNING_COLOR if days > 3 else DANGER_COLOR,
                text=f"\u26A0  Update v{ver} ({days}d)")
        self.update_side_lbl.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.update_side_lbl.bind(
            "<Button-1>", lambda e: self._show_update_dialog_from_sidebar())

    def _show_update_dialog_from_sidebar(self):
        status = get_update_status()
        if status["force_update"]:
            self._show_force_update_dialog(status)
        else:
            self._download_update(status["download_url"])

    def _dismiss_update(self):
        self.update_bar.pack_forget()

    def _show_force_update_dialog(self, status):
        result = messagebox.askyesno(
            "Update Required",
            f"A newer version (v{status['latest_version']}) is available.\n\n"
            f"Your version: v{status['current_version']}\n\n"
            "You must update to continue using this application.\n"
            "Would you like to download the update now?",
            icon="warning",
        )
        if result:
            self._download_update(status["download_url"])
        else:
            messagebox.showwarning(
                "Update Required",
                "Please update to the latest version to continue.\n"
                "The application will now close.",
            )
            self._on_close()

    def _download_update(self, url):
        if url:
            import webbrowser
            webbrowser.open(url)
        else:
            messagebox.showinfo(
                "Update",
                f"Please download the latest version from:\n"
                f"https://github.com/ramlalitsharma/BasicAccountingAPP/releases"
            )

    def show_modal(self, title, width=500, height=400):
        overlay = tk.Frame(self.content, bg="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        overlay.bind("<Button-1>", lambda e: "break")
        overlay.bind("<ButtonRelease-1>", lambda e: "break")

        dialog = tk.Frame(overlay, bg=CARD_BG, highlightbackground="#ccc",
                           highlightthickness=1)
        dialog.place(relx=0.5, rely=0.5, anchor="center")
        dialog.configure(width=width, height=height)
        dialog.pack_propagate(False)

        title_frame = tk.Frame(dialog, bg=PRIMARY_COLOR, height=34)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text=title,
                 font=(FONT_FAMILY, 11, "bold"),
                 bg=PRIMARY_COLOR, fg="white").pack(side=tk.LEFT, padx=12, pady=4)
        close_btn = tk.Label(title_frame, text="\u2715",
                             font=(FONT_FAMILY, 10),
                             bg=PRIMARY_COLOR, fg="white",
                             padx=10, cursor="hand2")
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.close_modal())

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
