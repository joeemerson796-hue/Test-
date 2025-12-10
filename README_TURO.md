# Turo Signup Automation Script

This script automates the Turo signup process using Playwright with multiple concurrent workers.

## Features

- **Multi-threaded execution**: Run multiple signups concurrently
- **Stealth mode**: Uses undetected-playwright to avoid detection
- **Human-like interactions**: Simulates mouse movements and random delays
- **Thread-safe operations**: Safe file reading/writing with multiple workers
- **Progress tracking**: Real-time progress bar showing completion status
- **Automatic cleanup**: Removes used phone numbers from the pool

## Requirements

- Python 3.8+
- Playwright
- undetected-playwright
- loguru
- tqdm

Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

## Input Files

The script requires the following input files:

### 1. `accounts.txt`
Email addresses (one per line):
```
email1@example.com
email2@example.com
email3@example.com
```

### 2. `password.txt`
Passwords (one per line):
```
Password123!
SecurePass456
MyPass789
```
Note: Passwords are reused in a round-robin fashion if there are more accounts than passwords.

### 3. `country.txt`
Country names (one per line, must match Turo's dropdown exactly):
```
Angola
Kenya
Nigeria
```
Note: Countries are reused in a round-robin fashion if there are more accounts than countries.

### 4. `numbers.txt`
Phone numbers (one per line):
```
770651959
770651960
770651961
```
Note: Each phone number is used once and then removed from the file.

## How It Works

For each account, the script:

1. Opens the Turo signup page: https://turo.com/us/en/sign-up/email?next=%2Fus%2Fen%2Fdrivers%2F52266563
2. Clicks "Continue with email"
3. Generates random first name (10 characters)
4. Generates random last name (10 characters)
5. Enters email from `accounts.txt`
6. Enters password from `password.txt`
7. Checks the Terms of Service checkbox
8. Clicks "Sign up" button
9. Saves account credentials to `created.txt` as `email:password`
10. Waits 2 seconds
11. Opens phone number change page: https://turo.com/us/en/account/change-phone-number?next=/us/en/account
12. Selects country from `country.txt`
13. Enters phone number from `numbers.txt`
14. Clicks "Send code" button
15. Removes used phone number from `numbers.txt`

## Usage

1. Prepare all input files (accounts.txt, password.txt, country.txt, numbers.txt)

2. Run the script:
```bash
python turo_signup_automation.py
```

3. Enter the number of concurrent workers when prompted:
```
Number of concurrent workers: 5
```

4. The script will process all accounts and show progress in real-time

## Output Files

### `created.txt`
Successfully created accounts:
```
email1@example.com:Password123!
email2@example.com:SecurePass456
```

### `failed.txt`
Failed accounts with error messages:
```
email3@example.com:MyPass789 - Error: Timeout waiting for element
```

## Worker Configuration

- **Low load**: 1-3 workers (safer, slower)
- **Medium load**: 4-6 workers (balanced)
- **High load**: 7-10 workers (faster, but may trigger anti-bot measures)

Start with fewer workers and gradually increase based on success rate.

## Important Notes

- The script runs in **headless mode** (no visible browser)
- Uses **stealth techniques** to avoid bot detection
- Implements **human-like delays** and mouse movements
- **Thread-safe** operations ensure no data corruption with multiple workers
- Phone numbers are **permanently removed** after use
- Passwords and countries **loop** if there are fewer than accounts

## Troubleshooting

### "No more phone numbers available"
- Add more phone numbers to `numbers.txt`
- Each account requires one unique phone number

### "Timeout waiting for element"
- Website may have changed its structure
- Check your internet connection
- Try reducing the number of concurrent workers

### Script stops unexpectedly
- Check `failed.txt` for error details
- Ensure all input files are properly formatted
- Verify Playwright is installed: `playwright install chromium`

## Security Warning

This script is for **educational purposes only**. Automating signups may violate Turo's Terms of Service. Use at your own risk.

## License

This script follows the same license as the other automation scripts in this repository.
