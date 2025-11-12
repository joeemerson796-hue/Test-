#!/bin/bash

echo "============================================================"
echo "McAfee Automation Scripts - Setup"
echo "============================================================"
echo ""

echo "[1/4] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi
python3 --version
echo "Python found!"
echo ""

echo "[2/4] Installing Python packages..."
echo "This may take a few minutes..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Python packages!"
    exit 1
fi
echo "Python packages installed successfully!"
echo ""

echo "[3/4] Installing Chromium browser for automation..."
echo "This may take a few minutes and requires ~300MB disk space..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Chromium browser!"
    exit 1
fi
echo "Chromium browser installed successfully!"
echo ""

echo "[4/4] Verifying installation..."
python3 -c "import playwright; import loguru; import tqdm; import requests; print('All packages imported successfully!')"
if [ $? -ne 0 ]; then
    echo "WARNING: Some packages may not have installed correctly!"
else
    echo "All packages verified!"
fi
echo ""

echo "============================================================"
echo "Setup completed successfully!"
echo "============================================================"
echo ""
echo "You can now run:"
echo "  - python3 mcafee_automation.py (Browser automation)"
echo "  - python3 mcafee_otp_bot.py (Telegram OTP bot)"
echo "  - python3 generate_key.py (License key generator)"
echo ""
