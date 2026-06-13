import sys
import os
import logging


def show_splash():
    try:
        import tkinter as tk
        from config import ICON_PATH, ICON_PNG_PATH
        splash = tk.Tk()
        splash.title("")
        splash.overrideredirect(True)
        splash.geometry("520x340+{}+{}".format(
            (splash.winfo_screenwidth() - 520) // 2,
            (splash.winfo_screenheight() - 340) // 2,
        ))
        splash.configure(bg="#1a1a2e")
        try:
            if os.path.exists(ICON_PATH):
                splash.iconbitmap(default=ICON_PATH)
        except Exception:
            pass

        try:
            if os.path.exists(ICON_PNG_PATH):
                logo_img = tk.PhotoImage(file=ICON_PNG_PATH).subsample(2, 2)
                logo_lbl = tk.Label(splash, image=logo_img, bg="#1a1a2e")
                logo_lbl.image = logo_img
                logo_lbl.place(relx=0.5, rely=0.30, anchor="center")
        except Exception:
            pass

        tk.Label(splash, text="Accounting Pro",
                 font=("Segoe UI", 24, "bold"),
                 bg="#1a1a2e", fg="white").place(relx=0.5, rely=0.58, anchor="center")
        tk.Label(splash, text="Professional Accounting Suite",
                 font=("Segoe UI", 11),
                 bg="#1a1a2e", fg="#c8d6e5").place(relx=0.5, rely=0.68, anchor="center")
        tk.Label(splash, text="v2.5.0  |  Loading...",
                 font=("Segoe UI", 8),
                 bg="#1a1a2e", fg="#0f3460").place(relx=0.5, rely=0.82, anchor="center")

        splash.update()
        return splash
    except Exception as e:
        logging.getLogger().warning(f"Splash screen failed: {e}")
        return None


def main():
    from utils.logging_setup import setup_logging
    logger = setup_logging()
    logger.info("Starting Accounting Pro v2.5.0")

    from utils.single_instance import is_already_running, release_lock
    if is_already_running():
        logger.warning("Another instance is already running")
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Already Running",
            "Accounting Pro is already running.\nOnly one instance is allowed."
        )
        root.destroy()
        sys.exit(0)

    splash = show_splash()
    try:
        from ui.app import AccountingApp
        if splash:
            splash.destroy()
        app = AccountingApp()
        app.protocol("WM_DELETE_WINDOW", lambda: (
            release_lock(),
            app.destroy()
        ))
        app.mainloop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        if splash:
            splash.destroy()
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Fatal Error",
            f"An unexpected error occurred:\n{e}\n\nPlease check the logs."
        )
        root.destroy()
        raise


if __name__ == "__main__":
    main()
