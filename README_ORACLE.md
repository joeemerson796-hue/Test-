# Oracle Account Creation with Hotmail

This script creates Oracle Cloud accounts using Hotmail/Outlook email accounts instead of temporary email services.

## Features

- Uses real Hotmail/Outlook accounts from `accounts.txt`
- Supports both OAuth2 and basic IMAP authentication
- Automatically checks email inbox for Oracle verification links via IMAP
- Multi-threaded account creation
- Saves successful and failed accounts separately

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Configuration Files

### 1. `accounts.txt`
Contains Hotmail/Outlook accounts in one of these formats:

**Format 1 (OAuth2 - Recommended):**
```
email@hotmail.com:password:refresh_token:client_id
```

**Format 2 (Basic Auth):**
```
email@hotmail.com:password
```

**Note:** OAuth2 is more reliable for modern Outlook accounts. To get OAuth2 tokens:
- Register an app in Azure AD
- Get refresh token and client ID
- Format: `email:password:refresh_token:client_id`

### 2. `password.txt`
Contains the password to use for all Oracle accounts:
```
YourOraclePassword123!
```

### 3. `country.txt`
Contains the country for Oracle registration:
```
Egypt +20
```

Format: `CountryName +CountryCode`

Examples:
- `Egypt +20`
- `United States +1`
- `United Kingdom +44`

## Usage

1. Prepare your configuration files:
   - Add Hotmail accounts to `accounts.txt`
   - Set Oracle password in `password.txt`
   - Set country in `country.txt`

2. Run the script:
```bash
python oracle_hotmail_automation.py
```

3. Enter:
   - Number of Oracle accounts to create
   - Number of concurrent workers (threads)

## Output Files

- `oracle_accounts.txt` - Successfully created Oracle accounts (format: `email:password`)
- `oracle_failed.txt` - Failed account creation attempts with error details

## How It Works

1. Reads Hotmail accounts from `accounts.txt`
2. For each account:
   - Opens Oracle registration page
   - Fills form with Hotmail email and random personal details
   - Submits registration
   - Connects to Hotmail inbox via IMAP
   - Waits for Oracle verification email from `oracle-acct_ww@oracle.com`
   - Extracts verification link
   - Opens verification link in new tab
   - Saves successful account to `oracle_accounts.txt`

## Troubleshooting

### IMAP Connection Failed
- Ensure IMAP is enabled in your Hotmail/Outlook account settings
- For OAuth2: Verify your refresh token and client ID are valid
- For basic auth: Some accounts may have basic auth disabled

### No Verification Email
- Check if Oracle emails are in spam/junk folder manually
- Increase timeout in script (default: 120 seconds)
- Verify the Hotmail account can receive emails

### Account Creation Failed
- Check if country format in `country.txt` matches Oracle's expected format
- Ensure password meets Oracle requirements (uppercase, lowercase, numbers, special chars)
- Check browser console for errors (run in non-headless mode)

## Notes

- The script uses undetected-playwright to avoid bot detection
- Each worker opens a separate browser instance
- Recommended: Start with 1-2 workers to test before scaling up
- Make sure you have enough Hotmail accounts for the number of Oracle accounts you want to create
