# AWS Automation Scripts Guide

This project has been split into **two separate scripts** for better control and reliability:

## 📋 Overview

### 1. **aws_creation_script.py** - Account Creation
Creates AWS accounts from scratch up to payment submission (Step 3 of 5)

### 2. **aws_login_complete.py** - Login & Phone Verification
Logs into created accounts and completes phone verification

---

## 🚀 Script 1: AWS Account Creation

### What it does:
- ✅ Email verification with captcha
- ✅ Email OTP verification
- ✅ Password creation
- ✅ Account plan selection (Free)
- ✅ Personal information
- ✅ Address details
- ✅ Payment information
- ✅ **Stops after submitting payment (Step 3 of 5)**

### Input Files Required:
- `accounts.txt` - Format: `email:hotmailpassword:refreshtoken:clientid`
- `password.txt` - Contains the AWS password to use
- `cards.txt` - Contains credit card number

### Output:
- `created.txt` - Format: `email:hotmailpassword:refreshtoken:clientid:awspassword`
- `failed.txt` - Failed accounts with error messages

### Usage:
```bash
python aws_creation_script.py
# Enter number of threads when prompted
```

### Configuration (Top of script):
```python
COUNTRY_NAME = "Mozambique"           # Change country
PHONE_CODE = "+258"
PHONE_NUMBER = "573596-0999"
ADDRESS_LINE = "Avenue de Bouillon 38"
CITY = "Maputo"
POSTAL_CODE = "1100"
```

---

## 🔐 Script 2: AWS Login & Completion

### What it does:
- ✅ Logs into AWS account
- ✅ Handles email OTP during login
- ✅ Completes phone verification
- ✅ Solves captcha if appears
- ✅ **Retry loop (3 attempts)** with page refresh
- ✅ Keeps browser open for **manual SMS code entry**

### Input Files Required:
- `created.txt` - Format: `email:hotmailpassword:refreshtoken:clientid:awspassword`
- `numbers.txt` - Phone numbers for verification (one per line)

### Output:
- `completed.txt` - Successfully completed accounts
- `failed.txt` - Failed accounts with error messages

### Usage:
```bash
python aws_login_complete.py
# Enter number of threads when prompted
```

### Configuration (Top of script):
```python
COUNTRY_NAME = "Mozambique"           # Country for phone verification
PHONE_NUMBER_FROM_FILE = True         # Read from numbers.txt
PHONE_NUMBER_DEFAULT = "573596-0999"  # Fallback if not from file
```

### Important Features:
- **Browser stays open** after retry loop for you to manually enter SMS codes
- **60-second wait** before auto-closing (Press Ctrl+C to close earlier)
- **Automatic page refresh** and retry (3 times) to get SMS codes
- **2-second wait** after captcha submit (marked with comment for easy modification)

---

## 📁 File Formats

### accounts.txt (Input for Script 1):
```
email1@hotmail.com:hotmailpass1:refreshtoken1:clientid1
email2@hotmail.com:hotmailpass2:refreshtoken2:clientid2
```

### created.txt (Output from Script 1 / Input for Script 2):
```
email1@hotmail.com:hotmailpass1:refreshtoken1:clientid1:AwsPassword123
email2@hotmail.com:hotmailpass2:refreshtoken2:clientid2:AwsPassword123
```

### numbers.txt (Input for Script 2):
```
573596-0999
573596-1000
573596-1001
```

### password.txt (Input for Script 1):
```
YourAWSPassword123!
```

### cards.txt (Input for Script 1):
```
4111111111111111
```

---

## ⚙️ Adjustable Wait Times

Both scripts have **marked comments** for easy wait time adjustments:

### Script 1 & 2 - Captcha Submit Wait:
```python
submit_button.click()
time.sleep(2)  # WAIT TIME AFTER CAPTCHA SUBMIT - Change this if needed (in seconds)
```

### Script 2 - Send SMS Wait:
```python
send_sms_button.click()
time.sleep(2)  # WAIT TIME AFTER SEND SMS - Change this if needed (in seconds)
```

---

## 🔄 Typical Workflow

1. **Run Creation Script**:
   ```bash
   python aws_creation_script.py
   ```
   - Creates accounts up to payment submission
   - Saves to `created.txt`

2. **Review created.txt**:
   - Check which accounts were successfully created

3. **Run Login/Completion Script**:
   ```bash
   python aws_login_complete.py
   ```
   - Logs into accounts from `created.txt`
   - Completes phone verification
   - Browser stays open for manual SMS entry

4. **Manual SMS Entry**:
   - After 3 retry attempts, browser stays open
   - Manually enter SMS codes from your phone
   - Press Ctrl+C or wait 60 seconds when done

---

## 🛠️ Troubleshooting

### Creation Script Issues:
- **Captcha fails**: Increase retry attempts in code or check YesCaptcha API
- **Email OTP not found**: Wait longer or check Hotmail OAuth tokens
- **Country not found**: Verify `COUNTRY_NAME` matches dropdown exactly

### Login Script Issues:
- **Login OTP not appearing**: Normal if account doesn't require it
- **Phone verification not found**: Check if account completed creation properly
- **SMS not received**: Use retry loop (refreshes 3 times automatically)

---

## 🎯 Key Differences from Original Script

### Why Split?
1. **Better Control**: Create accounts separately from phone verification
2. **Failure Recovery**: If phone verification fails, you can retry without recreating account
3. **Manual Intervention**: Keep browser open to manually enter SMS codes
4. **Debugging**: Easier to identify which step failed

### Data Flow:
```
accounts.txt → [Script 1] → created.txt → [Script 2] → completed.txt
```

---

## 📝 Notes

- Both scripts support **multi-threading** for parallel processing
- All wait times are optimized for speed while maintaining reliability
- **Error alerts** are automatically detected and handled with retries
- Full **hotmail details** are saved for future use
- **Human-like behavior** with random delays to avoid detection

---

## 🔧 Quick Config Changes

To change **country** for a different region:

```python
# In both scripts, change these at the top:
COUNTRY_NAME = "Brazil"        # Or any other country
PHONE_CODE = "+55"             # Country code
PHONE_NUMBER = "11999999999"   # Local number format
ADDRESS_LINE = "Rua Example 123"
CITY = "São Paulo"
POSTAL_CODE = "01000-000"
```

---

**Happy Automating! 🚀**
