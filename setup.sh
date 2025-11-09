#!/bin/bash

echo "========================================"
echo "McAfee Automation Setup Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python3 is not installed"
    echo "Please install Python3 first"
    exit 1
fi

echo "Python3 is installed"
echo ""

echo "Installing required packages..."
echo ""

# Install Python packages
pip install playwright
pip install undetected-playwright
pip install loguru
pip install tqdm

echo ""
echo "Installing Playwright browser (Chromium)..."
echo ""

# Install Playwright browsers
playwright install chromium

echo ""
echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo ""
echo "You can now run the script with:"
echo "python3 mcafee_automation.py"
echo ""
