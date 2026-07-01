@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set VERSION=2.8.0
set APP_NAME=AccountingPro
set DIST_DIR=dist
set INSTALLER_DIR=installer
set SCRIPT_DIR=%~dp0

echo ============================================
echo  Building %APP_NAME% v%VERSION% (Full Pipeline)
echo ============================================
echo.

REM Step 1: Install dependencies
echo [1/5] Installing Python dependencies...
pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo FAILED: pip install
    pause
    exit /b 1
)
echo  Done.

REM Step 2: Clean previous builds
echo [2/5] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
echo  Done.

REM Step 3: Build executable with PyInstaller
echo [3/5] Building executable using AccountingPro.spec (this may take several minutes)...
pyinstaller AccountingPro.spec --noconfirm

if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo FAILED: PyInstaller build did not produce executable
    pause
    exit /b 1
)

for %%I in ("%DIST_DIR%\%APP_NAME%.exe") do (
    set FILESIZE=%%~zI
    set /A SIZEMB=!FILESIZE! / 1048576
)
echo  SUCCESS - Executable size: !SIZEMB! MB

REM Step 4: Build installer with Inno Setup
echo [4/5] Building installer with Inno Setup...
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\Compil32.exe"
if not exist %INNO_PATH% (
    set INNO_PATH="C:\Program Files\Inno Setup 6\Compil32.exe"
)
if not exist %INNO_PATH% (
    set INNO_PATH="%LOCALAPPDATA%\Programs\Inno Setup 6\Compil32.exe"
)
if exist %INNO_PATH% (
    %INNO_PATH% /cc "%SCRIPT_DIR%installer\setup.iss"
    if exist "%INSTALLER_DIR%\AccountingPro_Setup_v%VERSION%.exe" (
        echo  SUCCESS - Installer created
    ) else (
        echo  WARNING: Inno Setup compilation may have failed.
        echo  Open installer\setup.iss manually in Inno Setup and press Ctrl+F9.
    )
) else (
    echo  WARNING: Inno Setup not found at %INNO_PATH%
    echo  To create installer:
    echo    1. Open installer\setup.iss in Inno Setup
    echo    2. Press Ctrl+F9 to compile
    echo.
)

REM Step 5: Clean up temp files
echo [5/5] Cleaning up temporary files...
if exist "build" rmdir /s /q "build"
echo  Done.

echo.
echo ============================================
echo  BUILD COMPLETE
echo ============================================
echo  Executable: %DIST_DIR%\%APP_NAME%.exe (!SIZEMB! MB)
if exist "%INSTALLER_DIR%\AccountingPro_Setup_v%VERSION%.exe" (
    echo  Installer:  %INSTALLER_DIR%\AccountingPro_Setup_v%VERSION%.exe
)
echo ============================================
echo.
pause
