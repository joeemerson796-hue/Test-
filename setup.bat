@echo off
echo ============================================================
echo McAfee Automation Scripts - Setup
echo ============================================================
echo.

echo [1/4] Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)
echo Python found!
echo.

echo [2/4] Installing Python packages...
echo This may take a few minutes...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python packages!
    pause
    exit /b 1
)
echo Python packages installed successfully!
echo.

echo [3/4] Installing Chromium browser for automation...
echo This may take a few minutes and requires ~300MB disk space...
playwright install chromium
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Chromium browser!
    pause
    exit /b 1
)
echo Chromium browser installed successfully!
echo.

echo [4/4] Verifying installation...
python -c "import playwright; import loguru; import tqdm; import requests; print('All packages imported successfully!')"
if %errorlevel% neq 0 (
    echo WARNING: Some packages may not have installed correctly!
    pause
) else (
    echo All packages verified!
)
echo.

echo ============================================================
echo Setup completed successfully!
echo ============================================================
echo.
echo You can now run:
echo   - mcafee_automation.py (Browser automation)
echo   - mcafee_otp_bot.py (Telegram OTP bot)
echo   - generate_key.py (License key generator)
echo.
pause
