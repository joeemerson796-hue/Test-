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
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync

# ===== Telegram Bot Config =====
TELEGRAM_TOKEN = "8231519327:AAEIRu7Sm8C_lLGiFvP97DcAeXsMJaCjf04"
ORACLE_PASSWORD = "Gouda@123@gg"
ORACLE_SIGNUP_URL = "https://profile.oracle.com/myprofile/account/create-account.jspx"

# ===== Global State Management =====
# Track which accounts are assigned to which users
assignments_lock = threading.Lock()
script_dir = os.path.dirname(os.path.abspath(__file__))
assignments_file = os.path.join(script_dir, "assignments.json")
last_processed_update_id = 0

# Track last account index for each user
user_account_index = defaultdict(int)

# Track current/active account for each user
user_current_account = {}

# Track active operations
active_operations = {}

# Session to reuse connections
session = requests.Session()

# Browser lock for thread-safe Playwright operations
browser_lock = threading.Lock()

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
                'status': data.get('status', 'pending'),
                'oracle_password': data.get('oracle_password', 'N/A')
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
            'status': 'pending',
            'oracle_password': None
        }
        return save_assignments(assignments)

def update_account_status(account_line, status, oracle_password=None):
    """Update the status of an account"""
    with assignments_lock:
        assignments = load_assignments()
        if account_line in assignments:
            assignments[account_line]['status'] = status
            if oracle_password:
                assignments[account_line]['oracle_password'] = oracle_password
            assignments[account_line]['updated_at'] = datetime.now().isoformat()
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

def save_created_account(email, oracle_password):
    """Save successfully created Oracle account to file"""
    try:
        with open(os.path.join(script_dir, "created.txt"), "a", encoding="utf-8") as f:
            f.write(f"{email}:{oracle_password}\n")
        return True
    except Exception as e:
        print(f"Error saving created account: {e}")
        return False

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
            if not line or line.startswith('#'):
                continue

            parts = line.split(':')
            if len(parts) >= 4:
                accounts.append((parts[0], parts[1], ':'.join(parts[2:-1]), parts[-1], line))
            elif len(parts) >= 2:
                accounts.append((parts[0], parts[1], None, None, line))

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

# ========== OAuth2 & IMAP Functions ==========
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

def connect_to_imap(email_address, password, access_token=None):
    """Connect to Hotmail/Outlook IMAP with OAuth2 or basic auth"""
    try:
        mail = imaplib.IMAP4_SSL('outlook.office365.com', timeout=15)

        if access_token:
            # OAuth2 authentication
            mail.authenticate('XOAUTH2', lambda x: generate_auth_string(email_address, access_token))
        else:
            # Basic authentication
            mail.login(email_address, password)

        return mail
    except Exception as e:
        print(f"Failed to connect to IMAP for {email_address}: {e}")
        return None

def check_for_oracle_verification_email(email_address, password, access_token):
    """Check for Oracle verification email and extract verification link"""
    try:
        mail = connect_to_imap(email_address, password, access_token)
        if not mail:
            return None

        mail.select("INBOX")

        # Search for Oracle emails
        status, messages = mail.search(None, 'FROM "oracle-acct_ww@oracle.com"')

        if status != 'OK' or not messages[0]:
            mail.logout()
            return None

        email_ids = messages[0].split()

        # Get the last (most recent) Oracle email
        if email_ids:
            last_email_id = email_ids[-1]
            status, msg_data = mail.fetch(last_email_id, '(RFC822)')

            if status == 'OK':
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain" or content_type == "text/html":
                            try:
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                if body:
                                    break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    except:
                        pass

                # Search for verification URL in the email body
                if body:
                    url_pattern = r'https://profile\.oracle\.com/myprofile/account/verify\.jspx\?key=[A-F0-9]+'
                    match = re.search(url_pattern, body)

                    if match:
                        verify_url = match.group(0)
                        mail.logout()
                        return verify_url

        mail.logout()
        return None

    except Exception as e:
        print(f"Error checking email for {email_address}: {e}")
        return None

