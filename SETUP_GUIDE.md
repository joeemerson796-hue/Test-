# McAfee Automation - Setup Guide (Windows)

## Quick Setup

### Just double-click:
```
setup.bat
```

That's it! Everything will install automatically.

---

## What Gets Installed

1. **playwright** - Browser automation
2. **undetected-playwright** - Stealth mode
3. **loguru** - Logging
4. **tqdm** - Progress bars
5. **Chromium browser** (~300MB)

---

## Manual Setup (if setup.bat doesn't work)

### Step 1: Install packages
```bash
pip install -r requirements.txt
```

### Step 2: Install Chromium (REQUIRED!)
```bash
playwright install chromium
```

### Step 3: Run the script
```bash
python mcafee_automation.py
```

---

## System Requirements

- **Windows:** 10 or 11
- **Python:** 3.8 or higher
- **Disk Space:** ~500 MB
- **RAM:** 2 GB minimum

---

## Files You Need

Give these to friends:
- ✅ mcafee_automation.py
- ✅ license_system.py
- ✅ accounts.txt (empty template)
- ✅ numbers.txt (empty template)
- ✅ requirements.txt
- ✅ setup.bat
- ✅ SETUP_GUIDE.md

Keep for yourself:
- ❌ generate_key.py (only you should have this!)

---

## Troubleshooting

### Error: "Python not found"
- Install Python from: https://www.python.org/downloads/
- During install, check "Add Python to PATH"

### Error: "pip not found"
```bash
python -m pip install -r requirements.txt
```

### Error: "Browser not found"
```bash
playwright install chromium
```

### Error: "Permission denied"
- Right-click setup.bat → Run as Administrator

---

## First Run

1. Double-click `setup.bat` and wait
2. Run: `python mcafee_automation.py`
3. Copy your Hardware ID
4. Send Hardware ID to script owner
5. Get license key from owner
6. Enter license key when prompted
7. Done! Script is activated

---

## Quick Start for Friends

1. Download all files
2. Double-click `setup.bat`
3. Wait for installation (3-5 minutes)
4. Run: `python mcafee_automation.py`
5. Get license key from you
6. Enter key and start using!

---

**That's it!** 🚀
