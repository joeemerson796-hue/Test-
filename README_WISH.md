# Wish Merchant Store Setup Automation

This script automates the creation of Wish merchant stores using Playwright with concurrent workers.

## Features

- 🚀 **Automated Store Creation**: Automatically creates Wish merchant stores with random names
- 📋 **Complete Address Form Filling**: Auto-fills personal information with random data
- 📞 **Phone Verification Loop**: Sends verification code 5 times per account
- 🌍 **Country Selection**: Automatically selects country from configuration
- 🔄 **Multi-threading Support**: Process multiple accounts concurrently
- 🤖 **Captcha Solving**: Integrated YesCaptcha API for automatic captcha solving
- 📊 **Progress Tracking**: Real-time progress bar showing completion status
- 💾 **Result Logging**: Saves successful and failed attempts to separate files

## Prerequisites

1. Python 3.8 or higher
2. Required Python packages (install via `pip install -r requirements.txt`):
   - playwright
   - undetected-playwright
   - loguru
   - tqdm
   - requests

3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## File Setup

### 1. `accounts.txt`
Contains email:password pairs (one per line):
```
email1@example.com:password1
email2@example.com:password2
email3@example.com:password3
```

### 2. `password.txt`
Contains a single password that will be used for all Wish merchant stores:
```
YourStorePassword123!
```

### 3. `country.txt`
Contains a single country name that will be selected for all stores:
```
Nigeria
```
**Note**: Country name must match exactly as it appears in the Wish country dropdown (e.g., "Nigeria", "United States", "United Kingdom").

### 4. `numbers.txt`
Contains phone numbers (one per line):
```
+2348012345678
+2348023456789
+2348034567890
```
**Note**: If you have more accounts than phone numbers, phone numbers will be cycled (reused).

## YesCaptcha API Configuration

The script uses YesCaptcha API for solving captchas. The API key is configured in the script:
```python
YESCAPTCHA_CLIENT_KEY = "8d381f04402598ed227557a6acb91a6da1a909c375946"
```

Make sure you have sufficient balance in your YesCaptcha account.

## How It Works

### Phase 1: Initial Store Setup

1. **Opens Wish Merchant Signup**: Navigates to `https://merchant.wish.com/open-express?r=802OI`

2. **Fills Store Name**: Generates a random 12-character store name (letters + numbers)

3. **Enters Email**: Uses email from `accounts.txt`

4. **Enters Password**: Uses password from `password.txt`

5. **Solves Captcha**:
   - Captures the captcha image from the page
   - Converts it to base64
   - Sends to YesCaptcha API for OCR
   - Enters the solved captcha text

6. **Submits Initial Form**: Clicks the Continue button

### Phase 2: Address & Phone Verification Loop (5 iterations)

For each account, the script performs the following 5 times:

7. **Fills Personal Information**:
   - **First Name**: Random 8 characters (letters)
   - **Last Name**: Random 8 characters (letters)
   - **Street Address**: Random 10 characters (letters)

8. **Selects Country**: Uses country from `country.txt`

9. **Fills Location Details**:
   - **State**: Random 8 characters (letters)
   - **City**: Random 8 characters (letters)
   - **Postal Code**: Random 6 digits

10. **Enters Phone Number**: Uses phone number from `numbers.txt`

11. **Clicks "Send verification code"**: Triggers SMS verification

12. **Refreshes Page**: Reloads the page to repeat the process (except on the 5th iteration)

13. **Repeats Steps 7-12**: Continues for a total of 5 iterations

14. **Logs Results**: After all 5 iterations, saves results to `completed.txt` and failures to `failed.txt`

## Usage

1. Make sure all required files are set up:
   - `accounts.txt` with your email accounts
   - `password.txt` with your store password
   - `country.txt` with your target country
   - `numbers.txt` with phone numbers

2. Run the script:
   ```bash
   python wish_store_automation.py
   ```

3. When prompted, enter the number of concurrent workers:
   ```
   Number of concurrent workers: 3
   ```

4. The script will:
   - Process all accounts from `accounts.txt`
   - Pair each account with a phone number from `numbers.txt`
   - Complete initial signup with captcha solving
   - Fill address form and send verification code 5 times per account
   - Run multiple workers in parallel
   - Show progress bar with completion status
   - Save results to `completed.txt` and `failed.txt`

## Output Files

- **`completed.txt`**: Successfully processed accounts with all 5 verification attempts
  ```
  email@example.com:password - Store: RandomName12 - Phone: +2348012345678
  ```

- **`failed.txt`**: Failed attempts with error messages
  ```
  email@example.com - Error: Failed to fill address form on iteration 3
  email2@example.com - Error: Captcha solving failed
  ```

