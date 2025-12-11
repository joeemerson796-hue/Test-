# Oracle Account Creation Telegram Bot

A Telegram bot that helps users create Oracle Cloud accounts using Hotmail accounts. The bot provides Hotmail accounts, checks for Oracle verification emails, and automatically opens verification links.

## Features

- 🤖 **Telegram Integration** - Easy to use via Telegram commands
- 📧 **Account Assignment** - Each user gets their own Hotmail accounts
- ✅ **Auto Verification** - Bot checks email and opens verification links automatically
- 💾 **Progress Tracking** - Saves verified accounts to `created.txt`
- 👥 **Multi-User Support** - Multiple users can work simultaneously
- 🔄 **Account Management** - View, release, and track account status

## How It Works

### User Workflow:

1. **Get Account**: User sends `/get` → Bot assigns a Hotmail account
2. **Manual Signup**: User manually signs up for Oracle using the Hotmail email
3. **Verify**: User sends `/check YourPassword` → Bot:
   - Checks Hotmail inbox for Oracle verification email
   - Extracts verification link
   - Opens link in browser using Playwright
   - Saves to `created.txt`
   - Gives user the next account

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Configuration

### 1. Set Telegram Bot Token

Edit `oracle_bot.py` and set your bot token:
```python
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"
```

To get a bot token:
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token provided

### 2. Prepare `accounts.txt`

Add Hotmail accounts in one of these formats:

**OAuth2 Format (Recommended):**
```
email@hotmail.com:password:refresh_token:client_id
```

**Basic Auth Format:**
```
email@hotmail.com:password
```

## Usage

### Starting the Bot

```bash
python oracle_bot.py
```

The bot will start and wait for Telegram commands.

### Telegram Commands

#### `/start` or `/help`
Shows welcome message and command list

#### `/get`
Assigns a Hotmail account to you for Oracle signup

**Example Response:**
```
✅ Hotmail Account Assigned

📧 Email: example@hotmail.com
🔑 Password: yourpassword

Next Steps:
1. Go to Oracle signup
2. Use the email above
3. Complete signup manually
4. Use: /check YourOraclePassword
```

#### `/check <oracle_password>`
Checks for Oracle verification email and verifies the account

**Example:**
```
/check MyPassword123!
```

**What happens:**
1. Bot connects to Hotmail via IMAP
2. Searches for email from `oracle-acct_ww@oracle.com`
3. Extracts verification link
4. Opens link in browser (Playwright)
5. Saves to `created.txt`
6. Prompts you to get next account

#### `/myaccounts`
Shows all your assigned accounts and their status

**Example Response:**
```
📋 Your Accounts (3):

1. ✅ example1@hotmail.com
   🔐 Oracle Password: Pass123
   Status: verified

2. ⏳ example2@hotmail.com
   Status: pending
```

#### `/release <email>`
Releases an account back to the pool

**Example:**
```
/release example@hotmail.com
```

#### `/status`
Shows system-wide statistics

**Example Response:**
```
📊 System Status

📦 Total Accounts: 50
✅ Assigned: 10
🆓 Available: 40
✔️ Verified: 5
👥 Active Users: 3

Your Stats:
Total: 2
Verified: 1
```

## Complete Workflow Example

```
User: /start
Bot: [Shows welcome and instructions]

User: /get
Bot:
✅ Hotmail Account Assigned
📧 Email: test123@hotmail.com
🔑 Password: pass456

[User goes to Oracle signup, uses test123@hotmail.com]
[User completes Oracle registration manually]

User: /check OraclePass123!
Bot: ⏳ Checking test123@hotmail.com for Oracle verification email...
Bot: ✅ Verification email found! Opening link...
Bot:
✅ Account Created Successfully!
📧 Email: test123@hotmail.com
🔐 Password: OraclePass123!
Saved to created.txt
Ready for next account? /get

User: /get
Bot: [Assigns next Hotmail account...]
```

## Output Files

### `created.txt`
Contains successfully verified Oracle accounts:
```
email@hotmail.com:OraclePassword1
email2@hotmail.com:OraclePassword2
```

### `assignments.json`
Tracks account assignments (auto-managed by bot):
```json
{
  "email@hotmail.com:pass:token:clientid": {
    "user_id": "123456789",
    "email": "email@hotmail.com",
    "assigned_at": "2025-12-11T10:30:00",
    "status": "verified",
    "oracle_password": "OraclePass123"
  }
}
```

## Troubleshooting

### No Verification Email Found

**Possible causes:**
- User hasn't completed Oracle signup yet
- Email went to spam folder
- Oracle didn't send email yet (wait a few minutes)

**Solution:**
Wait 1-2 minutes after completing Oracle signup, then try `/check` again

### IMAP Connection Failed

**Possible causes:**
- Invalid OAuth2 tokens
- IMAP not enabled in Hotmail account
- Incorrect password

**Solution:**
- Verify `accounts.txt` format is correct
- Check if IMAP is enabled in Hotmail settings
- Use OAuth2 format for better reliability

### Browser Opens But Verification Fails

**Possible causes:**
- Verification link expired
- Network issues
- Page didn't load completely

**Solution:**
- Manually check the verification link
- Try `/check` again
- Contact support if persistent

### Bot Not Responding

**Possible causes:**
- Bot not running
- Wrong bot token
- Network issues

**Solution:**
- Check if `oracle_bot.py` is running
- Verify `TELEGRAM_TOKEN` is correct
- Check internet connection

## Technical Details

### IMAP Connection
- Uses OAuth2 for Hotmail/Outlook accounts (recommended)
- Fallback to basic auth for accounts without OAuth2 tokens
- Searches for emails from `oracle-acct_ww@oracle.com`
- Extracts verification links using regex pattern

### Playwright Verification
- Launches Chromium browser (non-headless by default)
- Uses undetected-playwright for stealth
- Opens verification link
- Checks for success message
- Keeps browser open briefly for visual confirmation

### Thread Safety
- Uses locks for file operations
- Browser operations are thread-safe
- Supports multiple concurrent users

## Security Notes

- Keep your `TELEGRAM_TOKEN` private
- Store `accounts.txt` securely (contains passwords)
- `assignments.json` contains user data - protect it
- `created.txt` contains Oracle credentials - keep secure

## Advanced Configuration

### Change Browser Behavior

Edit in `oracle_bot.py`:
```python
browser = playwright.chromium.launch(
    headless=True,  # Set to True for background operation
    # ... other options
)
```

### Adjust Timeouts

```python
# IMAP timeout
mail = imaplib.IMAP4_SSL('outlook.office365.com', timeout=30)

# Page load timeout
page.goto(verify_url, wait_until="domcontentloaded", timeout=60000)
```

### Custom Verification URL Pattern

```python
url_pattern = r'https://profile\.oracle\.com/myprofile/account/verify\.jspx\?key=[A-F0-9]+'
```

## Support

For issues or questions:
1. Check this README
2. Review error messages in bot console
3. Check Telegram bot logs
4. Verify all configuration files

## License

This tool is for authorized use only. Ensure you comply with Oracle's terms of service and email provider policies.
