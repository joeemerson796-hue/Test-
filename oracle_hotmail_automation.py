import os
import time
import random
import string
import re
import imaplib
import email
import requests
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
from loguru import logger
from threading import Lock
from tqdm import tqdm

# Global lock for thread-safe file operations
file_lock = Lock()
country_name = ""
country_code = ""

# Global session for OAuth2 requests
session = requests.Session()


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def generate_random_string(length=8):
    """Generate random alphabetical string"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def generate_random_numbers(length=8):
    """Generate random numerical string"""
    return ''.join(random.choices(string.digits, k=length))


def get_access_token(client_id, refresh_token):
    """Get OAuth2 access token for Hotmail/Outlook"""
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
    """Generate IMAP XOAUTH2 auth string"""
    return f"user={user}\1auth=Bearer {token}\1\1"


def connect_to_imap(email_address, password, access_token=None):
    """Connect to Hotmail/Outlook IMAP with OAuth2 or basic auth"""
    try:
        mail = imaplib.IMAP4_SSL('outlook.office365.com', timeout=15)

        if access_token:
            # OAuth2 authentication
            mail.authenticate('XOAUTH2', lambda x: generate_auth_string(email_address, access_token))
        else:
            # Basic authentication (may not work for some accounts)
            mail.login(email_address, password)

        return mail
    except Exception as e:
        logger.error(f"Failed to connect to IMAP: {e}")
        return None


def wait_for_oracle_verification_email_imap(email_address, password, access_token, runner_id):
    """Wait for and extract Oracle verification link from Hotmail inbox via IMAP"""
    logger.info(f"{runner_id}: Waiting for Oracle verification email in {email_address}...")

    max_wait = 120
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            # Connect to IMAP
            mail = connect_to_imap(email_address, password, access_token)
            if not mail:
                logger.error(f"{runner_id}: Failed to connect to IMAP")
                time.sleep(5)
                continue

            mail.select("INBOX")

            # Search for Oracle emails
            status, messages = mail.search(None, 'FROM "oracle-acct_ww@oracle.com"')

            if status != 'OK' or not messages[0]:
                logger.debug(f"{runner_id}: No Oracle emails found yet, waiting...")
                mail.logout()
                time.sleep(5)
                continue

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
                            logger.success(f"{runner_id}: Found verification URL in email!")
                            mail.logout()
                            return verify_url
                        else:
                            logger.debug(f"{runner_id}: Oracle email found but no verification link yet")

            mail.logout()
            time.sleep(5)

        except Exception as e:
            logger.debug(f"{runner_id}: Error checking email: {e}")
            time.sleep(5)

    logger.error(f"{runner_id}: Verification email not received within timeout")
    return None


def verify_email(verify_url, page, runner_id):
    """Open verification URL"""
    try:
        logger.info(f"{runner_id}: Opening verification URL...")
        verify_page = page.context.new_page()
        verify_page.goto(verify_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        page_content = verify_page.content()

        if 'Success. Your account is ready to use.' in page_content or 'x289' in page_content:
            logger.success(f"{runner_id}: Email verified successfully!")
        else:
            logger.info(f"{runner_id}: Verification page opened")

        verify_page.close()
        return True

    except Exception as e:
        logger.error(f"{runner_id}: Error during verification: {e}")
        return False


def create_oracle_account(page, email, password, runner_id):
    """Create Oracle account"""
    logger.info(f"{runner_id}: Creating Oracle account...")

    oracle_page = page.context.new_page()

    logger.info(f"{runner_id}: Loading Oracle registration page...")
    oracle_page.goto("https://profile.oracle.com/myprofile/account/create-account.jspx",
                     wait_until="domcontentloaded", timeout=20000)

    # Wait for form
    country_select = oracle_page.locator('select#sView1\\:r1\\:0\\:country\\:\\:content')
    country_select.wait_for(state="visible", timeout=10000)

    # Select country
    logger.info(f"{runner_id}: Selecting country ({country_name})...")
    time.sleep(0.3)

    box = country_select.bounding_box()
    if box:
        x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
        y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
        oracle_page.mouse.move(x, y)
        time.sleep(0.2)

    country_select.click()
    time.sleep(0.3)

    # Select country option
    oracle_page.locator(f'select#sView1\\:r1\\:0\\:country\\:\\:content').select_option(label=country_name)
    time.sleep(0.3)

    # Fill email
    logger.info(f"{runner_id}: Filling form with email: {email}")
    email_input = oracle_page.locator('input#sView1\\:r1\\:0\\:email\\:\\:content')
    email_input.wait_for(state="visible", timeout=10000)
    email_input.fill(email)
    time.sleep(0.2)

    # Fill password
    password_input = oracle_page.locator('input#sView1\\:r1\\:0\\:password\\:\\:content')
    password_input.fill(password)
    time.sleep(0.2)

    # Retype password
    retype_password_input = oracle_page.locator('input#sView1\\:r1\\:0\\:retypePassword\\:\\:content')
    retype_password_input.fill(password)
    time.sleep(0.2)

    # Fill personal details
    first_name = generate_random_string(8)
    last_name = generate_random_string(8)
    job_title = generate_random_string(8)
    work_phone = generate_random_numbers(8)
    company_name = generate_random_string(8)
    address = generate_random_string(8)
    city = generate_random_string(8)
    postal_code = generate_random_numbers(8)

    logger.info(f"{runner_id}: Filling personal details...")

    oracle_page.locator('input#sView1\\:r1\\:0\\:firstName\\:\\:content').fill(first_name)
    oracle_page.locator('input#sView1\\:r1\\:0\\:lastName\\:\\:content').fill(last_name)
    oracle_page.locator('input#sView1\\:r1\\:0\\:jobTitle\\:\\:content').fill(job_title)
    oracle_page.locator('input#sView1\\:r1\\:0\\:workPhone\\:\\:content').fill(work_phone)
    oracle_page.locator('input#sView1\\:r1\\:0\\:companyName\\:\\:content').fill(company_name)
    oracle_page.locator('input#sView1\\:r1\\:0\\:address1\\:\\:content').fill(address)
    oracle_page.locator('input#sView1\\:r1\\:0\\:city\\:\\:content').fill(city)
    oracle_page.locator('input#sView1\\:r1\\:0\\:postalCode\\:\\:content').fill(postal_code)

    time.sleep(0.5)

    # Click Create Account
    logger.info(f"{runner_id}: Clicking Create Account button...")
    create_button = oracle_page.locator('div#sView1\\:r1\\:0\\:b1 a')
    create_button.scroll_into_view_if_needed()
    time.sleep(0.3)
    create_button.wait_for(state="visible", timeout=10000)
    create_button.click()

    logger.info(f"{runner_id}: Account creation submitted...")
    time.sleep(2)

    return oracle_page


def read_hotmail_accounts(filename="accounts.txt"):
    """Read Hotmail accounts from file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, filename)

    if not os.path.exists(full_path):
        logger.error(f"accounts.txt not found in script directory: {script_dir}")
        return []

    accounts = []
    with open(full_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            parts = line.split(':')
            if len(parts) >= 4:
                # Format: email:password:refresh_token:client_id
                accounts.append({
                    'email': parts[0],
                    'password': parts[1],
                    'refresh_token': ':'.join(parts[2:-1]),
                    'client_id': parts[-1],
                    'use_oauth': True,
                    'original_line': line
                })
            elif len(parts) >= 2:
                # Format: email:password (basic auth)
                accounts.append({
                    'email': parts[0],
                    'password': parts[1],
                    'refresh_token': None,
                    'client_id': None,
                    'use_oauth': False,
                    'original_line': line
                })

    return accounts


def create_account_worker(index, hotmail_account, oracle_password, progress_bar):
    """Worker to create a single Oracle account using Hotmail"""
    runner_id = f"Worker-{index + 1}"

    hotmail_email = hotmail_account['email']
    hotmail_password = hotmail_account['password']
    refresh_token = hotmail_account['refresh_token']
    client_id = hotmail_account['client_id']
    use_oauth = hotmail_account['use_oauth']

    logger.info(f"{runner_id}: Starting account creation with Hotmail: {hotmail_email}")

    # Get access token if using OAuth2
    access_token = None
    if use_oauth:
        logger.info(f"{runner_id}: Getting OAuth2 access token...")
        access_token = get_access_token(client_id, refresh_token)
        if not access_token:
            logger.error(f"{runner_id}: Failed to get access token")
            savecreated('oracle_failed', f"{hotmail_email}:{oracle_password} - Failed to get access token")
            if progress_bar:
                progress_bar.update(1)
            return False

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                color_scheme='light'
            )
            stealth_sync(context)
            page = context.new_page()

            # Create Oracle account with Hotmail email
            oracle_page = create_oracle_account(page, hotmail_email, oracle_password, runner_id)

            # Wait for verification email via IMAP
            logger.info(f"{runner_id}: Checking Hotmail inbox for verification email...")
            verify_url = wait_for_oracle_verification_email_imap(
                hotmail_email,
                hotmail_password,
                access_token,
                runner_id
            )

            if not verify_url:
                logger.error(f"{runner_id}: Failed to get verification URL")
                savecreated('oracle_failed', f"{hotmail_email}:{oracle_password} - No verification email")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return False

            # Verify email
            if not verify_email(verify_url, page, runner_id):
                logger.error(f"{runner_id}: Verification failed")
                savecreated('oracle_failed', f"{hotmail_email}:{oracle_password} - Verification failed")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return False

            # Save successful account
            savecreated('oracle_accounts', f"{hotmail_email}:{oracle_password}")
            logger.success(f"{runner_id}: Oracle account created successfully: {hotmail_email}")

            browser.close()
            if progress_bar:
                progress_bar.update(1)
            return True

        except Exception as e:
            logger.error(f"{runner_id}: Failed - {e}")
            savecreated('oracle_failed', f"{hotmail_email}:{oracle_password} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)
            return False


if __name__ == "__main__":
    clear_console()
    logger.info("Oracle Account Creation Script (Using Hotmail)")
    logger.info("=" * 60)

    # Load Oracle password
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            oracle_password = file.read().strip()
        logger.info(f"Loaded Oracle password from password.txt")
    except FileNotFoundError:
        logger.error("'password.txt' not found")
        exit(1)

    # Load country
    try:
        with open("country.txt", "r", encoding="utf8") as file:
            country_line = file.read().strip()
            if country_line and '+' in country_line:
                parts = country_line.rsplit('+', 1)
                country_name = parts[0].strip()
                country_code = '+' + parts[1].strip()
                logger.info(f"Loaded country: {country_name} {country_code}")
            else:
                logger.error("Invalid format in country.txt. Expected: 'Egypt +20'")
                exit(1)
    except FileNotFoundError:
        logger.error("'country.txt' not found")
        exit(1)

    # Load Hotmail accounts
    hotmail_accounts = read_hotmail_accounts()
    if not hotmail_accounts:
        logger.error("No Hotmail accounts found in accounts.txt")
        logger.info("Expected format: email:password:refresh_token:client_id OR email:password")
        exit(1)

    logger.info(f"Loaded {len(hotmail_accounts)} Hotmail account(s)")

    # Ask for number of accounts and workers
    num_accounts = int(input('Number of Oracle accounts to create: '))
    num_workers = int(input('Number of concurrent workers: '))

    # Limit to available Hotmail accounts
    if num_accounts > len(hotmail_accounts):
        logger.warning(f"Only {len(hotmail_accounts)} Hotmail accounts available, limiting to that")
        num_accounts = len(hotmail_accounts)

    # Initialize progress bar
    with tqdm(total=num_accounts, desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Use the first num_accounts Hotmail accounts
            tasks = []
            for i in range(num_accounts):
                hotmail_account = hotmail_accounts[i]
                tasks.append((i, hotmail_account, oracle_password, progress_bar))

            executor.map(lambda args: create_account_worker(*args), tasks)

    logger.success("Script finished!")
    input('Press Enter to exit...')
