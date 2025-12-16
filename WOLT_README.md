# Wolt Account Creator (Python + Async)

Fast automated script to create Wolt accounts using Priyo temp mail API and Playwright.

## Features

- ⚡ **Fast async/await** implementation with parallel workers
- 🛡️ **Robust error handling** - continues on failures
- 💬 **Interactive worker selection** - prompts you at runtime
- 🍪 **Auto-handles cookies** - waits and declines consent modal
- 🔧 **Smart iframe detection** - works with modals or iframes
- 📧 Uses free.priyo.email API for temporary emails
- 🤖 Automated account creation on Wolt.com
- 🔄 SMS verification resend (4 attempts per number)
- 💾 Saves account details to file
- 📊 Real-time progress tracking

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Create your files
echo "your-api-key" > keys.txt
echo "501234567" > numbers.txt

# Run script
python wolt_creator.py

# It will ask: "How many workers do you need?"
# Type number (or press Enter for default 3)
```

## Setup

1. **Create `keys.txt`** with Priyo Email API keys (one per line):
```
7jkmE5NM2VS6GqJ9pzlI
another-api-key
```

2. **Create `numbers.txt`** with Ukrainian phone numbers WITHOUT +380 prefix (one per line):
```
501234567
502345678
503456789
```

## Usage

```bash
python wolt_creator.py
```

**Interactive Prompt:**
```
How many workers do you need? (default 3): 5
```

- Press Enter for default (3 workers)
- Type a number (1-10)
- For 10+ workers, you'll get a warning confirmation

## How It Works

1. Gets random email from Priyo Email API
2. Opens Wolt.com and clicks "Sign up"
3. Enters email and waits for verification email
4. Fetches verification link from email API (auto-retries)
5. Opens verification link and completes registration:
   - Country: Hungary
   - Random first name (9 chars)
   - Random last name (10 chars)
   - Phone country: Ukraine (+380)
   - Phone number from numbers.txt
6. Sends SMS verification code
7. Resends SMS 4 times
8. Saves account to `wolt_accounts.txt`
9. Moves to next number (errors don't stop other accounts)

## Configuration

**Runtime (Interactive):**
- Script asks "How many workers?" when you run it
- Default: 3 workers
- Range: 1-10 (10+ needs confirmation)

**Script Variables** (edit in `wolt_creator.py`):
```python
MAX_EMAIL_ATTEMPTS = 15      # Email fetch retries
SMS_RESEND_COUNT = 4         # SMS resend count
```

## Output

Account details saved to `wolt_accounts.txt`:
```
Email: example@priyomail.top | Password: abc123 | Name: Firstname Lastname | Phone: +380501234567 | Time: 45.2s
```

## Error Handling

- ✅ Timeouts handled gracefully
- ✅ Failed accounts logged but don't stop script
- ✅ Progress counter shows success/fail stats
- ✅ Auto-retries for email fetching (15 attempts)
- ✅ Browser closes even on errors
- ✅ Cookie consent auto-handled
- ✅ Smart modal/iframe detection

## Notes

- Uses visible browsers for monitoring (set `headless=True` for background)
- Average time: 45-60 seconds per account
- API keys rotated automatically
- Phone numbers must be 9 digits (no +380 prefix)
