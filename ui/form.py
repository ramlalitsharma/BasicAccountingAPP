import tkinter as tk
from tkinter import ttk, messagebox
from modules import suppliers, sales, stock


# ---------------- SUPPLIER + STOCK FORM ----------------
def add_supplier_form(app):
    if not app.active_file:
        messagebox.showwarning("No File", "Please create or select a stock file first!")
        return

    form = tk.Toplevel(app)
    form.title("Add Supplier & Stock Item")
    form.geometry("500x500")

    # Supplier fields
    supplier_labels = ["Bill id", "Name", "Contact", "Address"]
    supplier_entries = {}
    for i, label in enumerate(supplier_labels):
        ttk.Label(form, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="w")
        entry = ttk.Entry(form)
        entry.grid(row=i, column=1, padx=10, pady=5)
        supplier_entries[label] = entry

    # Category dropdown (existing categories from Suppliers sheet)
    categories = []
    try:
        existing_suppliers = suppliers.get_suppliers(app.active_file)
        categories = list({row[4] for row in existing_suppliers if row and row[4]})
    except Exception:
        categories = []

    ttk.Label(form, text="Item Category").grid(row=len(supplier_labels), column=0, padx=10, pady=5, sticky="w")
    category_var = tk.StringVar()
    category_dropdown = ttk.Combobox(form, textvariable=category_var, values=categories, state="normal")
    category_dropdown.grid(row=len(supplier_labels), column=1, padx=10, pady=5)

    # Stock item fields
    stock_labels = ["Bill id", "Item Name", "Quantity", "Purchase Price", "Selling Price"]
    stock_entries = {}
    for i, label in enumerate(stock_labels):
        ttk.Label(form, text=label).grid(row=len(supplier_labels)+1+i, column=0, padx=10, pady=5, sticky="w")
        entry = ttk.Entry(form)
        entry.grid(row=len(supplier_labels)+1+i, column=1, padx=10, pady=5)
        stock_entries[label] = entry

    def save_supplier_and_stock():
        # Supplier values
        supplier_values = [supplier_entries[label].get() for label in supplier_labels]
        supplier_values.append(category_var.get())
        if not supplier_values[1]:
            messagebox.showerror("Error", "Supplier Name is required!")
            return

        suppliers.create_suppliers_sheet(app.active_file)
        suppliers.add_supplier(app.active_file, supplier_values)

        # Stock values
        try:
            stock_data = [
                int(stock_entries["Bill id"].get()),
                stock_entries["Item Name"].get(),
                category_var.get(),
                int(stock_entries["Quantity"].get()),
                float(stock_entries["Purchase Price"].get()),
                float(stock_entries["Selling Price"].get())
            ]
        except ValueError:
            messagebox.showerror("Error", "Quantity, Purchase Price, and Selling Price must be numbers!")
            return

        stock.add_item(app.active_file, stock_data)
        messagebox.showinfo("Success", f"Supplier '{supplier_values[1]}' and Item '{stock_data[1]}' added!")
        form.destroy()

    ttk.Button(form, text="Save Supplier & Stock", command=save_supplier_and_stock).grid(
        row=len(supplier_labels)+len(stock_labels)+2, column=0, columnspan=2, pady=20
    )


# ---------------- VIEW SUPPLIERS ----------------
def view_suppliers_form(app):
    if not app.active_file:
        messagebox.showwarning("No File", "Please create or select a stock file first!")
        return

    data = suppliers.get_suppliers(app.active_file)
    if not data:
        messagebox.showinfo("Suppliers", "No suppliers found!")
        return

    form = tk.Toplevel(app)
    form.title("Suppliers List")
    form.geometry("600x400")

    cols = ["Bill id", "Name", "Contact", "Address", "Item Categories"]
    tree = ttk.Treeview(form, columns=cols, show="headings")

    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=120)

    for row in data:
        tree.insert("", tk.END, values=row)

    tree.pack(expand=True, fill="both")


# ---------------- NEW SALE FORM ----------------
def new_sale_form(app):
    if not app.active_file:
        messagebox.showwarning("No File", "Please create or select a stock file first!")
        return

    form = tk.Toplevel(app)
    form.title("Record Sale")
    form.geometry("400x350")

    labels = ["Bill id", "Item", "Quantity Sold", "Price", "Total Amount"]
    entries = {}
    for i, label in enumerate(labels):
        ttk.Label(form, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="w")
        entry = ttk.Entry(form)
        entry.grid(row=i, column=1, padx=10, pady=5)
        entries[label] = entry

    def save_sale():
        values = [entries[label].get() for label in labels]
        if not values[1] or not values[2]:
            messagebox.showerror("Error", "Item and Quantity are required!")
            return

        try:
            sale_data = [
                int(values[0]),   # Sale ID
                str(values[1]),   # Item
                int(values[2]),   # Quantity
                float(values[3]), # Price
                float(values[4])  # Total Amount
            ]
        except ValueError:
            messagebox.showerror("Error", "Quantity, Price, and Total must be numbers!")
            return

        sales.record_sale(app.active_file, sale_data)
        messagebox.showinfo("Success", f"Sale recorded for Item {values[1]}")
        form.destroy()

    ttk.Button(form, text="Save Sale", command=save_sale).grid(
        row=len(labels), column=0, columnspan=2, pady=20
    )


