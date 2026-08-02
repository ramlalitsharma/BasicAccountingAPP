"""Login dialog and user management modal."""
import tkinter as tk
from tkinter import ttk, messagebox
from config import CARD_BG, TEXT_PRIMARY, TEXT_MUTED, SUCCESS_COLOR, DANGER_COLOR, \
    FONT_FAMILY, FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG, get_color
from utils.auth import auth_manager
from database.audit import log_login


class LoginDialog:
    def __init__(self, app):
        self.app = app
        self.result = False

    def show(self):
        top = tk.Toplevel(self.app)
        top.title("Login - Accounting Pro")
        top.configure(bg=CARD_BG)
        top.transient(self.app)
        top.grab_set()
        top.protocol("WM_DELETE_WINDOW", lambda: self._close(top, False))
        w, h = 380, 340
        x = self.app.winfo_rootx() + (self.app.winfo_width() - w) // 2
        y = self.app.winfo_rooty() + (self.app.winfo_height() - h) // 2
        top.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        top.resizable(False, False)

        main_frame = tk.Frame(top, bg=CARD_BG, padx=30, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Accounting Pro",
                 font=(FONT_FAMILY, 18, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(pady=(10, 4))
        tk.Label(main_frame, text="Sign in to continue",
                 font=(FONT_FAMILY, 10), bg=CARD_BG, fg=TEXT_MUTED).pack(pady=(0, 20))

        tk.Label(main_frame, text="Username",
                 font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
        username_entry = ttk.Entry(main_frame, width=30, font=(FONT_FAMILY, 11))
        username_entry.pack(fill=tk.X, pady=(2, 10))
        username_entry.focus_set()

        tk.Label(main_frame, text="Password",
                 font=(FONT_FAMILY, 10, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
        password_entry = ttk.Entry(main_frame, width=30, font=(FONT_FAMILY, 11), show="*")
        password_entry.pack(fill=tk.X, pady=(2, 10))

        error_lbl = tk.Label(main_frame, text="", font=(FONT_FAMILY, 9),
                             bg=CARD_BG, fg=DANGER_COLOR)
        error_lbl.pack()

        def do_login():
            user = username_entry.get().strip()
            password = password_entry.get().strip()
            if not user or not password:
                error_lbl.config(text="Please enter username and password")
                return
            success, msg = auth_manager.login(user, password)
            if success:
                log_login(user, True)
                self.result = True
                top.destroy()
            else:
                log_login(user, False)
                error_lbl.config(text=msg)

        def try_skip():
            if messagebox.askyesno("Skip login?", "Operating in view-only mode.\n\nContinue without login?", parent=top):
                self.result = True
                top.destroy()

        btn_frame = tk.Frame(main_frame, bg=CARD_BG)
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="Login", command=do_login,
                  font=(FONT_FAMILY, 10, "bold"), bg=get_color("ACCENT_COLOR"), fg="white",
                  activebackground=get_color("ACCENT_LIGHT"), activeforeground="white",
                  bd=0, cursor="hand2", padx=20, pady=6).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Skip", command=try_skip).pack(side=tk.LEFT)

        top.bind("<Return>", lambda e: do_login())
        top.wait_window()
        return self.result


class UserManagementDialog:
    def __init__(self, app):
        self.app = app

    def show(self):
        if not auth_manager.has_permission("can_manage_users"):
            messagebox.showwarning("Access Denied", "You don't have permission to manage users.")
            return

        body = self.app.show_modal("User Management", 600, 450)
        main = tk.Frame(body, bg=CARD_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        tk.Label(main, text="Users", font=(FONT_FAMILY, 12, "bold"),
                 bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")

        # User list
        list_frame = tk.Frame(main, bg=CARD_BG)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        tree = ttk.Treeview(list_frame, columns=["user", "role", "name"], show="headings", height=6)
        tree.heading("user", text="Username")
        tree.heading("role", text="Role")
        tree.heading("name", text="Display Name")
        tree.column("user", width=120)
        tree.column("role", width=100)
        tree.column("name", width=180)
        for u in auth_manager.list_users():
            tree.insert("", tk.END, values=[u["username"], u["role"].capitalize(), u["display_name"]])
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scroll.set)

        # Buttons
        btn_frame = tk.Frame(main, bg=CARD_BG)
        btn_frame.pack(fill=tk.X, pady=8)

        def add_user():
            add_body = self.app.show_modal("Add User", 400, 280)
            fields = {}
            for label, key in [("Username", "username"), ("Password", "password"),
                               ("Display Name", "display")]:
                tk.Label(add_body, text=label, font=(FONT_FAMILY, 10, "bold"),
                         bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w", pady=(8, 2))
                entry = ttk.Entry(add_body, width=30)
                entry.pack(fill=tk.X)
                if key == "password":
                    entry.configure(show="*")
                fields[key] = entry
            tk.Label(add_body, text="Role", font=(FONT_FAMILY, 10, "bold"),
                     bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w", pady=(8, 2))
            role_var = tk.StringVar(value="cashier")
            for r, info in [("admin", "Administrator - full access"),
                            ("manager", "Manager - delete & export"),
                            ("cashier", "Cashier - sales only")]:
                tk.Radiobutton(add_body, text=f"{r.capitalize()}: {info}",
                               variable=role_var, value=r, bg=CARD_BG,
                               font=(FONT_FAMILY, 9), selectcolor=CARD_BG).pack(anchor="w")

            def do_add():
                u = fields["username"].get().strip()
                p = fields["password"].get().strip()
                d = fields["display"].get().strip()
                if not u or not p:
                    messagebox.showwarning("Missing", "Username and password required", parent=add_body)
                    return
                success, msg = auth_manager.add_user(u, p, role_var.get(), d or u)
                if success:
                    self.app.close_modal()
                    self.show()
                    messagebox.showinfo("Success", msg)
                else:
                    messagebox.showerror("Error", msg, parent=add_body)

            ttk.Button(add_body, text="Create User", command=do_add).pack(pady=12)

        ttk.Button(btn_frame, text="Add User", command=add_user).pack(side=tk.LEFT, padx=2)

        def delete_user():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a user first")
                return
            values = tree.item(sel[0])["values"]
            if not values:
                return
            username = values[0]
            if username == auth_manager.get_current_user():
                messagebox.showwarning("Cannot Delete", "Cannot delete your own account")
                return
            if messagebox.askyesno("Confirm", f"Delete user '{username}'?"):
                success, msg = auth_manager.delete_user(username)
                if success:
                    tree.delete(sel[0])
                    messagebox.showinfo("Deleted", msg)
                else:
                    messagebox.showerror("Error", msg)

        ttk.Button(btn_frame, text="Delete User", command=delete_user).pack(side=tk.LEFT, padx=2)

        def change_pass():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a user first")
                return
            values = tree.item(sel[0])["values"]
            if not values:
                return
            username = values[0]
            body2 = self.app.show_modal("Change Password", 380, 200)
            tk.Label(body2, text="New Password", font=(FONT_FAMILY, 10),
                     bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
            pw_entry = ttk.Entry(body2, width=30, show="*")
            pw_entry.pack(fill=tk.X, pady=4)
            tk.Label(body2, text="Confirm Password", font=(FONT_FAMILY, 10),
                     bg=CARD_BG, fg=TEXT_PRIMARY).pack(anchor="w")
            pw2_entry = ttk.Entry(body2, width=30, show="*")
            pw2_entry.pack(fill=tk.X, pady=4)

            def do_change():
                if pw_entry.get() != pw2_entry.get():
                    messagebox.showerror("Error", "Passwords don't match", parent=body2)
                    return
                if len(pw_entry.get()) < 4:
                    messagebox.showerror("Error", "Password too short (min 4 chars)", parent=body2)
                    return
                # Admin can force change password for any user
                auth_manager._users[username]["password_hash"] = \
                    auth_manager._hash_password(pw_entry.get())
                auth_manager._save()
                self.app.close_modal()
                messagebox.showinfo("Success", f"Password changed for user '{username}'")

            ttk.Button(body2, text="Change Password", command=do_change).pack(pady=12)

        ttk.Button(btn_frame, text="Change Password", command=change_pass).pack(side=tk.LEFT, padx=2)