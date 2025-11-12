# Setup Guide

## Quick Setup

### Windows:
```bash
# Double-click setup.bat
# OR run in Command Prompt:
setup.bat
```

### Linux/macOS:
```bash
# Make executable and run:
chmod +x setup.sh
./setup.sh
```

---

## Manual Setup

If the automatic setup doesn't work, follow these steps:

### Step 1: Install Python Packages
```bash
pip install -r requirements.txt
```

### Step 2: Install Chromium Browser (REQUIRED!)
```bash
playwright install chromium
```

### Step 3: Verify Installation
```bash
python -c "import playwright; print('Playwright OK')"
python -c "import loguru; print('Loguru OK')"
python -c "import tqdm; print('Tqdm OK')"
python -c "import requests; print('Requests OK')"
```

---

## What Gets Installed

### Python Packages:
- **playwright** - Browser automation
- **undetected-playwright** - Stealth browser automation
- **loguru** - Beautiful logging
- **tqdm** - Progress bars
- **requests** - HTTP requests

### Browser:
- **Chromium** (~300MB) - Automated browser

---

## After Setup

### 1. Run McAfee Automation:
```bash
python mcafee_automation.py
```

### 2. Run OTP Bot:
```bash
python mcafee_otp_bot.py
```

### 3. Generate License Keys:
```bash
python generate_key.py
```

---

## Troubleshooting

### Error: "playwright not found"
```bash
pip install --upgrade pip
pip install playwright
playwright install chromium
```

### Error: "Browser executable not found"
```bash
playwright install chromium
```

### Error: "Permission denied" (Linux)
```bash
chmod +x setup.sh
./setup.sh
```

### Error: "pip not recognized"
```bash
# Use python -m pip instead:
python -m pip install -r requirements.txt
```

---

## System Requirements

- **Python:** 3.8 or higher
- **Disk Space:** ~500 MB
- **RAM:** 2 GB minimum
- **OS:** Windows 10+, Linux, macOS

---

## Files Needed

**For friends (users):**
- mcafee_automation.py
- license_system.py
- accounts.txt
- numbers.txt
- requirements.txt
- setup.bat (Windows) or setup.sh (Linux/macOS)

**Keep for yourself (admin):**
- generate_key.py

---

## Quick Test

After setup, test if everything works:

```bash
# Test license system
python generate_key.py

# Test automation (will ask for license)
python mcafee_automation.py

# Test OTP bot
python mcafee_otp_bot.py
```

---

**Setup complete!** 🚀
