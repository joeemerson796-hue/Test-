# AWS Account Registration Automation

This script automates the AWS account registration process using Playwright and YesCaptcha API.

## Features

- ✅ Automated email verification using Hotmail/Outlook IMAP OAuth2
- ✅ **iframe-based captcha solving** using YesCaptcha API (handles AWS Security Verification modal)
- ✅ **Auto-retry logic for incorrect captcha** (up to 5 attempts with error detection)
- ✅ Full AWS signup flow automation (all 5 steps)
- ✅ Multi-threaded execution for concurrent account creation
- ✅ Human-like typing and clicking simulation
- ✅ Automatic retry logic for phone verification (3 attempts)
- ✅ Thread-safe file operations
- ✅ Progress tracking with tqdm
- ✅ Fallback captcha handling for both iframe and non-iframe captchas

## Prerequisites

### Required Python Packages

```bash
pip install playwright
pip install undetected-playwright
pip install loguru
pip install tqdm
pip install requests
```

### Install Playwright Browsers

```bash
playwright install chromium
```

## Required Files

Create the following files in the same directory as the script:

### 1. `accounts.txt`
Format: `email:hotmail_password:refresh_token:client_id`

Example:
```
ezequielavalosaolq@hotmail.com:MyPassword123:0.AX0Aabcd1234...:00000000-1234-5678-9abc-def012345678
anotheremail@hotmail.com:Password456:0.AX0Axyz7890...:00000000-9876-5432-1abc-fed098765432
```

### 2. `password.txt`
Single AWS password for all accounts (must meet AWS requirements):
```
MySecureAWSPass123!
```

### 3. `cards.txt`
Credit card numbers (one per line):
```
4532015112830366
5425233430109903
```

### 4. `numbers.txt`
Phone numbers for verification (one per line):
```
841234567
842345678
```

## How It Works

### Step-by-Step Process

1. **Email Submission**
   - Opens AWS signup page
   - Enters Hotmail email address
   - Enters account name (username from email)
   - Clicks "Verify email address"

2. **Captcha Solving (iframe-based with auto-retry)**
   - Iframe appears automatically after clicking "Verify email address"
   - Switches to iframe context
   - Waits for captcha image inside iframe
   - Downloads captcha image
   - Sends to YesCaptcha API for solving
   - Enters solution inside iframe
   - Submits captcha
   - **Detects error message** "That wasn't quite right, please try again"
   - **Automatically retries up to 5 times** if captcha is incorrect
   - Clears input and tries new solution on each retry
   - Includes fallback for non-iframe captchas

3. **Email Verification**
   - Connects to Hotmail via IMAP OAuth2
   - Retrieves 6-digit verification code from AWS email
   - Enters code on AWS page

4. **Password Setup**
   - Sets AWS account password
   - Confirms password
   - Proceeds to step 1 of 5

5. **Contact Information (Step 2 of 5)**
   - Selects "Personal" account type
   - Sets phone code to Mozambique (+258)
   - Generates random full name (12 characters)
   - Enters phone: 573596-0999
   - Selects country: Mozambique
   - Fills address: Avenue de Bouillon 38
   - City: Libramont-Chevigny
   - State: Luxembourg
   - Postal code: 6800
   - Checks AWS Customer Agreement
   - Clicks "Agree and Continue"

6. **Payment Information (Step 3 of 5)**
   - Enters card number from cards.txt
   - Selects expiration month (random)
   - Selects expiration year: 2027
   - Generates random CVV (3 digits)
   - Generates random account holder name (12 characters)
   - Clicks "Verify and continue"

7. **Phone Verification (Step 4 of 5)**
   - Selects Mozambique (+258)
   - Enters phone from numbers.txt
   - Clicks "Send SMS"
   - Solves another captcha
   - Retries 3 times with page refresh

8. **Account Saved**
   - Successfully created accounts saved to `created.txt`
   - Failed accounts logged to `failed.txt`

## Usage

1. Prepare all required files (accounts.txt, password.txt, cards.txt, numbers.txt)

2. Run the script:
```bash
python aws_registration_automation.py
```

3. Enter the number of concurrent workers when prompted:
```
Number of concurrent workers: 3
```

4. Monitor the progress in the terminal

## Output Files

- **created.txt**: Successfully created accounts (format: `email:aws_password`)
- **failed.txt**: Failed accounts with error messages

## Configuration

### YesCaptcha API Key

The script uses YesCaptcha for captcha solving. Update the API key in the script:

```python
YESCAPTCHA_CLIENT_KEY = "your_api_key_here"
```

### Headless Mode

To run in headless mode (no browser window), change in the script:

```python
browser = playwright.chromium.launch(headless=True)
```

## Features Explained

### Human-Like Behavior

- Random delays between keystrokes (0.05-0.15 seconds)
- Mouse movement simulation before clicks
- Random positioning within clickable elements
- Realistic timing between actions

### Thread Safety

- All file operations are protected with locks
- Safe concurrent execution of multiple workers
- No race conditions when writing to output files

### Error Handling

- Comprehensive exception handling
- Automatic retry logic for transient failures
- Detailed error logging
- Graceful browser cleanup

### Email Verification

- OAuth2 authentication for Hotmail/Outlook
- Automatic email polling (12 attempts, 5 seconds apart)
- Regex extraction of 6-digit verification codes
- Connection reuse for better performance

## Troubleshooting

### Common Issues

1. **"No verification email received"**
   - Check refresh token and client ID are valid
   - Ensure Hotmail account is accessible
   - Verify email hasn't been flagged as spam

2. **"Failed to solve captcha"**
   - Script automatically retries up to 5 times per captcha
   - Check YesCaptcha API key is valid
   - Ensure sufficient API credits
   - Check YesCaptcha solve accuracy (should be >80%)
   - Script detects "That wasn't quite right" errors and retries automatically

3. **Timeout errors**
   - Increase timeout values in the script
   - Check internet connection
   - Reduce number of concurrent workers

4. **Element not found errors**
   - AWS may have updated their UI
   - Check element selectors in the script
   - Run in non-headless mode to debug

5. **Iframe captcha issues**
   - The script handles AWS's iframe-based Security Verification modal
   - If captcha isn't detected, check browser console for iframe loading errors
   - Script includes fallback for non-iframe captchas
   - Ensure JavaScript is enabled in Playwright

## Notes

- The script uses **Mozambique (+258)** as the default country and phone code
- Account holder names and full names are randomly generated (12 characters)
- Phone verification is attempted 3 times with page refresh
- Each account is saved immediately after step 2 completion
- The script uses undetected-playwright to avoid bot detection

## Security Considerations

- **Never share your accounts.txt file** (contains sensitive credentials)
- Keep YesCaptcha API key secure
- Use strong passwords in password.txt
- Review AWS terms of service before automation

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Run in non-headless mode to see what's happening
3. Verify all input files are formatted correctly
4. Ensure all dependencies are installed

## Credits

Based on reference scripts:
- xm_registration_automation.py
- xm_email_verifier.py
- wish_store_automation.py
