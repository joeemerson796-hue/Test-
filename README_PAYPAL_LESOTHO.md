# PayPal Lesotho Signup Automation

This script automates the PayPal signup process for Lesotho accounts using Playwright.

## Features

- Automated country selection (Lesotho)
- Email and phone number input from text files
- Automated resend code clicking until limit reached
- Multi-threaded execution for processing multiple accounts
- Human-like interactions to avoid detection
- Progress tracking with visual progress bar

## Prerequisites

1. Python 3.7+
2. Required packages (install via `requirements.txt`):
   - playwright
   - undetected-playwright
   - loguru
   - tqdm

## Installation

### Windows
```bat
setup.bat
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

## Input Files

### accounts.txt
Format: `email:password` (one per line)
```
example1@email.com:Password123
example2@email.com:Password456
```

### numbers.txt
Format: Phone numbers (one per line)
```
770651959
770651960
```

## How It Works

1. **Navigate to PayPal signup page**: Opens the PayPal Lesotho signup URL
2. **Select Lesotho**: Automatically selects Lesotho from the country dropdown
3. **Click Get Started**: Proceeds to the signup form
4. **Enter email**: Fills in email from `accounts.txt`
5. **Click Next**: Proceeds to phone verification
6. **Enter phone number**: Fills in phone number from `numbers.txt`
7. **Click Next**: Initiates phone verification
8. **Resend loop**: Continuously clicks "Resend code" until the error message appears:
   - Target message: "Sorry, we can't send a new code right now. Try again later."
9. **Move to next account**: Proceeds with the next email/phone combination

## Usage

```bash
python paypal_lesotho_automation.py
```

When prompted, enter the number of concurrent workers (threads) to run:
```
Number of concurrent workers: 5
```

## Output Files

- `completed.txt`: Successfully processed accounts
- `failed.txt`: Accounts that encountered errors

## Script Flow

```
Start
  ↓
Load accounts.txt and numbers.txt
  ↓
Select number of concurrent workers
  ↓
For each account:
  ├─ Open PayPal signup page
  ├─ Select Lesotho
  ├─ Enter email
  ├─ Enter phone number
  ├─ Click resend until blocked
  └─ Save to completed.txt
  ↓
End
```

## Error Handling

- Logs all errors to `failed.txt` with detailed error messages
- Continues processing remaining accounts even if one fails
- Thread-safe file operations for concurrent execution

## Notes

- The script runs in visible browser mode (`headless=False`) for debugging
- Uses human-like delays and interactions to mimic real user behavior
- Phone numbers are cycled through if you have fewer numbers than accounts
- Safety limit of 100 resends per account to prevent infinite loops

## Troubleshooting

1. **Browser doesn't open**: Ensure Playwright is properly installed
   ```bash
   playwright install chromium
   ```

2. **Element not found errors**: The PayPal page structure may have changed. Check the element selectors in the script.

3. **Too many workers**: Reduce the number of concurrent workers to avoid rate limiting or system resource issues.

## Warning

This script is for educational purposes only. Automated signup processes may violate PayPal's Terms of Service. Use at your own risk.
