@echo off
echo ============================================================
echo McAfee Automation - First Time Setup
echo ============================================================
echo.
echo This is a ONE-TIME setup. It will:
echo 1. Install Playwright library
echo 2. Download Chromium browser (~300MB)
echo.
echo This may take 5-10 minutes depending on your internet speed.
echo.
pause
echo.

echo [1/2] Installing Playwright...
pip install playwright
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install Playwright!
    echo Make sure Python is installed: python.org
    pause
    exit /b 1
)
echo Playwright installed!
echo.

echo [2/2] Downloading Chromium browser (~300MB)...
echo This may take a few minutes...
playwright install chromium
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install Chromium!
    pause
    exit /b 1
)
echo.

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo You can now run: McAfee_Automation.exe
echo.
echo You only need to run this setup ONCE.
echo Next time, just double-click McAfee_Automation.exe
echo.
pause
