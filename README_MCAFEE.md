# McAfee Login Automation Script

## Features
- Automates McAfee login and 2FA setup process
- Multi-threaded worker support for bulk operations
- Human-like sign-in behavior with mouse movements and random delays
- Handles dynamic class names using stable selectors
- Automatic phone number rotation from pool
- Progress tracking with tqdm
- Detailed logging with loguru
- Automatically moves to next account when max resend attempts reached

## Setup

### Quick Setup (Recommended)

**For Windows:**
- Double-click `setup.bat` and wait for installation to complete

**For Linux/Mac:**
```bash
bash setup.sh
```

### Manual Setup

1. Install required dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Prepare your files:
   - **accounts.txt**: Email and password combinations (format: `email:password`)
     ```
     ukjzpmsj7061@hotmail.com:Gouda123
     user2@example.com:Pass456
     ```

   - **numbers.txt**: Phone numbers (one per line, without country code)
     ```
     770651959
     770651960
     770651961
     ```

## Usage

```bash
python mcafee_automation.py
```
- Enter number of concurrent workers when prompted
- Accounts will be loaded from `accounts.txt`
- Phone numbers will be automatically assigned from `numbers.txt`

## What the Script Does

1. Navigates to McAfee login page
2. Enters email and password
3. Clicks sign in button with **human-like behavior** (mouse movements, random delays)
4. Waits for "Enable 2FA" button and clicks it
5. Changes country from Egypt to Kenya (searches and selects)
6. Enters phone number from pool
7. Clicks continue
8. Repeatedly clicks "Resend" button until max attempts message appears
9. **Immediately moves to next account** when "You've reached the maximum number of resend attempts" message is displayed

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
