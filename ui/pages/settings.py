import tkinter as tk
from tkinter import ttk, messagebox
from config import ACCENT_COLOR, FONT_FAMILY, APP_NAME, VERSION, USER_DATA_DIR, update_data_dir
from utils.company import load_company, save_company


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
        theme = self.theme_var.get()
        if theme == "Dark":
            bg, fg, card = "#2d2d2d", "#ffffff", "#3d3d3d"
        else:
            bg, fg, card = "#f0f2f5", "#2c3e50", "#ffffff"

        self._app.configure(bg=bg)

        def apply_theme(widget):
            try:
                if isinstance(widget, (tk.Label, tk.Frame, tk.Button)):
                    cbg = widget.cget("bg")
                    if cbg in ("#f0f2f5", "#2d2d2d", "#ffffff", "#3d3d3d",
                               "#1a1a2e", "#16213e", "#0f3460"):
                        widget.configure(
                            bg=bg if cbg != "#1a1a2e" else "#1a1a2e")
                if isinstance(widget, (tk.Label, tk.Button)):
                    cfg = widget.cget("fg")
                    if cfg in ("#2c3e50", "#ffffff", "#777", "#c8d6e5"):
                        widget.configure(fg=fg if cfg != "#c8d6e5" else fg)
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