def verify_oracle_email(verify_url):
    """Open verification URL using Playwright"""
    try:
        with browser_lock:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                stealth_sync(context)
                page = context.new_page()

                print(f"Opening verification URL: {verify_url}")
                page.goto(verify_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                page_content = page.content()

                # Check for success
                success = False
                if 'Success. Your account is ready to use.' in page_content or 'x289' in page_content:
                    success = True
                    print("✅ Email verified successfully!")
                else:
                    print("⚠️ Verification page opened, but success not confirmed")

                # Keep browser open for a few seconds
                time.sleep(2)

                browser.close()
                return success

    except Exception as e:
        print(f"Error during verification: {e}")
        return False

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
    message = """🤖 <b>Oracle Account Creation Bot</b>

<b>How it works:</b>
1. /get → Get account details (all copyable!)
2. Sign up Oracle manually
3. /check → Bot verifies automatically
4. Account saved to created.txt
5. Repeat!

<b>Commands:</b>
/get - Get account
/check - Verify account
/myaccounts - Your accounts
/status - System status

——————————
/get"""
    send_telegram_message(chat_id, message)

def handle_get_command(chat_id):
    """Handle /get command - assign next Hotmail account to user"""
    account = get_next_available_account(chat_id)

    if not account:
        send_telegram_message(chat_id, "❌ No available accounts\n\n——————————\n/get\n/check")
        return

    email_part, password, refresh_token, client_id, original_line = account

    # Assign account to user
    success = assign_account_to_user(chat_id, original_line, email_part)

    if not success:
        send_telegram_message(chat_id, "❌ Error saving assignment\n\n——————————\n/get\n/check")
        return

    # Set this as the current account for the user
    user_current_account[chat_id] = account

    message = f"""✅ <b>Account Ready - Click to Copy!</b>

🔗 <b>Registration Link:</b>
{ORACLE_SIGNUP_URL}

📧 <b>Hotmail Email:</b>
<code>{email_part}</code>

🔑 <b>Hotmail Password:</b>
<code>{password}</code>

🔐 <b>Oracle Password:</b>
<code>{ORACLE_PASSWORD}</code>

<b>Steps:</b>
1. Click link above
2. Copy & paste each field (click to copy)
3. Complete signup
4. Use /check when done

——————————
/check"""

    send_telegram_message(chat_id, message)

def handle_check_command(chat_id):
    """Handle /check command - verify Oracle account"""
    if chat_id in active_operations:
        send_telegram_message(chat_id, "⏳ Processing previous request...\n\n——————————\n/get\n/check")
        return

    # Check if user has a current account
    if chat_id not in user_current_account:
        send_telegram_message(chat_id, "❌ No account assigned. Use /get first\n\n——————————\n/get\n/check")
        return

    active_operations[chat_id] = True

    try:
        account_data = user_current_account[chat_id]
        email_part, password, refresh_token, client_id, original_line = account_data

        send_telegram_message(chat_id, f"⏳ Checking {email_part} for Oracle verification email...")

        # Get access token if using OAuth2
        access_token = None
        if refresh_token and client_id:
            access_token = get_access_token(client_id, refresh_token)

        # Check for verification email
        verify_url = check_for_oracle_verification_email(email_part, password, access_token)

        if not verify_url:
            send_telegram_message(chat_id, f"❌ No Oracle verification email found for {email_part}\n\nMake sure you completed the Oracle signup!\n\n——————————\n/get\n/check")
            return

        send_telegram_message(chat_id, "✅ Verification email found! Opening link...")

        # Verify email using Playwright
        success = verify_oracle_email(verify_url)

        if success:
            # Save to created.txt
            save_created_account(email_part, ORACLE_PASSWORD)

            # Update status
            update_account_status(original_line, 'verified', ORACLE_PASSWORD)

            message = f"""✅ <b>Account Created Successfully!</b>

📧 <b>Email:</b> <code>{email_part}</code>
🔐 <b>Password:</b> <code>{ORACLE_PASSWORD}</code>

Saved to created.txt

——————————
Ready for next account? /get"""

            send_telegram_message(chat_id, message)

            # Clear current account so user can get next one
            if chat_id in user_current_account:
                del user_current_account[chat_id]

        else:
            send_telegram_message(chat_id, f"⚠️ Verification link opened but success not confirmed\n\nPlease check manually: {verify_url}\n\n——————————\n/get\n/check")

    except Exception as e:
        print(f"Error in check command: {e}")
        send_telegram_message(chat_id, f"❌ Error: {str(e)}\n\n——————————\n/get\n/check")
    finally:
        if chat_id in active_operations:
            del active_operations[chat_id]

def handle_myaccounts_command(chat_id):
    """Handle /myaccounts command"""
    user_accounts = get_user_assignments(chat_id)

    if not user_accounts:
        send_telegram_message(chat_id, "❌ No accounts assigned\n\n——————————\n/get\n/check")
        return

    message = f"📋 <b>Your Accounts ({len(user_accounts)}):</b>\n\n"

    for i, acc in enumerate(user_accounts, 1):
        status_emoji = "✅" if acc['status'] == 'verified' else "⏳"
        message += f"{i}. {status_emoji} <code>{acc['email']}</code>\n"
        if acc['status'] == 'verified':
            message += f"   🔐 Oracle Password: <code>{ORACLE_PASSWORD}</code>\n"
        message += f"   Status: {acc['status']}\n\n"

    message += "——————————\n/get\n/check"

    send_telegram_message(chat_id, message)

def handle_release_command(chat_id, email):
    """Handle /release command"""
    if not email:
        send_telegram_message(chat_id, "❌ Specify email\n\nExample: /release email@hotmail.com\n\n——————————\n/get\n/check")
        return

    if release_account(chat_id, email):
        # Also clear from current account if it's the active one
        if chat_id in user_current_account:
            if user_current_account[chat_id][0] == email:
                del user_current_account[chat_id]

        send_telegram_message(chat_id, f"✅ Released <code>{email}</code>\n\n——————————\n/get\n/check")
    else:
        send_telegram_message(chat_id, f"❌ <code>{email}</code> not found in your accounts\n\n——————————\n/get\n/check")

def handle_status_command(chat_id):
    """Handle /status command"""
    accounts = read_accounts()
    assignments = load_assignments()

    total_accounts = len(accounts)
    assigned_accounts = len(assignments)
    available_accounts = total_accounts - assigned_accounts

    # Count verified accounts
    verified_count = sum(1 for data in assignments.values() if data.get('status') == 'verified')

    # Count unique users
    unique_users = len(set(data['user_id'] for data in assignments.values()))

    message = f"📊 <b>System Status</b>\n\n"
    message += f"📦 Total Accounts: {total_accounts}\n"
    message += f"✅ Assigned: {assigned_accounts}\n"
    message += f"🆓 Available: {available_accounts}\n"
    message += f"✔️ Verified: {verified_count}\n"
    message += f"👥 Active Users: {unique_users}\n\n"

    # Show user's personal stats
    user_accounts = get_user_assignments(chat_id)
    user_verified = sum(1 for acc in user_accounts if acc['status'] == 'verified')

    message += f"<b>Your Stats:</b>\n"
    message += f"Total: {len(user_accounts)}\n"
    message += f"Verified: {user_verified}\n\n"
    message += "——————————\n/get\n/check"

    send_telegram_message(chat_id, message)

def handle_message(chat_id, text):
    """Handle incoming message"""
    text = text.strip()

    if text == "/start" or text == "/help":
        handle_start_command(chat_id)
    elif text == "/get":
        handle_get_command(chat_id)
    elif text == "/check":
        handle_check_command(chat_id)
    elif text == "/myaccounts":
        handle_myaccounts_command(chat_id)
    elif text.startswith("/release"):
        parts = text.split(maxsplit=1)
        email = parts[1] if len(parts) > 1 else None
        handle_release_command(chat_id, email)
    elif text == "/status":
        handle_status_command(chat_id)
    else:
        send_telegram_message(chat_id, "❌ Unknown command. Use /help\n\n——————————\n/get\n/check")

# ========== Main Bot Loop ==========
def main():
    global last_processed_update_id

    print("🤖 Oracle Account Creation Bot Started!")
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
                            threading.Thread(target=handle_message, args=(chat_id, text), daemon=True).start()

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
