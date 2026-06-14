import tkinter as tk
from tkinter import ttk, messagebox
from config import (
    ACCENT_COLOR, ACCENT_LIGHT, FONT_FAMILY, APP_NAME, VERSION,
    USER_DATA_DIR, update_data_dir, TEXT_PRIMARY, TEXT_MUTED,
    FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL,
)
from utils.company import load_company, save_company
from utils.update_checker import get_update_status, RELEASE_BASE_URL


class SettingsPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._app = self.winfo_toplevel()
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Settings",
                           font=("Segoe UI", 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._general_tab(notebook)
        self._company_tab(notebook)
        self._updates_tab(notebook)

    def _general_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  General  ")

        ttk.Label(frame, text="Currency Symbol",
                  font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", pady=8)
        self.currency_var = tk.StringVar(value="\u20B9")
        ttk.Entry(frame, textvariable=self.currency_var, width=10).grid(
            row=0, column=1, sticky="w", padx=10)

        ttk.Label(frame, text="Theme",
                  font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=8)
        self.theme_var = tk.StringVar(value="Light")
        ttk.Combobox(frame, textvariable=self.theme_var,
                     values=["Light", "Dark"], state="readonly", width=12).grid(
            row=1, column=1, sticky="w", padx=10)
        self.theme_var.trace_add("write", self._toggle_theme)

        ttk.Separator(frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(frame, text="Data Location",
                  font=("Segoe UI", 11)).grid(row=3, column=0, sticky="nw", pady=8)
        self.data_dir_var = tk.StringVar(value=str(USER_DATA_DIR))
        data_entry = ttk.Entry(frame, textvariable=self.data_dir_var, width=45)
        data_entry.grid(row=3, column=1, sticky="w", padx=10)
        ttk.Button(frame, text="Browse...",
                   command=self._browse_data_dir).grid(row=3, column=2, padx=5)

        ttk.Separator(frame, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(frame, text="About",
                  font=("Segoe UI", 11)).grid(row=5, column=0, sticky="w", pady=8)
        ttk.Label(frame,
                  text=f"{APP_NAME} v{VERSION}\n"
                       "Built with Python & Tkinter\n"
                       "Database: Microsoft Excel (.xlsx)",
                  foreground="#777").grid(row=5, column=1, sticky="w", padx=10)

    def _updates_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Updates  ")

        row = 0
        ttk.Label(frame, text="Update Settings",
                  font=("Segoe UI", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row += 1

        status = get_update_status()

        info_items = [
            ("Current Version", f"v{VERSION}"),
            ("Latest Available", f"v{status['latest_version']}" if status['latest_version'] else "Not checked"),
            ("Last Checked", status['last_check'] if status['last_check'] else "Never"),
            ("Online Status", "\u2713 Online" if status['is_online_now'] else "\u2717 Offline"),
        ]
        for label, value in info_items:
            ttk.Label(frame, text=label + ":",
                      font=("Segoe UI", 10, "bold")).grid(
                row=row, column=0, sticky="w", pady=3, padx=(0, 15))
            ttk.Label(frame, text=value,
                      font=("Segoe UI", 10)).grid(
                row=row, column=1, sticky="w", pady=3)
            row += 1

        row += 1
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="w")

        def check_now():
            self._app.check_updates_now(True)

        ttk.Button(btn_frame, text="\u21BB  Check for Updates Now",
                   command=check_now).pack(side=tk.LEFT, padx=5)

        def open_releases():
            import webbrowser
            webbrowser.open(RELEASE_BASE_URL)

        ttk.Button(btn_frame, text="\u2197  View All Releases",
                   command=open_releases).pack(side=tk.LEFT, padx=5)

        history = status.get("update_history", [])
        if history and isinstance(history, list) and len(history) > 0:
            row += 2
            sep = ttk.Separator(frame, orient="horizontal")
            sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
            row += 1

            ttk.Label(frame, text="Update History",
                      font=("Segoe UI", 11, "bold")).grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))
            row += 1

            tree_frame = ttk.Frame(frame)
            tree_frame.grid(row=row, column=0, columnspan=2, sticky="nsew")
            frame.grid_rowconfigure(row, weight=1)
            frame.grid_columnconfigure(1, weight=1)

            cols = ["Version", "Detected At", "Highlights"]
            tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=5)
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            tree.column("Highlights", width=250)

            for h in reversed(history[-10:]):
                tree.insert("", tk.END, values=[
                    h.get("version", ""),
                    h.get("detected_at", ""),
                    h.get("changelog", "")[:60],
                ])

            scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _company_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Company  ")
        company = load_company()

        fields = [
            ("Business Name", "name", 35),
            ("Address", "address", 45),
            ("City", "city", 25),
            ("State", "state", 25),
            ("Pincode", "pincode", 15),
            ("Phone", "phone", 20),
            ("Email", "email", 30),
            ("GSTIN", "gstin", 25),
            ("PAN", "pan", 20),
            ("Invoice Prefix", "invoice_prefix", 10),
        ]

        self._company_fields = {}
        for i, (label, key, width) in enumerate(fields):
            ttk.Label(frame, text=label,
                      font=("Segoe UI", 10)).grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            entry = ttk.Entry(frame, width=width)
            entry.insert(0, company.get(key, ""))
            entry.grid(row=i, column=1, sticky="w", pady=4)
            self._company_fields[key] = entry

        ttk.Label(frame, text="Invoice Footer Note",
                  font=("Segoe UI", 10)).grid(
            row=len(fields), column=0, sticky="w", pady=8, padx=(0, 10))
        self.inv_note_text = tk.Text(frame, width=40, height=3,
                                     font=(FONT_FAMILY, 10))
        self.inv_note_text.insert("1.0", company.get("invoice_note", ""))
        self.inv_note_text.grid(row=len(fields), column=1, sticky="w", pady=8)

        ttk.Button(frame, text="\u2713  Save Company Details",
                   command=self._save_company).grid(
            row=len(fields) + 1, column=0, columnspan=2, pady=15)

    def _save_company(self):
        data = {}
        for key, entry in self._company_fields.items():
            data[key] = entry.get().strip()
        data["invoice_note"] = self.inv_note_text.get("1.0", "end-1c").strip()
        save_company(data)
        messagebox.showinfo("Saved", "Company details saved successfully")

    def _browse_data_dir(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Data Folder")
        if path:
            self.data_dir_var.set(path)
            update_data_dir(path)
            messagebox.showinfo("Data Location",
                                f"Data will now be saved to:\n{path}\n\n"
                                "Existing files must be moved manually.")

    def _toggle_theme(self, *args):
        from config import (
            BG_COLOR as OLD_BG, BG_DARK as OLD_BG_DARK,
            CARD_BG as OLD_CARD, TEXT_PRIMARY as OLD_FG,
            SIDEBAR_BG as OLD_SIDEBAR,
        )
        theme = self.theme_var.get()
        if theme == "Dark":
            bg, fg, card = "#1E293B", "#F1F5F9", "#334155"
            sidebar = "#0F172A"
        else:
            bg, fg, card = "#F1F5F9", "#1E293B", "#FFFFFF"
            sidebar = "#0F172A"

        self._app.configure(bg=bg)

        def apply_theme(widget):
            old_bgs = (OLD_BG, OLD_BG_DARK, OLD_CARD, "#2d2d2d", "#ffffff",
                       "#3d3d3d", "#1a1a2e", "#16213e", "#0f3460")
            old_fgs = (OLD_FG, "#2c3e50", "#ffffff", "#777", "#c8d6e5")
            try:
                if isinstance(widget, (tk.Label, tk.Frame, tk.Button)):
                    cbg = widget.cget("bg")
                    if cbg in old_bgs:
                        new_bg = card if cbg in (OLD_CARD, "#ffffff", "#3d3d3d") else (
                            sidebar if cbg in ("#1a1a2e", "#0f3460", "#16213e") else bg)
                        widget.configure(bg=new_bg)
                if isinstance(widget, (tk.Label, tk.Button)):
                    cfg = widget.cget("fg")
                    if cfg in old_fgs:
                        widget.configure(fg=fg)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                apply_theme(child)

        apply_theme(self._app)

        style = ttk.Style(self._app)
        style.theme_use("clam")
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("Treeview", background=card, foreground=fg,
                        fieldbackground=card)
