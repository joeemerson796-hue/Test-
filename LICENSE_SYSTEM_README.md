# License System for McAfee Automation Script

## Overview

The script now includes a **device-locked license system**. Each license key is tied to a specific device and will only work on that device.

## Files

- `license_system.py` - Core license validation system
- `generate_key.py` - Key generator (for script owner only)
- `mcafee_automation.py` - Main script (now requires license)
- `license.key` - License key file (auto-created after activation)

## How It Works

### 1. Hardware Fingerprinting

Each device has a unique "Hardware ID" generated from:
- MAC Address
- Hostname
- System type
- Disk serial number

### 2. License Key Generation

License keys are cryptographically tied to the Hardware ID:
```
License Key = HASH(Hardware ID + SECRET_KEY)
```

This means:
- ✅ A key generated for Device A will ONLY work on Device A
- ❌ The same key will NOT work on Device B
- ✅ Keys are permanent (long-term)

## For Script Owner (You)

### Giving the Script to Friends

**Step 1: Give them the script files**
```
- mcafee_automation.py
- license_system.py
- accounts.txt
- numbers.txt
```

**Step 2: They run the script**
When they run it for the first time, they'll see:
```
❌ LICENSE NOT FOUND OR INVALID!

Your Hardware ID:
------------------------------------------------------------
a1b2c3d4e5f6...  (64 character hash)
------------------------------------------------------------

Send this Hardware ID to the script owner to get a license key.
```

**Step 3: Generate a key for their device**

Run the key generator:
```bash
python generate_key.py
```

Choose option 2 and enter their Hardware ID:
```
Choose an option:
1. Generate key for THIS device
2. Generate key for ANOTHER device (need Hardware ID)

Enter choice (1 or 2): 2

Enter the Hardware ID from the other device:
Hardware ID: a1b2c3d4e5f6...

============================================================
Generated License Key for that device:
------------------------------------------------------------
f9e8d7c6b5a4...  (64 character hash)
------------------------------------------------------------

Send this key to your friend!
```

**Step 4: Give them the license key**

Send them the generated key. They enter it in the script:
```
License Key (or press Enter to exit): f9e8d7c6b5a4...

Activating license...
✅ LICENSE ACTIVATED SUCCESSFULLY!
```

**Step 5: Done!**

The script creates a `license.key` file and they can use it forever on that device!

## For Your Friends (Script Users)

### First Time Setup

1. Run the script:
   ```bash
   python mcafee_automation.py
   ```

2. Copy your Hardware ID from the error message

3. Send the Hardware ID to the script owner

4. They will give you a License Key

5. Enter the License Key when prompted

6. Done! The script will work on your device

### After Activation

Once activated, the script will:
- Create a `license.key` file
- Automatically validate on every run
- Work forever on your device
- No need to enter the key again

## Security Features

✅ **Device-Locked** - Keys only work on the device they were generated for

✅ **Hardware Fingerprinting** - Uses multiple hardware identifiers

✅ **Cryptographic Hashing** - Keys are SHA-256 hashed

✅ **Secret Key Protection** - Keys require knowledge of the SECRET_KEY

✅ **Persistent** - Once activated, license persists across restarts

## Customization

### Change the Secret Key

Edit `license_system.py` and change the SECRET_KEY:

```python
# Change this to your own unique secret!
SECRET_KEY = "Your_Own_Secret_Key_Here_2025"
```

⚠️ **IMPORTANT:**
- Keep this secret private!
- If you change it, all existing keys will become invalid
- Generate new keys after changing the secret

## Troubleshooting

### "Invalid License Key" Error

**Cause:** The key doesn't match this device

**Solution:**
1. Get your current Hardware ID (run the script)
2. Ask the script owner to generate a NEW key for your current Hardware ID
3. Don't copy keys from other devices!

### License File Deleted

**Cause:** `license.key` file was deleted

**Solution:**
1. Run the script again
2. Re-enter your license key (ask script owner if you lost it)

### Moving to a New Device

**Cause:** Hardware changed or new computer

**Solution:**
1. Get your NEW Hardware ID
2. Ask script owner for a NEW key
3. Old key won't work on new device

## Example Workflow

### Scenario: Giving script to 3 friends

**Friend 1:**
- Hardware ID: `abc123...`
- You generate key: `key1...`
- They activate with `key1`
- ✅ Works on Friend 1's device only

**Friend 2:**
- Hardware ID: `def456...`
- You generate key: `key2...`
- They activate with `key2`
- ✅ Works on Friend 2's device only

**Friend 3:**
- Tries to use `key1` from Friend 1
- ❌ INVALID - key1 only works on Friend 1's device
- Gets their own Hardware ID: `ghi789...`
- You generate key: `key3...`
- They activate with `key3`
- ✅ Works on Friend 3's device only

## Notes

- 📌 Each friend needs their own unique key
- 📌 Keys are tied to hardware - can't be shared
- 📌 One key = one device, forever
- 📌 Keys don't expire
- 📌 You control who gets keys

---

**Enjoy your protected script!** 🔒
