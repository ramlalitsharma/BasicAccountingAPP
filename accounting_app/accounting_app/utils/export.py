import csv
import os
from tkinter import filedialog, messagebox


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
            writer.writerows(data)
        messagebox.showinfo("Export", f"Exported to:\n{path}")
    except Exception as e:
        messagebox.showerror("Export Error", str(e))
