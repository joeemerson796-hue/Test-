# Amazon OTP Multi-User Bot

## Overview

This bot allows multiple users to simultaneously extract Amazon OTPs from their Outlook accounts via Telegram. Each user gets **exclusive access** to their assigned accounts - no conflicts, no duplicates!

## Key Features

✅ **Exclusive Account Assignment** - Once you get an account, it's yours until you release it
✅ **No Conflicts** - Multiple users can use the bot at the same time
✅ **Persistent Tracking** - Your accounts stay assigned even if bot restarts
✅ **Easy OTP Refresh** - Get new OTPs from your assigned accounts anytime
✅ **User-Friendly Commands** - Simple Telegram commands for everything

## Files

- `amazon_otp_bot.py` - Main bot script (NEW - multi-user version)
- `accounts.txt` - Your email accounts (same format as before)
- `assignments.json` - Tracks which accounts belong to which users (auto-created)

## Setup

### 1. Install Requirements

```bash
pip install requests imaplib-oauth2
```

### 2. Prepare accounts.txt

Same format as before:
```
email@hotmail.com:password:refresh_token:client_id
another@outlook.com:password:refresh_token:client_id
```

### 3. Run the Bot

```bash
python amazon_otp_bot.py
```

The bot will start and wait for commands from Telegram.

## Bot Commands

### For Users:

| Command | Description | Example |
|---------|-------------|---------|
| `/start` or `/help` | Show welcome message and commands | `/start` |
| `/get` | Get next available account with OTP | `/get` |
| `/refresh` | Refresh OTPs for your assigned accounts | `/refresh` |
| `/myaccounts` | Show all your assigned accounts | `/myaccounts` |
| `/release <email>` | Release an account back to pool | `/release test@hotmail.com` |
| `/status` | Show overall system statistics | `/status` |

## How It Works

### 1. Getting Your First Account

```
You: /get
Bot: 🔍 Finding next available account...
Bot: ✅ Account assigned to you: example@hotmail.com
     ⏳ Extracting OTP...
Bot: ✅ OTP Extracted Successfully!
     📧 Email: example@hotmail.com
     🔐 OTP: 123456
     This account is now exclusively yours!
```

### 2. The Account is Now YOURS

- ✅ No one else can get this account
- ✅ It stays assigned to you even if bot restarts
- ✅ You can refresh OTP anytime
- ✅ Only you can release it back

### 3. Getting More Accounts

```
You: /get
Bot: ✅ Account assigned to you: another@hotmail.com
     🔐 OTP: 789012
```

Each time you use `/get`, you get the **next available account** in sequence.

### 4. Refreshing OTPs

```
You: /refresh
Bot: 🔄 Refreshing OTPs for 2 account(s)...
Bot: 🔄 Refresh Results:
     ✅ example@hotmail.com: 456789
     ✅ another@hotmail.com: 987654
```

### 5. Checking Your Accounts

```
You: /myaccounts
Bot: 📋 Your Assigned Accounts (2):

     1. example@hotmail.com
        🔐 Last OTP: 456789
        📅 Assigned: 2025-11-11 10:30:45

     2. another@hotmail.com
        🔐 Last OTP: 987654
        📅 Assigned: 2025-11-11 10:35:20
```

### 6. Releasing an Account

```
You: /release example@hotmail.com
Bot: ✅ Account example@hotmail.com has been released back to the pool!
```

Now others can get this account.

## Multi-User Example

### User A (Chat ID: 111):
```
User A: /get
Bot → User A: ✅ account1@hotmail.com (OTP: 123456)

User A: /get
Bot → User A: ✅ account2@hotmail.com (OTP: 789012)
```

### User B (Chat ID: 222) - At the Same Time:
```
User B: /get
Bot → User B: ✅ account3@hotmail.com (OTP: 456789)

User B: /get
Bot → User B: ✅ account4@hotmail.com (OTP: 321654)
```

**Result:**
- User A has: account1, account2
- User B has: account3, account4
- **NO CONFLICTS!** Each user gets different accounts
- Each user gets the next account in sequence from where they left off

## Key Differences from Old Script

### Old Script (Original):
- ❌ Manual batch processing
- ❌ No user tracking
- ❌ Can't handle multiple users
- ❌ Need to manually manage accounts
- ❌ Interactive console (not automated)

### New Bot (amazon_otp_bot.py):
- ✅ Automatic via Telegram commands
- ✅ Tracks which accounts belong to which user
- ✅ Multiple users can use simultaneously
- ✅ Accounts stay assigned automatically
- ✅ Fully automated, runs 24/7

## Assignment System

The bot uses `assignments.json` to track everything:

```json
{
  "email@hotmail.com:password:token:id": {
    "user_id": "7312871544",
    "email": "email@hotmail.com",
    "assigned_at": "2025-11-11T10:30:45.123456",
    "last_otp": "123456",
    "last_otp_time": "2025-11-11T10:30:50.789012"
  }
}
```

## Important Notes

1. **Exclusive Access**: Once assigned, an account is locked to that user
2. **Persistent**: Assignments survive bot restarts
3. **Sequential**: Each user gets accounts in order, no skipping
4. **Safe**: Thread-safe locking prevents race conditions
5. **24/7**: Bot runs continuously, handles commands as they come

## Troubleshooting

### Bot not responding?
- Check if bot is running: `python amazon_otp_bot.py`
- Check bot token is correct
- Make sure you sent `/start` first

### No available accounts?
- Use `/status` to check how many accounts are free
- Use `/release <email>` to free up accounts
- Add more accounts to `accounts.txt`

### OTP not found?
- The email might not have received Amazon OTP yet
- Try `/refresh` after a few minutes
- Check if the account credentials are correct

## Security Notes

⚠️ **IMPORTANT**:
- Keep `accounts.txt` secure (contains passwords and tokens)
- Keep `assignments.json` secure (contains user mappings)
- Keep your Telegram bot token private
- Don't share your bot with untrusted users

## Support

If you need help:
1. Use `/help` in the bot to see commands
2. Use `/status` to check system state
3. Use `/myaccounts` to see your assignments

---

**Enjoy your multi-user OTP extraction bot! 🎉**
