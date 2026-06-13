import tkinter as tk


class Toast:
    def __init__(self, parent):
        self._parent = parent
        self._toasts = []

    def show(self, message, toast_type="info", duration=3000):
        colors = {
            "success": "#27ae60",
            "error": "#e74c3c",
            "warning": "#f39c12",
            "info": "#3498db",
        }
        bg = colors.get(toast_type, "#3498db")
        fg = "white"

        top = tk.Toplevel(self._parent)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg=bg)

        frame = tk.Frame(top, bg=bg, padx=20, pady=10)
        frame.pack()

        tk.Label(frame, text=message, bg=bg, fg=fg,
                 font=("Segoe UI", 10)).pack()

        top.update_idletasks()
        w = top.winfo_reqwidth()
        h = top.winfo_reqheight()
        sw = self._parent.winfo_screenwidth()
        sh = self._parent.winfo_screenheight()
        x = sw - w - 20
        y = sh - h - 50 - (len(self._toasts) * (h + 10))
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
