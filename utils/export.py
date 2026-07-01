import csv
from tkinter import filedialog, messagebox


def _sanitize_csv(val):
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def export_to_csv(data, headers, default_name="export.csv"):
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile=default_name,
    )
    if not path:
        return
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows([_sanitize_csv(c) for c in row] for row in data)
        messagebox.showinfo("Export", f"Exported to:\n{path}")
    except (PermissionError, OSError, csv.Error) as e:
        messagebox.showerror("Export Error", f"Could not export file:\n{e}")
