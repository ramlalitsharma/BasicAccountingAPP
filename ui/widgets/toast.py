import tkinter as tk


class Toast:
    def __init__(self, parent):
        self._parent = parent
        self._toasts = []

    def show(self, message, toast_type="info", duration=3000):
        colors = {
            "success": "#059669",
            "error": "#DC2626",
            "warning": "#D97706",
            "info": "#2563EB",
        }
        bg = colors.get(toast_type, "#2563EB")
        fg = "white"

        top = tk.Toplevel(self._parent)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=bg)

        frame = tk.Frame(top, bg=bg, padx=20, pady=10)
        frame.pack()

        icon_map = {"success": "\u2713", "error": "\u2717", "warning": "\u26A0", "info": "\u2139"}
        icon = icon_map.get(toast_type, "")
        tk.Label(frame, text=f"{icon}  {message}", bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack()

        top.update_idletasks()
        w = top.winfo_reqwidth()
        h = top.winfo_reqheight()
        sw = self._parent.winfo_screenwidth()
        sh = self._parent.winfo_screenheight()
        x = sw - w - 24
        y = sh - h - 60 - (len(self._toasts) * (h + 10))
        top.geometry(f"+{x}+{y}")

        self._toasts.append(top)

        def fade():
            try:
                top.destroy()
            except tk.TclError:
                pass
            if top in self._toasts:
                self._toasts.remove(top)

        top.after(duration, fade)
