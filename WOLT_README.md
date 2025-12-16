# Wolt Account Creator with Temp Mail API

Automated script to create Wolt accounts using the Priyo temp mail API and Playwright.

## Features

- Uses free.priyo.email API for temporary emails
- Automated account creation on Wolt.com
- Parallel processing with multiple workers
- SMS verification resend (4 attempts per number)
- Saves account details to file

## Prerequisites

```bash
npm install playwright
npx playwright install chromium
```

## Setup

1. **Create `keys.txt`** with your Priyo Email API keys (one per line):
```
7jkmE5NM2VS6GqJ9pzlI
another-api-key-here
```

2. **Create `numbers.txt`** with Ukrainian phone numbers WITHOUT +380 prefix (one per line):
```
501234567
502345678
503456789
```

## Usage

```bash
node wolt_temp_mail.js
```

## How It Works

1. Gets a random email from Priyo Email API
2. Opens Wolt.com and clicks "Sign up"
3. Enters the email and waits for verification email
4. Fetches verification link from email API
5. Opens verification link and completes registration:
   - Country: Hungary
   - Random first name (9 characters)
   - Random last name (10 characters)
   - Phone country: Ukraine (+380)
   - Phone number from numbers.txt
6. Sends SMS verification code
7. Clicks "I didn't get a code" and "Resend code by SMS" 4 times
8. Saves account details to `wolt_accounts.txt`
9. Moves to next number

## Configuration

You can adjust concurrent workers in the script:

```javascript
const maxConcurrentWorkers = 3; // Change this number
```

## Output

Account details are saved to `wolt_accounts.txt` in format:
```
Email: example@priyomail.top | Password: abc123 | Name: Firstname Lastname | Phone: +380501234567
```

## Notes

- The script uses visible browser windows (headless: false)
- Each account creation takes approximately 1-2 minutes
- API keys are rotated among phone numbers
- Ukrainian phone numbers should be 9 digits without country code
