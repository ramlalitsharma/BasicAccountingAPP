Accounting Pro v2.5.0 - Professional Accounting Suite
====================================================

A desktop accounting application with Excel-based data storage.
Built with Python & Tkinter.

FEATURES
--------
- Dashboard with business overview
- Supplier & Customer management (CRUD + CSV import/export)
- Stock inventory with low-stock alerts
- Sales recording with auto-stock deduction
- Purchase orders (auto-adds to stock)
- Professional GST-compliant invoice printing
- Monthly, yearly & daily sales reports
- P&L reports with profit margin calculation
- Dark/Light theme support
- Subscription-based licensing system
- Auto-backup on exit
- Single-instance lock

SYSTEM REQUIREMENTS
-------------------
- Windows 7, 8, 10, or 11 (64-bit)
- No Python required (standalone executable)

INSTALLATION
------------
1. Run AccountingPro_Setup_v2.5.0.exe
2. Follow the installer wizard
3. Launch from Start Menu or Desktop shortcut

FIRST TIME USE
--------------
1. The app will ask to create a new workbook or open existing
2. Choose "Yes" to create a new Excel workbook
3. Data is saved in the app's data/ folder as .xlsx files

FOR DEVELOPERS
--------------
Source: https://github.com/yourusername/accounting-pro
To build from source:
  pip install -r requirements.txt
  pyinstaller --onefile --windowed --name "AccountingPro" main.py

To create installer:
  1. Run build_exe.bat to build the .exe
  2. Open installer/setup.iss with Inno Setup
  3. Compile (Ctrl+F9)

CONTACT
-------
support@accountingpro.example.com
