@echo off
echo ============================================================
echo Building McAfee Automation to EXE
echo ============================================================
echo.

echo [1/4] Installing PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller!
    pause
    exit /b 1
)
echo.

echo [2/4] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist McAfee_Automation.spec del McAfee_Automation.spec
echo.

echo [3/4] Building EXE (this may take 3-5 minutes)...
echo Please wait...
echo.
pyinstaller --onefile --console --name "McAfee_Automation" --add-data "license_system.py;." mcafee_automation.py
if %errorlevel% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo.

echo [4/4] Installing Playwright browsers for the EXE...
echo.
playwright install chromium
echo.

echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Your EXE file: dist\McAfee_Automation.exe
echo Size: ~50-100 MB
echo.
echo IMPORTANT: To distribute to friends:
echo.
echo 1. Copy these files to a folder:
echo    - dist\McAfee_Automation.exe
echo    - accounts.txt (empty template)
echo    - numbers.txt (empty template)
echo.
echo 2. They also need to install:
echo    - Python 3.8+ (from python.org)
echo    - Playwright: pip install playwright
echo    - Browser: playwright install chromium
echo.
echo OR use the portable version (see BUILD_EXE_GUIDE.md)
echo.
pause
