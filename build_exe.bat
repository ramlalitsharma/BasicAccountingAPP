@echo off
echo ============================================
echo Building Accounting Pro Executable
echo ============================================
echo.

pyinstaller --onefile --windowed --name "AccountingPro" ^
  --distpath "_build" ^
  --workpath "_temp" ^
  --specpath "_temp" ^
  --icon "icon\accounting_pro.ico" ^
  --add-data "config.py;." ^
  --add-data "database;database" ^
  --add-data "ui;ui" ^
  --add-data "utils;utils" ^
  --add-data "icon;icon" ^
  --hidden-import openpyxl ^
  --hidden-import openpyxl.cell._writer ^
  --hidden-import openpyxl.styles ^
  --collect-all openpyxl ^
  --exclude-module torch --exclude-module torchvision --exclude-module torchaudio ^
  --exclude-module numpy --exclude-module pandas --exclude-module matplotlib ^
  --exclude-module scipy --exclude-module tensorflow --exclude-module keras ^
  --exclude-module sklearn --exclude-module Pillow --exclude-module lxml ^
  --exclude-module pytest --exclude-module setuptools --exclude-module distutils ^
  --exclude-module pip ^
  --noconfirm ^
  main.py

echo.
echo ============================================
if exist _build\AccountingPro.exe (
    echo SUCCESS: _build\AccountingPro.exe created
    dir _build\AccountingPro.exe
) else (
    echo FAILED: Check build output above
)
echo ============================================
pause
