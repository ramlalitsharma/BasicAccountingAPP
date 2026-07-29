"""First-run setup wizard: selects vertical + country + tax config."""
import tkinter as tk
from tkinter import messagebox
from config import (
    CARD_BG, TEXT_PRIMARY, TEXT_MUTED,
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG,
    get_color, set_setting,
)
from utils.verticals import (
    list_verticals, get_default_feature_flags,
    DEFAULT_COUNTRY_FOR_VERTICAL,
)


class FirstRunWizard:
    def run(self, app):
        """Open wizard and return chosen settings dict."""
        top = tk.Toplevel(app)
        top.title("Welcome to Accounting Pro - Setup")
        top.configure(bg=CARD_BG)
        top.transient(app)
        top.grab_set()
        w, h = 760, 560
        x = app.winfo_rootx() + (app.winfo_width() - w) // 2
        y = app.winfo_rooty() + (app.winfo_height() - h) // 2
        top.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        top.minsize(w, h)

        self.app = app
        self.top = top
        self.choices = {
            "vertical": "general",
            "country": "India",
            "tax_enabled": True,
            "default_tax_rate": 18,
            "currency": "\u20B9",
        }
        self._done = False

        self._nav_frame = tk.Frame(top, bg=CARD_BG, height=46)
        self._nav_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self._step_idx = 0
        self._steps = [self._s_welcome, self._s_vertical, self._s_tax, self._s_confirm]
        self._body = None
        self._build_step()
        top.protocol("WM_DELETE_WINDOW", lambda: self._cancel(top))
        top.wait_window()
        return self.choices if self._done else None

    def _cancel(self, top):
        if messagebox.askyesno("Cancel setup", "Skip setup for now?\n\nYou can configure this anytime from Settings.", parent=top):
            self._done = False
            top.destroy()

    def _build_step(self):
        if self._body is not None and self._body.winfo_exists():
            self._body.destroy()
        for w in self._nav_frame.winfo_children():
            w.destroy()
        self._body = tk.Frame(self.top, bg=CARD_BG)
        self._body.pack(fill=tk.BOTH, expand=True)
        try:
            self._steps[self._step_idx](self._body)
        except Exception as exc:
            print(f"Wizard step error: {exc}")
        self._render_nav()

    def _render_nav(self):
        is_last = self._step_idx == len(self._steps) - 1
        if self._step_idx > 0:
            tk.Button(self._nav_frame, text="Back",
                      font=(FONT_FAMILY, 10), command=self._back,
                      cursor="hand2", padx=18, pady=4, bd=1).pack(
                          side=tk.LEFT, padx=18, pady=10)
        label = "Finish" if is_last else "Next"
        tk.Button(self._nav_frame, text=label,
                  font=(FONT_FAMILY, 10, "bold"),
                  bg=get_color("ACCENT_COLOR"), fg="white",
                  activebackground=get_color("ACCENT_LIGHT"),
                  activeforeground="white", bd=0,
                  command=(self._finish if is_last else self._next),
                  cursor="hand2", padx=22, pady=6).pack(
                      side=tk.RIGHT, padx=18, pady=10)
        tk.Label(self._nav_frame,
                 text=f"Step {self._step_idx + 1} of {len(self._steps)}",
                 font=(FONT_FAMILY, 9), bg=CARD_BG, fg=TEXT_MUTED).pack(
                     side=tk.LEFT, padx=18)

    def _next(self):
        if self._step_idx == 1 and not self.choices.get("vertical"):
            messagebox.showwarning("Pick one", "Please choose your business type.",
                                   parent=self.top)
            return
        if self._step_idx == 2 and not self.choices.get("country"):
            messagebox.showwarning("Pick one", "Please choose a country.",
                                   parent=self.top)
            return
        self._step_idx += 1
        if self._step_idx >= len(self._steps):
            self._finish()
            return
        self._build_step()

    def _back(self):
        if self._step_idx > 0:
            self._step_idx -= 1
            self._build_step()

    def _finish(self):
        try:
            self.choices["default_tax_rate"] = float(self.choices.get("default_tax_rate", 0))
        except Exception:
            self.choices["default_tax_rate"] = 0
        set_setting("vertical", self.choices.get("vertical", "general"))
        set_setting("country", self.choices.get("country", "India"))
        set_setting("currency_symbol", self.choices.get("currency"))
        tax_enabled = bool(self.choices.get("tax_enabled"))
        set_setting("feature_flags.tax_system", tax_enabled)
        if tax_enabled:
            country = self.choices.get("country")
            rate = self.choices["default_tax_rate"]
            if country == "India":
                set_setting("tax.india.default_rate", rate)
            elif country == "Nepal":
                set_setting("tax.nepal.default_rate", rate)
            set_setting("tax.default_rate_percent", rate)
        defaults = get_default_feature_flags(self.choices.get("vertical", "general"))
        for k, val in defaults.items():
            set_setting(f"feature_flags.{k}", val)
        set_setting("feature_flags.tax_system", tax_enabled)
        set_setting("first_run", False)
        self._done = True
        try:
            self.top.destroy()
        except tk.TclError:
            pass

    def _s_welcome(self, body):
        bg = CARD_BG
        tk.Label(body, text="Welcome to Accounting Pro",
                 font=(FONT_FAMILY, 22, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(
                     anchor="w", padx=28, pady=(28, 6))
        tk.Label(body, text="Let's get your workspace set up. Just a few quick questions.",
                 font=(FONT_FAMILY, 11), bg=bg, fg=TEXT_MUTED,
                 justify="left").pack(anchor="w", padx=28, pady=(0, 24))
        for line in [
            "Pick your business type — we'll enable only the features you need.",
            "Pick your country so tax calculations are correct on every bill.",
            "Everything can be changed later from Settings — nothing is locked in.",
        ]:
            tk.Label(body, text=line, font=(FONT_FAMILY, 11), bg=bg,
                     fg=TEXT_PRIMARY, justify="left").pack(anchor="w", padx=28, pady=4)
        tk.Label(body, text="Tip: this dialog can be re-opened any time from Settings.",
                 font=(FONT_FAMILY, 10), bg=bg, fg=TEXT_MUTED).pack(
                     anchor="w", padx=28, pady=(22, 0))

    def _s_vertical(self, body):
        bg = CARD_BG
        tk.Label(body, text="Business Type",
                 font=(FONT_FAMILY, 16, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(
                     anchor="w", padx=28, pady=(24, 4))
        tk.Label(body, text="Choose the closest match. You can fine-tune features later.",
                 font=(FONT_FAMILY, 10), bg=bg, fg=TEXT_MUTED).pack(
                     anchor="w", padx=28, pady=(0, 12))
        self._v_var = tk.StringVar(value=self.choices["vertical"])
        self._v_rows = []
        for key, name, icon, desc in list_verticals():
            row = tk.Frame(body, bg=bg, bd=2, relief=tk.GROOVE, cursor="hand2")
            row.pack(fill=tk.X, padx=28, pady=4)
            self._v_rows.append((key, row))
            row.bind("<Button-1>", lambda e, k=key: self._select_v(k))
            inner = tk.Frame(row, bg=bg)
            inner.pack(fill=tk.X, padx=12, pady=8)

            def make_click(k):
                return lambda e: self._select_v(k)

            tk.Label(inner, text=icon, font=("Segoe UI Emoji", 18),
                     bg=bg, fg=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 12))
            text_block = tk.Frame(inner, bg=bg)
            text_block.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(text_block, text=name, font=(FONT_FAMILY, 11, "bold"),
                     bg=bg, fg=TEXT_PRIMARY).pack(anchor="w")
            tk.Label(text_block, text=desc, font=(FONT_FAMILY, 9), bg=bg,
                     fg=TEXT_MUTED, wraplength=520, justify="left").pack(anchor="w")
            for child in inner.winfo_children():
                child.bind("<Button-1>", make_click(key))
                for c in child.winfo_children():
                    c.bind("<Button-1>", make_click(key))
        self._select_v(self.choices["vertical"])

    def _select_v(self, key):
        self.choices["vertical"] = key
        sel_color = get_color("ACCENT_LIGHT")
        plain = CARD_BG
        for k, row in self._v_rows:
            target = sel_color if k == key else plain
            try:
                row.configure(bg=target,
                              bd=2,
                              relief=tk.SOLID if k == key else tk.GROOVE)
            except Exception:
                pass
            self._recursive_bg(row, target)

    def _recursive_bg(self, widget, color):
        try:
            widget.configure(bg=color)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._recursive_bg(child, color)

    def _s_tax(self, body):
        bg = CARD_BG
        tk.Label(body, text="Country & Tax",
                 font=(FONT_FAMILY, 16, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(
                     anchor="w", padx=28, pady=(24, 4))
        tk.Label(body, text="Where does your business operate? We'll apply the correct tax rules.",
                 font=(FONT_FAMILY, 10), bg=bg, fg=TEXT_MUTED).pack(
                     anchor="w", padx=28, pady=(0, 12))

        country_frame = tk.Frame(body, bg=bg)
        country_frame.pack(fill=tk.X, padx=28, pady=(0, 16))
        tk.Label(country_frame, text="Country",
                 font=(FONT_FAMILY, 11, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(anchor="w")
        self._country_var = tk.StringVar(value=self.choices["country"])
        for label, value, cur in [("India", "India", "\u20B9"),
                                  ("Nepal", "Nepal", "Rs."),
                                  ("None / International", "None", "$")]:
            r = tk.Frame(country_frame, bg=bg)
            r.pack(anchor="w", pady=2)
            rb = tk.Radiobutton(r, text=label, variable=self._country_var,
                                value=value, bg=bg, fg=TEXT_PRIMARY,
                                font=(FONT_FAMILY, 11), selectcolor=bg,
                                command=self._on_country_change, cursor="hand2")
            rb.pack(side=tk.LEFT)
        tax_frame = tk.Frame(body, bg=bg)
        tax_frame.pack(fill=tk.X, padx=28, pady=(8, 16))
        self._tax_var = tk.BooleanVar(value=bool(self.choices["tax_enabled"]))
        tax_cb = tk.Checkbutton(tax_frame, text="Enable Tax System (recommended)",
                                variable=self._tax_var, bg=bg, fg=TEXT_PRIMARY,
                                font=(FONT_FAMILY, 11), selectcolor=bg,
                                activebackground=bg, command=self._on_tax_change,
                                cursor="hand2")
        tax_cb.pack(anchor="w")

        rate_frame = tk.Frame(body, bg=bg)
        rate_frame.pack(fill=tk.X, padx=28, pady=(0, 8))
        tk.Label(rate_frame, text="Default Tax Rate (%)",
                 font=(FONT_FAMILY, 11, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(anchor="w")
        self._rate_var = tk.StringVar(value=str(self.choices["default_tax_rate"]))
        rate_entry = tk.Entry(rate_frame, textvariable=self._rate_var,
                              font=(FONT_FAMILY, 11), width=8,
                              bg="white", fg=TEXT_PRIMARY, bd=1)
        rate_entry.pack(anchor="w", pady=4)
        self._rate_var.trace_add("write", lambda *a: self._sync_rate())
        tk.Label(rate_frame,
                 text="Will auto-apply to sales. Adjustable per invoice.",
                 font=(FONT_FAMILY, 9), bg=bg, fg=TEXT_MUTED).pack(anchor="w")

        cur_frame = tk.Frame(body, bg=bg)
        cur_frame.pack(fill=tk.X, padx=28, pady=(8, 0))
        tk.Label(cur_frame, text="Currency Symbol",
                 font=(FONT_FAMILY, 11, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(anchor="w")
        self._cur_var = tk.StringVar(value=self.choices["currency"])
        for sym in ["\u20B9", "Rs.", "$", "€", "£", "¥"]:
            tk.Radiobutton(cur_frame, text=sym, variable=self._cur_var, value=sym,
                           bg=bg, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 14),
                           selectcolor=bg, activebackground=bg, cursor="hand2",
                           command=lambda s=sym: self.choices.update({"currency": s})
                           ).pack(side=tk.LEFT, padx=4)

    def _on_country_change(self):
        value = self._country_var.get()
        self.choices["country"] = value
        if value == "India":
            self.choices["default_tax_rate"] = 18
            self.choices["currency"] = "\u20B9"
        elif value == "Nepal":
            self.choices["default_tax_rate"] = 13
            self.choices["currency"] = "Rs."
        else:
            self.choices["default_tax_rate"] = 0
            self.choices["currency"] = "$"
        try:
            self._rate_var.set(str(self.choices["default_tax_rate"]))
            self._cur_var.set(self.choices["currency"])
        except Exception:
            pass

    def _on_tax_change(self):
        enabled = bool(self._tax_var.get())
        self.choices["tax_enabled"] = enabled
        if not enabled:
            self.choices["default_tax_rate"] = 0
            try:
                self._rate_var.set("0")
            except Exception:
                pass

    def _sync_rate(self):
        try:
            self.choices["default_tax_rate"] = float(self._rate_var.get())
        except ValueError:
            pass

    def _s_confirm(self, body):
        bg = CARD_BG
        tk.Label(body, text="Confirm & Start",
                 font=(FONT_FAMILY, 16, "bold"), bg=bg, fg=TEXT_PRIMARY).pack(
                     anchor="w", padx=28, pady=(24, 4))
        tk.Label(body, text="Review your selections, then click Finish to start.",
                 font=(FONT_FAMILY, 10), bg=bg, fg=TEXT_MUTED).pack(
                     anchor="w", padx=28, pady=(0, 18))
        from utils.verticals import VERTICALS
        v = VERTICALS.get(self.choices.get("vertical", "general"), {})
        items = [
            ("Business Type", f"{v.get('icon', '')} {v.get('name', self.choices.get('vertical'))}"),
            ("Country", self.choices.get("country")),
            ("Currency", self.choices.get("currency")),
            ("Tax System", "Enabled" if self.choices.get("tax_enabled") else "Disabled"),
            ("Default Tax Rate", f"{self.choices.get('default_tax_rate', 0)}%"),
        ]
        for label, val in items:
            line = tk.Frame(body, bg=bg)
            line.pack(fill=tk.X, padx=28, pady=4)
            tk.Label(line, text=label + ":",
                     font=(FONT_FAMILY, 11), bg=bg, fg=TEXT_MUTED,
                     width=18, anchor="w").pack(side=tk.LEFT)
            tk.Label(line, text=val, font=(FONT_FAMILY, 11, "bold"),
                     bg=bg, fg=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(8, 0))
        primary = v.get("primary_features", [])
        if primary:
            from utils.verticals import ALL_FEATURES
            feature_names = {fid: name for fid, name, _ in ALL_FEATURES}
            lines = [f"  - {feature_names.get(f, f)}" for f in primary]
            tk.Label(body, text="\nPrimary features for your business:",
                     font=(FONT_FAMILY, 10), bg=bg, fg=TEXT_MUTED).pack(
                         anchor="w", padx=28, pady=(16, 0))
            for line_text in lines:
                tk.Label(body, text=line_text,
                         font=(FONT_FAMILY, 10), bg=bg, fg=TEXT_PRIMARY).pack(
                             anchor="w", padx=36, pady=2)
        tk.Label(body, text="You can change all of this from Settings.",
                 font=(FONT_FAMILY, 9), bg=bg, fg=TEXT_MUTED).pack(
                     anchor="w", padx=28, pady=(20, 0))