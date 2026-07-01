Accounting Pro v2.8.0 - Professional Accounting Suite
====================================================

A professional desktop accounting application with Excel-based data storage.
Built with Python, Tkinter, and Matplotlib.

FEATURES
--------
- Smart Dashboard with KPI metrics and interactive charts
- Revenue trends, payment breakdown, monthly comparisons, stock by category
- Pending payments popup (click Pending Payments card)
- Supplier & Customer management (CRUD + CSV import/export)
- Customer profiles with full transaction history and invoice view
- Stock inventory with low-stock highlighting and alerts
- Sales recording with auto-stock deduction and auto-fill price
- Payment status tracking (paid/unpaid/partial) with receipt numbers
- Invoice generation with company details and GST support
- Purchase orders (auto-adds to stock)
- Extra Income management with full CRUD and reporting
- Preorders with status tracking and completion workflow
- Advanced Reports with Sales, Purchases, Combined tabs
- Monthly, yearly & daily sales reports
- P&L reports with profit margin calculation
- Mandatory auto-update system (server-controlled, no skip)
- License management (Free/Pro/Enterprise tiers with HMAC key validation)
- Dark sidebar with modern professional UI
- Auto-backup on exit
- Single-instance lock
- Inno Setup installer with VC++ Redistributable auto-download

SYSTEM REQUIREMENTS
-------------------
- Windows 7, 8, 10, or 11 (64-bit)
- No Python required (standalone executable)

DOWNLOAD LATEST VERSION
-----------------------
https://github.com/ramlalitsharma/BasicAccountingAPP/releases

INSTALLATION
------------
1. Download AccountingPro_Setup_v2.8.0.exe from releases
2. Run the installer and follow the wizard
3. Launch from Start Menu or Desktop shortcut

FIRST TIME USE
--------------
1. The app will prompt to create a new workbook or open existing
2. Choose "Yes" to create a new Excel workbook
3. Data is saved in the app's data/ folder as .xlsx files

FOR DEVELOPERS (Building from Source)
-------------------------------------
Prerequisites:
  - Python 3.9+
  - pip (Python package manager)
  - Inno Setup 6+ (optional, for creating installer)

Steps:
  1. Clone the repository
  2. Install dependencies:
       pip install -r requirements.txt
  3. Run directly (no build needed):
       python main.py

  4. Build standalone executable:
       pyinstaller AccountingPro.spec --noconfirm --clean

  5. Build installer (after step 4):
       - Open installer/setup.iss with Inno Setup
       - Press Ctrl+F9 to compile
       - Output: installer/AccountingPro_Setup_v2.8.0.exe

Source: https://github.com/ramlalitsharma/BasicAccountingAPP
