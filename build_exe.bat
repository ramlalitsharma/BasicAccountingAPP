@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set VERSION=2.5.0
set APP_NAME=AccountingPro
set DIST_DIR=_build
set TEMP_DIR=_temp

echo ============================================
echo  Building %APP_NAME% v%VERSION%
echo ============================================
echo.

REM Clean previous build
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"

REM Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet

REM Build executable
echo [2/4] Building executable with PyInstaller...
pyinstaller --onefile --windowed --name "%APP_NAME%" ^
  --distpath "%DIST_DIR%" ^
  --workpath "%TEMP_DIR%" ^
  --specpath "%TEMP_DIR%" ^
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

REM Update version metadata on the exe (if ResourceHacker available)
if exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo [3/4] Embedding version info...
    REM Optional: use verpatch or ResourceHacker to set version metadata
    REM verpatch "%DIST_DIR%\%APP_NAME%.exe" /va %VERSION% /pv %VERSION% /high /company "Accounting Pro" /desc "%APP_NAME%" /product "%APP_NAME%" /copyright "© %DATE:~-4%"
)

REM Clean up
echo [4/4] Cleaning up temporary files...
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"

echo.
echo ============================================
if exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo  SUCCESS
    echo  Output: %DIST_DIR%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%.exe") do (
        set FILESIZE=%%~zI
        set /A SIZEMB=!FILESIZE! / 1048576
        echo  Size: !SIZEMB! MB
    )
) else (
    echo  FAILED - Check output above
)
echo ============================================
echo.
echo To create installer:
echo   1. Open installer\setup.iss in Inno Setup
echo   2. Press Ctrl+F9 to compile
echo.
pause