import base64
import imaplib
import requests
import email
import re
import os
import json
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ===== Telegram Bot Config =====
TELEGRAM_TOKEN = "8231519327:AAEIRu7Sm8C_lLGiFvP97DcAeXsMJaCjf04"

# ===== Global State Management =====
# Track which accounts are assigned to which users
assignments_lock = threading.Lock()
script_dir = os.path.dirname(os.path.abspath(__file__))
assignments_file = os.path.join(script_dir, "assignments.json")
last_processed_update_id = 0

# Track last account index for each user
user_account_index = defaultdict(int)

# Track active extraction sessions
active_extractions = {}

# Session to reuse connections
session = requests.Session()

# ========== Assignment Management ==========
def load_assignments():
    """Load account assignments from file"""
    try:
        if os.path.exists(assignments_file):
            with open(assignments_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_assignments(assignments):
    """Save account assignments to file"""
    try:
        with open(assignments_file, 'w', encoding='utf-8') as f:
            json.dump(assignments, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving assignments: {e}")
        return False

def get_user_assignments(chat_id):
    """Get all accounts assigned to a specific user"""
    assignments = load_assignments()
    user_accounts = []
    for account_line, data in assignments.items():
        if data['user_id'] == str(chat_id):
            user_accounts.append({
                'account': account_line,
                'email': data['email'],
                'assigned_at': data['assigned_at'],
                'last_otp': data.get('last_otp', 'N/A'),
                'last_otp_time': data.get('last_otp_time', 'N/A')
            })
    return user_accounts

def assign_account_to_user(chat_id, account_line, email):
    """Assign an account exclusively to a user"""
    with assignments_lock:
        assignments = load_assignments()
        assignments[account_line] = {
            'user_id': str(chat_id),
            'email': email,
            'assigned_at': datetime.now().isoformat(),
            'last_otp': None,
            'last_otp_time': None
        }
        return save_assignments(assignments)

def update_account_otp(account_line, otp):
    """Update the last OTP for an account"""
    with assignments_lock:
        assignments = load_assignments()
        if account_line in assignments:
            assignments[account_line]['last_otp'] = otp
            assignments[account_line]['last_otp_time'] = datetime.now().isoformat()
            save_assignments(assignments)

def release_account(chat_id, email):
    """Release an account back to the pool"""
    with assignments_lock:
        assignments = load_assignments()
        to_remove = None
        for account_line, data in assignments.items():
            if data['user_id'] == str(chat_id) and data['email'] == email:
                to_remove = account_line
                break
        if to_remove:
            del assignments[to_remove]
            save_assignments(assignments)
            return True
        return False

def is_account_assigned(account_line):
    """Check if an account is already assigned to someone"""
    assignments = load_assignments()
    return account_line in assignments

# ========== Account Reading ==========
def read_accounts(filename="accounts.txt"):
    """Read accounts from file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, filename)

    if not os.path.exists(full_path):
        return []

    accounts = []
    with open(full_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            parts = line.split(':')
            if len(parts) >= 4:
                accounts.append((parts[0], parts[1], ':'.join(parts[2:-1]), parts[-1], line))

    return accounts

def get_next_available_account(chat_id):
    """Get next available account for a user (not assigned to anyone)"""
    accounts = read_accounts()

    # Start from user's last index
    start_index = user_account_index[chat_id]

    for i in range(len(accounts)):
        index = (start_index + i) % len(accounts)
        account = accounts[index]

        if not is_account_assigned(account[4]):  # account[4] is the original line
            # Update user's index for next time
            user_account_index[chat_id] = (index + 1) % len(accounts)
            return account

    return None

# ========== OTP Extraction ==========
def get_access_token(client_id, refresh_token):
    """Get access token from Microsoft"""
    data = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    try:
        response = session.post('https://login.live.com/oauth20_token.srf', data=data, timeout=5)
        return response.json().get('access_token')
    except:
        return None

def generate_auth_string(user, token):
    """Generate IMAP auth string"""
    return f"user={user}\1auth=Bearer {token}\1\1"

def extract_mcafee_otp_from_last(email_address, access_token):
    """Extract OTP from last McAfee email"""
    try:
        mail = imaplib.IMAP4_SSL('outlook.office365.com', timeout=10)
        mail.authenticate('XOAUTH2', lambda x: generate_auth_string(email_address, access_token))
        mail.select("INBOX")

        status, messages = mail.search(
            None,
            'FROM "donotreply@authentication.mcafee.com"'
        )

        if status != 'OK' or not messages[0]:
            mail.logout()
            return None

        email_ids = messages[0].split()

        if email_ids:
            last_email_id = email_ids[-1]
            status, msg_data = mail.fetch(last_email_id, '(RFC822)')
            if status == 'OK':
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                if body:
                    match = re.search(r'\b(\d{6})\b', body)
                    if match:
                        mail.logout()
                        return match.group(1)

        mail.logout()
    except:
        return None
    return None

def extract_otp_for_account(account_data):
    """Extract OTP for a single account"""
    email_part, password, refresh_token, client_id, original_line = account_data

    access_token = get_access_token(client_id, refresh_token)
    if not access_token:
        return None

    otp = extract_mcafee_otp_from_last(email_part, access_token)
    return otp

# ========== Telegram Bot Functions ==========
def send_telegram_message(chat_id, text):
    """Send a message to a specific Telegram user"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_telegram_updates(offset=None):
    """Get updates from Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {"timeout": 30, "offset": offset}
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except Exception as e:
        print(f"Error getting updates: {e}")
        return None

# ========== Command Handlers ==========
def handle_start_command(chat_id):
    """Handle /start command"""
    message = """🤖 <b>McAfee OTP Bot</b>

/get - Get new account
/getcode - Extract McAfee code
/refresh - Refresh codes
/myaccounts - Your accounts
/release &lt;email&gt; - Release account
/status - System status

<b>Quick Start:</b>
1. /get → Get account
2. /getcode → Extract code

——————————
/get
/getcode"""
    send_telegram_message(chat_id, message)

def handle_get_command(chat_id):
    """Handle /get command - assign next account to user (no extraction)"""
    account = get_next_available_account(chat_id)

    if not account:
        send_telegram_message(chat_id, "❌ No available accounts\n\n——————————\n/get\n/getcode")
        return

    email_part, password, refresh_token, client_id, original_line = account

    # Assign account to user
    success = assign_account_to_user(chat_id, original_line, email_part)

    if not success:
        send_telegram_message(chat_id, "❌ Error saving assignment. Check bot permissions.\n\n——————————\n/get\n/getcode")
        return

    message = f"✅ Account assigned\n📧 <code>{email_part}</code>\n\nUse /getcode to extract OTP\n\n——————————\n/get\n/getcode"
    send_telegram_message(chat_id, message)

def handle_getcode_command(chat_id):
    """Handle /getcode command - extract McAfee OTP from user's accounts"""
    if chat_id in active_extractions:
        send_telegram_message(chat_id, "⏳ Processing...\n\n——————————\n/get\n/getcode")
        return

    active_extractions[chat_id] = True

    try:
        user_accounts = get_user_assignments(chat_id)

        if not user_accounts:
            send_telegram_message(chat_id, "❌ No accounts. Use /get first\n\n——————————\n/get\n/getcode")
            return

        send_telegram_message(chat_id, "⏳ Extracting codes...")

        accounts = read_accounts()
        results = []

        for user_acc in user_accounts:
            # Find full account data
            account_data = None
            for acc in accounts:
                if acc[4] == user_acc['account']:
                    account_data = acc
                    break

            if account_data:
                otp = extract_otp_for_account(account_data)
                if otp:
                    update_account_otp(user_acc['account'], otp)
                    results.append(f"✅ {account_data[0]}: <code>{otp}</code>")
                else:
                    results.append(f"⚠️ {account_data[0]}: No code")

        if results:
            message = "🔐 <b>McAfee Codes:</b>\n\n" + "\n".join(results) + "\n\n——————————\n/get\n/getcode"
            send_telegram_message(chat_id, message)
        else:
            send_telegram_message(chat_id, "❌ No codes found\n\n——————————\n/get\n/getcode")

    finally:
        if chat_id in active_extractions:
            del active_extractions[chat_id]

def handle_refresh_command(chat_id):
    """Handle /refresh command - re-extract McAfee codes"""
    # Same as getcode, just different naming
    handle_getcode_command(chat_id)

def handle_myaccounts_command(chat_id):
    """Handle /myaccounts command"""
    user_accounts = get_user_assignments(chat_id)

    if not user_accounts:
        send_telegram_message(chat_id, "❌ No accounts\n\n——————————\n/get\n/getcode")
        return

    message = f"📋 <b>Your Accounts ({len(user_accounts)}):</b>\n\n"

    for i, acc in enumerate(user_accounts, 1):
        message += f"{i}. <code>{acc['email']}</code>\n"
        message += f"   🔐 <code>{acc['last_otp'] or 'N/A'}</code>\n\n"

    message += "——————————\n/get\n/getcode"

    send_telegram_message(chat_id, message)

def handle_release_command(chat_id, email):
    """Handle /release command"""
    if not email:
        send_telegram_message(chat_id, "❌ Specify email\n\nExample: /release email@hotmail.com\n\n——————————\n/get\n/getcode")
        return

    if release_account(chat_id, email):
        send_telegram_message(chat_id, f"✅ Released <code>{email}</code>\n\n——————————\n/get\n/getcode")
    else:
        send_telegram_message(chat_id, f"❌ <code>{email}</code> not found\n\n——————————\n/get\n/getcode")

def handle_status_command(chat_id):
    """Handle /status command"""
    accounts = read_accounts()
    assignments = load_assignments()

    total_accounts = len(accounts)
    assigned_accounts = len(assignments)
    available_accounts = total_accounts - assigned_accounts

    # Count unique users
    unique_users = len(set(data['user_id'] for data in assignments.values()))

    message = f"📊 <b>Status</b>\n\n"
    message += f"📦 Total: {total_accounts}\n"
    message += f"✅ Assigned: {assigned_accounts}\n"
    message += f"🆓 Available: {available_accounts}\n"
    message += f"👥 Users: {unique_users}\n\n"

    # Show user's personal stats
    user_accounts = get_user_assignments(chat_id)
    message += f"<b>Your Accounts:</b> {len(user_accounts)}\n\n"
    message += "——————————\n/get\n/getcode"

    send_telegram_message(chat_id, message)

def handle_message(chat_id, text):
    """Handle incoming message"""
    text = text.strip()

    if text == "/start" or text == "/help":
        handle_start_command(chat_id)
    elif text == "/get":
        handle_get_command(chat_id)
    elif text == "/getcode":
        handle_getcode_command(chat_id)
    elif text == "/refresh":
        handle_refresh_command(chat_id)
    elif text == "/myaccounts":
        handle_myaccounts_command(chat_id)
    elif text.startswith("/release"):
        parts = text.split(maxsplit=1)
        email = parts[1] if len(parts) > 1 else None
        handle_release_command(chat_id, email)
    elif text == "/status":
        handle_status_command(chat_id)
    else:
        send_telegram_message(chat_id, "❌ Unknown command. Use /help\n\n——————————\n/get\n/getcode")

# ========== Main Bot Loop ==========
def main():
    global last_processed_update_id

    print("🤖 McAfee OTP Bot Started!")
    print("=" * 50)
    print("Bot is running and waiting for commands...")
    print("Send /start to your bot to begin!")
    print("=" * 50)

    offset = None

    while True:
        try:
            updates = get_telegram_updates(offset)

            if updates and updates.get('ok'):
                for update in updates.get('result', []):
                    update_id = update.get('update_id')

                    if offset is None or update_id >= offset:
                        offset = update_id + 1

                    message = update.get('message')
                    if message:
                        chat_id = message.get('chat', {}).get('id')
                        text = message.get('text', '')

                        if chat_id and text:
                            print(f"📨 Received from {chat_id}: {text}")

                            # Handle command in separate thread to not block
                            threading.Thread(target=handle_message, args=(chat_id, text)).start()

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n👋 Bot stopped by user")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"Fatal error: {e}")
        input("Press Enter to exit...")
