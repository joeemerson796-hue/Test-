# Wolt Account Creator - Robust Queue Edition

Ultra-robust automated script to create Wolt accounts using Priyo temp mail API and Playwright with queue-based worker system.

## Features

- ⚡ **Lightning fast** - optimized sleep times and lightweight code
- 💪 **100% Robust** - NEVER stops until all numbers processed
- 🔄 **Queue-based workers** - all workers share one phone queue
- 🚫 **Phone-in-use detection** - auto-skips used numbers
- 📞 **Smart retry** - continues with next number on any error
- 🛡️ **Comprehensive error handling** - catches everything
- 💬 **Interactive worker selection** - prompts you at runtime
- 🍪 **Auto-handles cookies** - waits and declines consent modal
- 🔧 **Smart iframe detection** - works with modals or iframes
- ⌨️ **Keyboard country selection** - fast and reliable
- 🚫 **Rate limit detection** - auto-skips to next account
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

## How It Works (Queue-Based System)

**Workers operate on a shared queue:**
- All workers pull phone numbers from one shared queue
- If a number fails, worker immediately tries next number
- Workers keep running until queue is empty
- No number is wasted or skipped!

**For each phone number:**
1. Gets random email from Priyo Email API
2. Opens Wolt.com and clicks "Sign up"
3. Enters email and waits for verification email
4. Fetches verification link from email API (auto-retries)
5. Opens verification link and completes registration:
   - Country: Hungary
   - Random first name (9 chars)
   - Random last name (10 chars)
   - Phone country: Ukraine (+380)
   - Phone number from queue
6. **If "phone already in use" error:**
   - Clicks back button
   - Closes browser
   - Gets next number from queue and retries
7. Sends SMS verification code
8. Resends SMS 4 times (stops if rate limited)
9. Saves account to `wolt_accounts.txt`
10. Gets next number from queue and repeats

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

## Error Handling (100% Robust)

- ✅ **Queue system** - workers never stop until queue is empty
- ✅ **Phone already in use** - auto-detected, clicks back, tries next number
- ✅ **Rate limit detection** - skips to next account automatically
- ✅ **Email fetch failures** - skips number and tries next
- ✅ **Browser crashes** - browser always closes, next number processed
- ✅ **Timeouts handled** - continues with next number
- ✅ **All errors caught** - comprehensive try/except blocks everywhere
- ✅ **Progress tracking** - shows success/fail stats per worker
- ✅ **Cookie consent** - auto-handled
- ✅ **Smart modal/iframe detection** - works with any layout
- ✅ **Playwright instance cleanup** - no memory leaks

**Script GUARANTEES:**
- Never crashes completely
- Processes every number in numbers.txt
- Shows final stats at the end
- Workers keep going until queue is empty

## Notes

- Uses visible browsers for monitoring (set `headless=True` for background)
- Average time: **30-40 seconds per account** (optimized!)
- API keys rotated automatically
- Phone numbers must be 9 digits (no +380 prefix)
- Rate limit error auto-detected and handled
