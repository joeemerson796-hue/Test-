@echo off
echo ========================================
echo McAfee Automation Setup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python is installed
echo.

echo Installing required packages...
echo.

REM Install Python packages
pip install playwright
pip install undetected-playwright
pip install loguru
pip install tqdm

echo.
echo Installing Playwright browser (Chromium)...
echo.

REM Install Playwright browsers
playwright install chromium

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo You can now run the script with:
echo python mcafee_automation.py
echo.
pause
