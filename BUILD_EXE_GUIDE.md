# Building McAfee Automation to EXE

## Quick Build (Recommended)

### Step 1: Run the Build Script
```bash
build_exe.bat
```

This will:
- Install PyInstaller
- Build McAfee_Automation.exe
- Create it in the `dist` folder

### Step 2: Your EXE is Ready!
```
Location: dist\McAfee_Automation.exe
Size: ~50-100 MB
```

---

## What You Get

### Single EXE File
- ✅ No Python installation needed on user's computer
- ✅ Includes license system
- ✅ ~50-100 MB file size
- ✅ Double-click to run

### Requirements on User's Computer
The EXE still needs:
- ❌ Playwright browsers installed
- ❌ Or bundle everything (see below)

---

## Option 1: Simple EXE (Smaller, Needs Setup)

**What you give friends:**
```
McAfee_Automation.exe
accounts.txt
numbers.txt
setup_browsers.bat  (see below)
```

**They run:**
1. `setup_browsers.bat` (one-time setup)
2. `McAfee_Automation.exe` (use forever)

**Create setup_browsers.bat:**
```batch
@echo off
echo Installing Chromium browser...
pip install playwright
playwright install chromium
echo Done! You can now run McAfee_Automation.exe
pause
```

---

## Option 2: Fully Portable (No Setup, Larger)

To make it 100% portable with NO requirements:

### Step 1: Build with All Dependencies
```batch
pyinstaller --onefile --console ^
  --name "McAfee_Automation" ^
  --add-data "license_system.py;." ^
  --hidden-import=playwright ^
  --hidden-import=undetected_playwright ^
  --collect-all playwright ^
  mcafee_automation.py
```

### Step 2: Bundle Chromium Browser

After building, copy browser files:
```batch
# Find playwright browsers location:
python -c "from playwright.driver import compute_driver_executable; print(compute_driver_executable())"

# Copy to dist folder with EXE
# Note: This adds ~300MB!
```

**Result:** 400-500 MB portable folder (no installation needed!)

---

## What I Recommend

### For You (Script Owner):
Use **Option 1** - Simple EXE

**Give friends:**
1. `McAfee_Automation.exe` (from dist folder)
2. `setup_browsers.bat` (one-time browser installer)
3. `accounts.txt`
4. `numbers.txt`

**They do:**
1. Run `setup_browsers.bat` once
2. Use `McAfee_Automation.exe` forever

### Pros:
- ✅ Small download (~50-100 MB vs 400+ MB)
- ✅ Easy to update (just send new .exe)
- ✅ Still simple for friends (2-click setup)

---

## Build Commands Reference

### Basic Build (Small, needs browser install):
```batch
pyinstaller --onefile --console --name "McAfee_Automation" mcafee_automation.py
```

### With License System:
```batch
pyinstaller --onefile --console --name "McAfee_Automation" --add-data "license_system.py;." mcafee_automation.py
```

### With Icon:
```batch
pyinstaller --onefile --console --name "McAfee_Automation" --icon=icon.ico --add-data "license_system.py;." mcafee_automation.py
```

### Fully Bundled (Large):
```batch
pyinstaller --onefile --console --name "McAfee_Automation" --add-data "license_system.py;." --collect-all playwright mcafee_automation.py
```

---

## Troubleshooting

### Error: "ModuleNotFoundError: license_system"
**Fix:** Use `--add-data "license_system.py;."`

### Error: "Playwright browser not found"
**Fix:** Users need to run: `playwright install chromium`

### EXE is too large (>400 MB)
**Cause:** Bundled browser files
**Fix:** Use simple EXE + setup script approach

### EXE won't run on other PCs
**Cause:** Missing Visual C++ Redistributable
**Fix:** Install from: https://aka.ms/vs/17/release/vc_redist.x64.exe

---

## Quick Setup for Friends

**Create: setup_for_friends.bat**
```batch
@echo off
echo ============================================================
echo McAfee Automation - First Time Setup
echo ============================================================
echo.
echo [1/2] Installing browser (one-time, ~300MB)...
pip install playwright
playwright install chromium
echo.
echo [2/2] Setup complete!
echo.
echo You can now run: McAfee_Automation.exe
echo.
pause
```

**Give them:**
- McAfee_Automation.exe
- setup_for_friends.bat
- accounts.txt
- numbers.txt

**They run:**
1. `setup_for_friends.bat` (first time only)
2. `McAfee_Automation.exe` (every time)

---

## File Sizes

| Build Type | Size | Setup Needed |
|------------|------|--------------|
| Simple EXE | 50-100 MB | Browser install |
| Fully Bundled | 400-500 MB | None |
| Python Script | 0.1 MB | Full install |

---

## Summary

**Easiest for friends:**
```
1. build_exe.bat → Creates McAfee_Automation.exe
2. Give them .exe + setup_for_friends.bat
3. They run setup once, then use .exe forever
```

**100% portable (no setup):**
```
Possible but creates 400+ MB file
Not recommended unless necessary
```

---

**I recommend Option 1!** ✅
