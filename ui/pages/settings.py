import tkinter as tk
from tkinter import ttk, messagebox
from config import (
    ACCENT_COLOR, ACCENT_LIGHT, FONT_FAMILY, APP_NAME, VERSION,
    USER_DATA_DIR, update_data_dir, TEXT_PRIMARY, TEXT_MUTED,
    FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL,
    get_setting, set_setting, CARD_BG, SUCCESS_COLOR,
)
from utils.company import load_company, save_company
from utils.update_checker import get_update_status
from config import RELEASE_BASE_URL
from database.backup import start_auto_backup, stop_auto_backup
from utils.license import license_manager, TIERS


class SettingsPage(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._app = self.winfo_toplevel()
        self._build_ui()

    def _build_ui(self):
        header = ttk.Label(self, text="Settings",
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=20, pady=(20, 10))

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self._general_tab(self._notebook)
        self._business_tab(self._notebook)
        self._vertical_tab(self._notebook)
        self._features_tab(self._notebook)
        self._tax_tab(self._notebook)
        self._company_tab(self._notebook)
        self._backup_tab(self._notebook)
        self._license_tab(self._notebook)
        self._updates_tab(self._notebook)

    def _general_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  General  ")

        ttk.Label(frame, text="Currency Symbol",
                  font=(FONT_FAMILY, 11)).grid(row=0, column=0, sticky="w", pady=8)
        self.currency_var = tk.StringVar(value=get_setting("currency_symbol", "\u20B9"))
        ttk.Entry(frame, textvariable=self.currency_var, width=10).grid(
            row=0, column=1, sticky="w", padx=10)

        ttk.Label(frame, text="Theme",
                  font=(FONT_FAMILY, 11)).grid(row=1, column=0, sticky="w", pady=8)
        self.theme_var = tk.StringVar(value=get_setting("theme", "Light"))
        ttk.Combobox(frame, textvariable=self.theme_var,
                     values=["Light", "Dark"], state="readonly", width=12).grid(
            row=1, column=1, sticky="w", padx=10)
        self.theme_var.trace_add("write", self._toggle_theme)

        ttk.Separator(frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(frame, text="Data Location",
                  font=(FONT_FAMILY, 11)).grid(row=3, column=0, sticky="nw", pady=8)
        self.data_dir_var = tk.StringVar(value=str(USER_DATA_DIR))
        data_entry = ttk.Entry(frame, textvariable=self.data_dir_var, width=45)
        data_entry.grid(row=3, column=1, sticky="w", padx=10)
        ttk.Button(frame, text="Browse...",
                   command=self._browse_data_dir).grid(row=3, column=2, padx=5)

        ttk.Separator(frame, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(frame, text="About",
                  font=(FONT_FAMILY, 11)).grid(row=5, column=0, sticky="w", pady=8)
        ttk.Label(frame,
                  text=f"{APP_NAME} v{VERSION}\n"
                       "Built with Python & Tkinter\n"
                       "Database: Microsoft Excel (.xlsx)",
                  foreground="#777").grid(row=5, column=1, sticky="w", padx=10)

    def _backup_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Backup  ")

        ttk.Label(frame, text="Automatic Backup",
                  font=(FONT_FAMILY, 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(frame, text="Backup Interval (minutes):",
                  font=(FONT_FAMILY, 10)).grid(
            row=1, column=0, sticky="w", pady=5, padx=(0, 10))
        self.backup_interval_var = tk.IntVar(value=get_setting("backup_interval_minutes", 30))
        interval_combo = ttk.Combobox(frame, textvariable=self.backup_interval_var,
                                       values=[15, 30, 60, 120, 180],
                                       state="readonly", width=10)
        interval_combo.grid(row=1, column=1, sticky="w", pady=5)
        interval_combo.bind("<<ComboboxSelected>>", self._on_backup_interval_change)

        ttk.Label(frame, text="How often to auto-backup data files.\n"
                              "Recommended: 30 minutes.",
                  font=(FONT_FAMILY, 9), foreground=TEXT_MUTED).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Separator(frame, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(frame, text="Manual Backup",
                  font=(FONT_FAMILY, 12, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(0, 10))

        def do_manual_backup():
            from database.backup import create_backup
            if create_backup():
                messagebox.showinfo("Backup", "Backup created successfully")
            else:
                messagebox.showerror("Backup", "Backup failed")

        ttk.Button(frame, text="\u21BA  Create Backup Now",
                   command=do_manual_backup).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(frame, text="Creates a timestamped backup of all data files.",
                  font=(FONT_FAMILY, 9), foreground=TEXT_MUTED).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 5))

    def _on_backup_interval_change(self, event=None):
        interval = self.backup_interval_var.get()
        set_setting("backup_interval_minutes", interval)
        stop_auto_backup()
        start_auto_backup(interval)
        self._app.toast.show(f"Backup interval set to {interval} minutes", "success", 3000)

    def _license_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  License  ")
        self._license_frame = frame

        row = 0
        ttk.Label(frame, text="License",
                  font=(FONT_FAMILY, 12, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 10))
        row += 1

        ttk.Label(frame, text="Current Plan:",
                  font=(FONT_FAMILY, 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10))

        if license_manager.is_pro():
            ttk.Label(frame, text=f"  {license_manager.get_tier_name()}  ",
                      font=(FONT_FAMILY, 10, "bold"),
                      foreground=SUCCESS_COLOR).grid(
                row=row, column=1, sticky="w", pady=5)
        else:
            ttk.Label(frame, text=f"  {license_manager.get_tier_name()}  ",
                      font=(FONT_FAMILY, 10, "bold"),
                      foreground=TEXT_MUTED).grid(
                row=row, column=1, sticky="w", pady=5)
        row += 1

        if license_manager.is_pro():
            ttk.Label(frame, text="Licensed To:",
                      font=(FONT_FAMILY, 10, "bold")).grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            ttk.Label(frame, text=license_manager.get_licensed_to(),
                      font=(FONT_FAMILY, 10)).grid(
                row=row, column=1, sticky="w", pady=5)
            row += 1

            ttk.Label(frame, text="Expires:",
                      font=(FONT_FAMILY, 10, "bold")).grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            ttk.Label(frame, text=license_manager._license.get("expires", "N/A"),
                      font=(FONT_FAMILY, 10)).grid(
                row=row, column=1, sticky="w", pady=5)
            row += 1

            ttk.Label(frame, text=f"Stock Limit: {TIERS[license_manager.get_tier()]['max_stock_items']:,}",
                      font=(FONT_FAMILY, 10)).grid(
                row=row, column=0, columnspan=2, sticky="w", pady=2)
            row += 1

            features = []
            if license_manager.has_feature("has_cloud_backup"):
                features.append("Cloud Backup")
            if license_manager.has_feature("has_email_invoicing"):
                features.append("Email Invoicing")
            if license_manager.has_feature("has_advanced_reports"):
                features.append("Advanced Reports")
            if license_manager.has_feature("has_multi_company"):
                features.append("Multi-Company")
            if features:
                ttk.Label(frame, text="Features: " + ", ".join(features),
                          font=(FONT_FAMILY, 9), foreground=TEXT_MUTED).grid(
                    row=row, column=0, columnspan=3, sticky="w", pady=2)
                row += 1

            ttk.Separator(frame, orient="horizontal").grid(
                row=row, column=0, columnspan=3, sticky="ew", pady=10)
            row += 1

            ttk.Button(frame, text="Deactivate License",
                       command=self._deactivate_license).grid(
                row=row, column=0, sticky="w", pady=5)
        else:
            ttk.Label(frame,
                      text="Upgrade to Professional for unlimited items,\n"
                           "cloud backup, email invoicing & more!",
                      font=(FONT_FAMILY, 10),
                      foreground=TEXT_MUTED).grid(
                row=row, column=0, columnspan=3, sticky="w", pady=5)
            row += 1
            ttk.Button(frame, text="Upgrade to Pro",
                       command=self._show_license_dialog).grid(
                row=row, column=0, sticky="w", pady=15)

    def _show_license_dialog(self):
        body = self._app.show_modal("Activate Pro License", 450, 250)

        tk.Label(body, text="Enter your license key to activate Professional:",
                 font=(FONT_FAMILY, 10), bg=CARD_BG,
                 fg=TEXT_PRIMARY).pack(anchor="w", pady=(0, 10))

        tk.Label(body, text="License Key:",
                 font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG,
                 fg=TEXT_PRIMARY).pack(anchor="w")
        key_entry = ttk.Entry(body, width=40, font=(FONT_FAMILY, 10))
        key_entry.pack(fill=tk.X, pady=(2, 10))
        key_entry.insert(0, "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")

        tk.Label(body, text="Licensed To (Name):",
                 font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG,
                 fg=TEXT_PRIMARY).pack(anchor="w")
        name_entry = ttk.Entry(body, width=40, font=(FONT_FAMILY, 10))
        name_entry.pack(fill=tk.X, pady=(2, 10))

        def do_activate():
            key = key_entry.get().strip()
            name = name_entry.get().strip()
            if not key or not name:
                messagebox.showwarning("Missing Info",
                                       "Please fill in both fields.")
                return
            success, msg = license_manager.activate(key, name)
            if success:
                self._app.close_modal()
                messagebox.showinfo("Success", msg)
                self._rebuild_license()
            else:
                messagebox.showerror("Activation Failed", msg)

        btn_frame = tk.Frame(body, bg=CARD_BG)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="Activate",
                   command=do_activate).pack(side=tk.LEFT, padx=(0, 5))

    def _deactivate_license(self):
        if messagebox.askyesno("Deactivate License",
                               "Are you sure? You will lose Pro features."):
            license_manager.deactivate()
            messagebox.showinfo("Deactivated",
                                "License deactivated successfully.")
            self._rebuild_license()

    def _rebuild_license(self):
        for i in range(self._notebook.index("end")):
            if self._notebook.tab(i, "text") == "  License  ":
                self._notebook.forget(i)
                break
        self._license_tab(self._notebook)

    def _updates_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Updates  ")

        row = 0
        ttk.Label(frame, text="Update Settings",
                  font=(FONT_FAMILY, 12, "bold")).grid(
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
                      font=(FONT_FAMILY, 10, "bold")).grid(
                row=row, column=0, sticky="w", pady=3, padx=(0, 15))
            ttk.Label(frame, text=value,
                      font=(FONT_FAMILY, 10)).grid(
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
                      font=(FONT_FAMILY, 11, "bold")).grid(
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
                      font=(FONT_FAMILY, 10)).grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            entry = ttk.Entry(frame, width=width)
            entry.insert(0, company.get(key, ""))
            entry.grid(row=i, column=1, sticky="w", pady=4)
            self._company_fields[key] = entry

        ttk.Label(frame, text="Invoice Footer Note",
                  font=(FONT_FAMILY, 10)).grid(
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
        theme = self.theme_var.get()
        set_setting("theme", theme)
        app = self._app
        app.reload_current_page()
        app._apply_theme()
        try:
            app.toast.show(f"Theme changed to {theme}", "success", 3000)
        except tk.TclError:
            pass

    # ========== NEW TABS (Business, Vertical, Features, Tax) ==========

    def _business_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Business  ")
        tk.Label(frame, text="Invoice Settings", font=(FONT_FAMILY, 12, "bold"),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
        tk.Label(frame, text="Invoice No. Prefix", font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(8, 2))
        self._inv_pref_var = tk.StringVar(value=get_setting("business.invoice_no_prefix", "INV"))
        tk.Entry(frame, textvariable=self._inv_pref_var, width=15, font=(FONT_FAMILY, 10)).pack(anchor="w")
        tk.Label(frame, text="Default Low-Stock Threshold", font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(12, 2))
        self._low_stock_var = tk.StringVar(value=str(get_setting("business.low_stock_threshold_default", 5)))
        tk.Entry(frame, textvariable=self._low_stock_var, width=10, font=(FONT_FAMILY, 10)).pack(anchor="w")
        self._show_tax_recpt_var = tk.BooleanVar(value=get_setting("business.show_tax_breakdown_on_receipt", True))
        tk.Checkbutton(frame, text="Show tax breakdown on receipt", variable=self._show_tax_recpt_var, bg=CARD_BG, font=(FONT_FAMILY, 10), activebackground=CARD_BG).pack(anchor="w", pady=(14, 0))
        tk.Button(frame, text="Save Business Settings", command=self._save_business, font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(16, 0))

    def _save_business(self):
        set_setting("business.invoice_no_prefix", self._inv_pref_var.get().strip())
        try:
            set_setting("business.low_stock_threshold_default", int(self._low_stock_var.get()))
        except ValueError:
            pass
        set_setting("business.show_tax_breakdown_on_receipt", bool(self._show_tax_recpt_var.get()))
        messagebox.showinfo("Saved", "Business settings saved")

    def _vertical_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Vertical  ")
        tk.Label(frame, text="Business Type", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w", pady=(0, 8))
        tk.Label(frame, text="Choose your industry. This enables appropriate features and fields.", font=(FONT_FAMILY, 9), fg=TEXT_MUTED, bg=CARD_BG).pack(anchor="w", pady=(0, 8))
        from utils.verticals import list_verticals
        current = get_setting("vertical", "general")
        self._v_sel_var = tk.StringVar(value=current)
        for key, name, icon, desc in list_verticals():
            tk.Radiobutton(frame, text=icon + "  " + name, variable=self._v_sel_var, value=key, bg=CARD_BG, font=(FONT_FAMILY, 10), selectcolor=CARD_BG, activebackground=CARD_BG).pack(anchor="w", pady=2)
        tk.Button(frame, text="Apply Vertical", command=self._apply_vertical, font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(12, 0))
        tk.Label(frame, text="You can also re-run the setup wizard", font=(FONT_FAMILY, 9), fg=TEXT_MUTED, bg=CARD_BG).pack(anchor="w", pady=(4, 0))
        tk.Button(frame, text="Re-Run Setup Wizard", command=self._run_wizard, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(2, 0))

    def _apply_vertical(self):
        vertical = self._v_sel_var.get()
        from utils.settings_helper import update_features_from_vertical
        update_features_from_vertical(vertical)
        self._app._apply_sidebar_visibility()
        self._app.reload_current_page()
        messagebox.showinfo("Vertical Updated", "Features have been updated. Fine-tune in Features tab.")

    def _run_wizard(self):
        from ui.wizard import FirstRunWizard
        FirstRunWizard().run(self._app)
        self._app._apply_sidebar_visibility()
        self._app.reload_current_page()

    def _features_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Features  ")
        tk.Label(frame, text="Feature Flags", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w", pady=(0, 4))
        tk.Label(frame, text="Enable/disable individual features. Some features depend on the vertical.", font=(FONT_FAMILY, 9), fg=TEXT_MUTED, bg=CARD_BG).pack(anchor="w", pady=(0, 8))
        from utils.verticals import ALL_FEATURES
        self._feat_vars = {}
        for fid, name, desc in ALL_FEATURES:
            row = tk.Frame(frame, bg=CARD_BG)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=get_setting("feature_flags." + fid, False))
            self._feat_vars[fid] = var
            tk.Checkbutton(row, text=name, variable=var, bg=CARD_BG, font=(FONT_FAMILY, 10, "bold"), activebackground=CARD_BG, selectcolor=CARD_BG).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=(FONT_FAMILY, 9), fg=TEXT_MUTED, bg=CARD_BG).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(frame, text="Save Feature Settings", command=self._save_features, font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(12, 0))

    def _save_features(self):
        for fid, var in self._feat_vars.items():
            set_setting("feature_flags." + fid, bool(var.get()))
        self._app._apply_sidebar_visibility()
        self._app.reload_current_page()
        messagebox.showinfo("Saved", "Feature flags saved")

    def _tax_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text="  Tax  ")
        row_frame = tk.Frame(frame, bg=CARD_BG)
        row_frame.pack(fill="x", pady=(0, 8))
        tk.Label(row_frame, text="Country / Tax System", font=(FONT_FAMILY, 12, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
        country = get_setting("country", "India")
        self._c_var = tk.StringVar(value=country)
        for name in ["India", "Nepal", "None"]:
            tk.Radiobutton(row_frame, text=name, variable=self._c_var, value=name, bg=CARD_BG, font=(FONT_FAMILY, 10), selectcolor=CARD_BG, activebackground=CARD_BG, command=self._on_country_change).pack(anchor="w", pady=2)
        self._tax_enabled_var = tk.BooleanVar(value=get_setting("feature_flags.tax_system", True))
        tk.Checkbutton(frame, text="Enable Tax (show on invoices)", variable=self._tax_enabled_var, bg=CARD_BG, font=(FONT_FAMILY, 10), activebackground=CARD_BG, selectcolor=CARD_BG).pack(anchor="w", pady=(4, 8))
        self._tax_rate_frame = tk.Frame(frame, bg=CARD_BG)
        self._tax_rate_frame.pack(fill="x")
        tk.Label(self._tax_rate_frame, text="Default Tax Rate (%)", font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
        self._rate_var = tk.StringVar(value=str(get_setting("tax.default_rate_percent", 18)))
        tk.Entry(self._tax_rate_frame, textvariable=self._rate_var, width=8, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(2, 0))
        tk.Button(frame, text="Save Tax Settings", command=self._save_tax, font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(12, 0))

    def _on_country_change(self):
        val = self._c_var.get()
        if val == "India":
            self._tax_enabled_var.set(True)
            self._rate_var.set("18")
        elif val == "Nepal":
            self._tax_enabled_var.set(True)
            self._rate_var.set("13")
        elif val == "None":
            self._tax_enabled_var.set(False)
            self._rate_var.set("0")
        if val == "India":
            set_setting("currency_symbol", "\u20B9")
        elif val == "Nepal":
            set_setting("currency_symbol", "Rs.")
        else:
            set_setting("currency_symbol", "$")

    def _save_tax(self):
        set_setting("country", self._c_var.get())
        set_setting("feature_flags.tax_system", bool(self._tax_enabled_var.get()))
        try:
            set_setting("tax.default_rate_percent", float(self._rate_var.get()))
        except ValueError:
            pass
        set_setting("first_run", False)
        self._app.reload_current_page()
        messagebox.showinfo("Saved", "Tax settings saved")
