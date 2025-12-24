# DSB Registration Automation Script

This script automates the registration process on https://www.dsb.dk/auth/opret using Playwright and concurrent workers.

## Features

- Automated cookie consent handling (declines cookies)
- Account registration with email and password
- Multiple phone number iterations per account
- Concurrent worker support for faster processing
- Thread-safe phone number management
- Human-like clicking behavior
- Detailed logging with loguru
- Progress tracking with tqdm

## Requirements

```bash
pip install playwright undetected-playwright loguru tqdm
playwright install chromium
```

## File Format

### accounts.txt
Format: `email:password`

Example:
```
test1@example.com:Password123
test2@example.com:Password456
test3@example.com:Password789
```

### numbers.txt
Format: One phone number per line

Example:
```
77123456
77234567
77345678
```

## How It Works

1. Opens https://www.dsb.dk/auth/opret
2. Declines cookie consent if shown
3. Fills in email and password (twice)
4. Sets birthdate to 11/11/2000
5. Clicks "Opret profil" button
6. For each iteration:
   - Generates random first name (8 characters)
   - Generates random last name (10 characters)
   - Selects Armenia (+374) as country code
   - Enters next phone number from numbers.txt
   - Clicks "Næste" button
   - Waits for "Tilbage" button and clicks it
   - Repeats for the specified number of iterations

## Usage

Run the script:
```bash
python dsb_automation.py
```

You will be prompted for:
1. **Number of iterations per account**: How many phone numbers to use per account (e.g., 10)
2. **Number of concurrent workers**: How many accounts to process simultaneously (e.g., 3)

## Output Files

- `dsb_completed.txt` - Successfully registered accounts with format: `email:password:phone:firstname:lastname`
- `dsb_failed.txt` - Failed accounts with error messages

## Example

If you have:
- 3 accounts in accounts.txt
- 30 phone numbers in numbers.txt
- Set iterations to 10
- Set workers to 2

The script will:
- Process 2 accounts concurrently
- Each account will use 10 different phone numbers
- Total: 30 phone numbers used for 3 accounts

## Notes

- The script runs in headless mode (no browser window)
- Uses stealth mode to avoid detection
- Includes random delays for human-like behavior
- Thread-safe for concurrent execution
- Automatically validates phone number availability

## Troubleshooting

- If cookie banner doesn't appear, the script will continue automatically
- If phone numbers run out, the script will stop iterations for that account
- Check dsb_failed.txt for any errors
- Increase timeout values if website is slow
