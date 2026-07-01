@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set VERSION=2.8.0
set APP_NAME=AccountingPro
set DIST_DIR=dist

echo ============================================
echo  Building %APP_NAME% v%VERSION%
echo ============================================
echo.

REM Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt --quiet

REM Build executable using the .spec file
echo [2/3] Building executable with PyInstaller (spec: AccountingPro.spec)...
pyinstaller AccountingPro.spec --noconfirm

REM Output result
echo [3/3] Build complete.
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