# ---------------- VIEW SALES ----------------
def view_sales_form(app):
    if not app.active_file:
        messagebox.showwarning("No File", "Please create or select a stock file first!")
        return

    data = sales.get_sales(app.active_file)
    if not data:
        messagebox.showinfo("Sales", "No sales records found!")
        return

    form = tk.Toplevel(app)
    form.title("Sales Records")
    form.geometry("600x400")

    cols = ["Bill id", "Item", "Quantity Sold", "Price", "Total Amount"]
    tree = ttk.Treeview(form, columns=cols, show="headings")

    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=120)

    for row in data:
        tree.insert("", tk.END, values=row)

    tree.pack(expand=True, fill="both")


# ---------------- VIEW STOCK ----------------
def view_stock_form(app):
    if not app.active_file:
        messagebox.showwarning("No File", "Please create or select a stock file first!")
        return

    data = stock.get_stock_items(app.active_file)
    if not data:
        messagebox.showinfo("Stock", "No stock items found!")
        return

    form = tk.Toplevel(app)
    form.title("Stock Inventory")
    form.geometry("700x400")

    cols = ["Bill id", "Item Name", "Category", "Quantity", "Purchase Price", "Selling Price"]
    tree = ttk.Treeview(form, columns=cols, show="headings")

    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=110)

    for row in data:
        tree.insert("", tk.END, values=row)

    tree.pack(expand=True, fill="both")


# ---------------- ADD STOCK ITEM ----------------
def add_stock_item_form(app):
    if not app.active_file:
        messagebox.showwarning("No File", "Please create or select a stock file first!")
        return

    form = tk.Toplevel(app)
    form.title("Add Stock Item")
    form.geometry("450x400")

    labels = ["Bill id", "Item Name", "Category", "Quantity", "Purchase Price", "Selling Price"]
    entries = {}
    for i, label in enumerate(labels):
        ttk.Label(form, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="w")
        entry = ttk.Entry(form)
        entry.grid(row=i, column=1, padx=10, pady=5)
        entries[label] = entry

    def save_item():
        values = [entries[label].get() for label in labels]
        if not values[1]:
            messagebox.showerror("Error", "Item Name is required!")
            return
        try:
            item_data = [
                int(values[0]),   # Item ID
                values[1],        # Item Name
                values[2],        # Category
                int(values[3]),   # Quantity
                float(values[4]), # Purchase Price
                float(values[5])  # Selling Price
            ]
        except ValueError:
            messagebox.showerror("Error", "Quantity, Purchase Price, and Selling Price must be numbers!")
            return

        stock.add_item(app.active_file, item_data)
        messagebox.showss

import os
import subprocess

def print_bill_form(app):
    form = tk.Toplevel(app)
    form.title("Print / Save Bill")
    form.geometry("300x150")

    ttk.Label(form, text="Enter Sale ID").pack(pady=10)
    sale_id_entry = ttk.Entry(form)
    sale_id_entry.pack(pady=5)

    def open_bill():
        sale_id = sale_id_entry.get()
        bill_filename = f"Sale_{sale_id}.xlsx"
        if os.path.exists(bill_filename):
            # Open with default program (Excel)
            subprocess.Popen([bill_filename], shell=True)
        else:
            messagebox.showerror("Error", f"Bill file {bill_filename} not found!")

    ttk.Button(form, text="Open Bill", command=open_bill).pack(pady=10)


# login for reset login page 
def reset_stock_login_form(app):
    form = tk.Toplevel(app)
    form.title("Login to Reset Stock")
    form.geometry("300x200")

    ttk.Label(form, text="Select Username").pack(pady=10)
    usernames = ["admin", "manager", "staff"]  # you can expand this list
    user_var = tk.StringVar()
    user_dropdown = ttk.Combobox(form, textvariable=user_var, values=usernames, state="readonly")
    user_dropdown.pack(pady=5)

    def login_and_reset():
        if user_var.get() == "admin":  # only admin can reset
            confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to delete ALL stock items?")
            if confirm:
                stock.reset_stock(app.active_file)
        else:
            messagebox.showerror("Access Denied", "Only admin can reset stock!")

    ttk.Button(form, text="Login & Reset", command=login_and_reset).pack(pady=10)
