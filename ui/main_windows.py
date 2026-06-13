from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import font
from modules import stock, sales, suppliers
from ui.form import add_supplier_form, new_sale_form, view_suppliers_form, view_sales_form, view_stock_form
from ui.form import add_stock_item_form
from ui.form import print_bill_form, reset_stock_login_form

class AccountingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Accounting Software")
        self.geometry("800x600")
        self.active_file = None

        

        menu_font = font.Font(family="Arial", size=18, weight="bold")
        menubar = tk.Menu(self, font=menu_font, bg="orange", fg="black")

        # Add spacing before menus to simulate center alignment
        menubar.add_command(label=">>>>>>>>>>>>>>>>>>>>>>>>>>>>>")  # spacer

        # Inside AccountingApp.__init__:
        suppliers_menu = tk.Menu(menubar, tearoff=0, font=("Arial", 16), bg="orange", fg="black")
        suppliers_menu.add_command(label="Add Supplier", command=lambda: add_supplier_form(self))
        suppliers_menu.add_command(label="View Suppliers", command=lambda: view_suppliers_form(self))
        menubar.add_cascade(label="Suppliers", menu=suppliers_menu)

        sales_menu = tk.Menu(menubar, tearoff=0, font=("Arial", 16), bg="orange", fg="black")
        sales_menu.add_command(label="New Sale", command=lambda: new_sale_form(self))
        sales_menu.add_command(label="View Sales", command=lambda: view_sales_form(self))
        menubar.add_cascade(label="Sales", menu=sales_menu)

        # Reports menu
        reports_menu = tk.Menu(menubar, tearoff=0, font=("Arial", 16), bg="orange", fg="black")
        reports_menu.add_command(label="Monthly Report")
        reports_menu.add_command(label="Profit & Loss")
        menubar.add_cascade(label="  Reports  ", menu=reports_menu,)

        #stock menu
        stock_menu = tk.Menu(menubar, tearoff=0, bg="orange", fg="black", font=("Arial", 16))
        stock_menu.add_command(label="Create New Stock", command=self.create_new_stock)
        stock_menu.add_command(label="Add Item", command=lambda: add_stock_item_form(self))
        stock_menu.add_command(label="View Stock", command=lambda: view_stock_form(self))
        menubar.add_cascade(label="Stock", menu=stock_menu)


        # Add spacing before menus to simulate center alignment
        menubar.add_command(label=">>>>>>>>>>>>>>>>>>>>>>>>>>>>>")  # spacer


       # rest button for reset stock  
        stock_menu.add_command(label="Reset Stock (Login)", command=lambda: reset_stock_login_form(self))

        #print button for printing bill
        bill_menu = tk.Menu(menubar, tearoff=0)
        bill_menu.add_command(label="Print Bill", command=lambda: print_bill_form(self))
        bill_menu.add_command(label="Save Bill", command=lambda: print_bill_form(self))
        menubar.add_cascade(label="Bills", menu=bill_menu)


        self.config(menu=menubar)

        # Methods in AccountingApp:
    def add_supplier(self):
        if not self.active_file:
            messagebox.showwarning("No File", "Please create or select a stock file first!")
            return
        

    def view_suppliers(self):
        if not self.active_file:
            messagebox.showwarning("No File", "Please create or select a stock file first!")
            return
        

    def new_sale(self):
        if not self.active_file:
            messagebox.showwarning("No File", "Please create or select a stock file first!")
            return

    def view_sales(self):
        if not self.active_file:
            messagebox.showwarning("No File", "Please create or select a stock file first!")
            return
        items = sales.get_sales(self.active_file)
        messagebox.showinfo("Sales", f"Sales records:\n{items}")
         

    def create_new_stock(self):
        choice = messagebox.askquestion("Stock Setup",
            "Do you want to create a NEW Excel file?\n\nClick 'Yes' for new, 'No' to browse existing.")

        if choice == "yes":
            self.active_file = stock.create_new_stock_file()
            messagebox.showinfo("Success", f"New stock file created at {self.active_file}")
        else:
            filepath = filedialog.askopenfilename(title="Select Existing Stock File",
                                                  filetypes=[("Excel files", "*.xlsx")])
            if filepath:
                self.active_file = filepath
                messagebox.showinfo("File Selected", f"You selected: {filepath}")
            else:
                messagebox.showwarning("No File", "No file selected!")

    def add_item(self):
        if not self.active_file:
            messagebox.showwarning("No File", "Please create or select a stock file first!")
            return

 