## Features in Detail

### Random Data Generation
- **Store Name**: 12 random characters (letters + numbers) - Example: `aB3xT9kL2pQ1`
- **First Name**: 8 random letters - Example: `JhFkTpQw`
- **Last Name**: 8 random letters - Example: `MnBvCxZa`
- **Street Address**: 10 random letters - Example: `KjHgFdSaWq`
- **State**: 8 random letters - Example: `LpMnBvCx`
- **City**: 8 random letters - Example: `QwErTyUi`
- **Postal Code**: 6 random digits - Example: `123456`

All data is generated uniquely for each iteration to avoid detection.

### Human-like Behavior
- Random typing delays between characters
- Mouse movement simulation before clicks
- Random delays between actions
- Helps avoid detection

### Captcha Solving Process
1. Detects captcha image on page
2. Downloads captcha image bytes
3. Converts to base64 format
4. Sends to YesCaptcha API with task type `ImageToTextTaskMuggle`
5. Polls API every 2 seconds for result (max 60 seconds)
6. Returns solved text and fills into form

### Phone Verification Loop
Each account goes through 5 iterations of phone verification:
1. **Iteration 1**: Fill form + Send verification code
2. **Refresh**: Page reloads
3. **Iteration 2**: Fill form again (same phone) + Send verification code
4. **Refresh**: Page reloads
5. **Iteration 3**: Fill form again (same phone) + Send verification code
6. **Refresh**: Page reloads
7. **Iteration 4**: Fill form again (same phone) + Send verification code
8. **Refresh**: Page reloads
9. **Iteration 5**: Fill form again (same phone) + Send verification code
10. **Complete**: Close browser and move to next account

This process helps verify the phone number multiple times as per Wish's requirements.

### Thread-Safe Operations
- File operations use locks to prevent race conditions
- Safe for concurrent workers
- Progress bar updates atomically

## Troubleshooting

### Script fails to find elements
- Check if Wish has changed their page structure
- Update CSS selectors in the script if needed

### Captcha solving fails
- Check YesCaptcha API balance
- Verify API key is correct
- Check network connectivity

### Browser doesn't open
- Make sure Playwright browsers are installed: `playwright install chromium`
- Check system requirements for running Chrome

### Workers are too slow
- Reduce number of concurrent workers
- Check system resources (CPU, RAM)

## Performance Tips

- **Worker Count**: Start with 2-3 workers and increase based on system performance
- **Network**: Ensure stable internet connection for captcha API calls
- **System Resources**: Each worker opens a browser instance (requires ~200-300MB RAM)

## Security Notes

- Store API keys securely
- Don't share your `accounts.txt` or `password.txt` files
- Use unique passwords for each service
- Be aware of Wish's terms of service regarding automation

## Example Run

```
Wish Merchant Store Setup Automation Script
==================================================
Loaded 5 accounts from accounts.txt
Loaded store password from password.txt
Loaded country: Nigeria
Loaded 3 phone numbers from numbers.txt
Created 5 tasks
Accounts: 5, Phone numbers: 3
Number of concurrent workers: 2

INFO: Worker-1: Starting automation for email1@example.com with phone +2348012345678
INFO: Worker-2: Starting automation for email2@example.com with phone +2348023456789
INFO: Worker-1: Generated store name: aB3xT9kL2pQ1
INFO: Worker-1: Entering email: email1@example.com
INFO: Worker-1: Captcha solved: ABC123
INFO: Worker-1: Clicking Continue button...
INFO: Worker-1: Starting phone verification loop (5 iterations)...
INFO: Worker-1: === Iteration 1/5 ===
INFO: Worker-1: Filling address form...
INFO: Worker-1: First name: JhFkTpQw
INFO: Worker-1: Last name: MnBvCxZa
INFO: Worker-1: Selected country: Nigeria
INFO: Worker-1: Phone number: +2348012345678
INFO: Worker-1: Clicked 'Send verification code' button
INFO: Worker-1: Refreshing page for next iteration...
INFO: Worker-1: === Iteration 2/5 ===
...
INFO: Worker-1: === Iteration 5/5 ===
SUCCESS: Worker-1: Completed all 5 phone verification attempts for email1@example.com

Progress: 100%|████████████████████████| 5/5 [15:45<00:00, 189s/account]

Script finished!
Press Enter to exit...
```

## Support

For issues or questions:
1. Check the log output for detailed error messages
2. Verify all input files are properly formatted
3. Ensure YesCaptcha API is working and has balance

## License

This script is for educational and authorized use only. Make sure you comply with Wish's terms of service.
