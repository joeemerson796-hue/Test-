@echo off
echo ============================================================
echo McAfee Automation Script - Setup (Windows)
echo ============================================================
echo.

echo [1/4] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python is not installed!
    echo Download Python from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo Python OK!
echo.

echo [2/4] Installing packages...
echo This may take a few minutes...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install packages!
    pause
    exit /b 1
)
echo Packages installed!
echo.

echo [3/4] Installing Chromium browser...
echo This may take a few minutes (~300MB download)...
playwright install chromium
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install Chromium!
    pause
    exit /b 1
)
echo Chromium installed!
echo.

echo [4/4] Testing installation...
python -c "import playwright; import loguru; import tqdm; print('All packages OK!')"
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Package verification failed!
    pause
) else (
    echo All packages verified!
)
echo.

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo You can now run: python mcafee_automation.py
echo.
pause
