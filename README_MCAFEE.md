# McAfee Login Automation Script

## Features
- Automates McAfee login and 2FA setup process
- Supports single account or multiple accounts
- Multi-threaded worker support for bulk operations
- Handles dynamic class names using stable selectors
- Progress tracking with tqdm
- Detailed logging with loguru

## Setup

1. Install required dependencies:
```bash
pip install playwright undetected-playwright loguru tqdm
playwright install chromium
```

2. Prepare your accounts file (for multiple accounts mode):
   - Create `accounts.txt` in the same directory
   - Format: `email:password:phone_number` (one per line)
   - Example:
     ```
     ukjzpmsj7061@hotmail.com:Gouda123:770651959
     user2@example.com:Pass456:770651960
     ```

## Usage

### Single Account Mode
```bash
python mcafee_automation.py
```
- Select option `1`
- Enter email, password, and phone number when prompted

### Multiple Accounts Mode
```bash
python mcafee_automation.py
```
- Select option `2`
- Specify number of concurrent workers
- Accounts will be loaded from `accounts.txt`

## What the Script Does

1. Navigates to McAfee login page
2. Enters email and password
3. Clicks sign in button
4. Waits for "Enable 2FA" button and clicks it
5. Changes country from Egypt to Kenya
6. Enters phone number
7. Clicks continue
8. Repeatedly clicks "Resend" button until max attempts message appears

## Output Files

- `completed.txt` - Successfully processed accounts
- `failed.txt` - Failed accounts with error messages

## Notes

- Set `headless=False` in the script to see the browser (useful for debugging)
- Set `headless=True` for production runs without GUI
- The script uses stable selectors (IDs, aria-labels, text content) to handle dynamic class names
- Includes proper waits and timeouts for stability

## Troubleshooting

- If elements are not found, the page structure may have changed
- Check the console logs for detailed error messages
- Try running with `headless=False` to see what's happening
- Adjust timeout values if your internet connection is slow
