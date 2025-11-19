@echo off
echo ============================================================
echo Building V3.exe
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
if exist V3.spec del V3.spec
if exist McAfee_Automation.spec del McAfee_Automation.spec
echo.

echo [3/4] Building EXE (this may take 3-5 minutes)...
echo Please wait...
echo.
python -m PyInstaller --onefile --console --name "V3" mcafee_automation.py
if %errorlevel% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo.

echo [4/4] Installing Playwright browsers for the EXE...
echo.
python -m playwright install chromium
echo.

echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Your EXE file: dist\V3.exe
echo Size: ~50-100 MB
echo.
echo IMPORTANT: To distribute to friends:
echo.
echo 1. Copy these files to a folder:
echo    - dist\V3.exe
echo    - accounts.txt (empty template)
echo    - numbers.txt (empty template)
echo    - setup_for_friends.bat
echo.
echo 2. They run setup_for_friends.bat ONCE
echo 3. Then use V3.exe forever (no license needed!)
echo.
pause
