@echo off
echo ================================================
echo Building PayPal Automation EXE
echo ================================================
echo.

echo Installing PyInstaller if needed...
pip install pyinstaller
echo.

echo Building executable...
python -m PyInstaller --onefile --console --name "PayPal_V1" paypal_automation.py
echo.

echo ================================================
echo Build complete!
echo EXE location: dist\PayPal_V1.exe
echo ================================================
pause
