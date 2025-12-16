import os
import time
import random
import string
import base64
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

# ============================================================================
# CONFIGURATION - Change these settings as needed
# ============================================================================

# YesCaptcha API configuration
YESCAPTCHA_CLIENT_KEY = "8d381f04402598ed227557a6acb91a6da1a909c375946"

# Country/Region Configuration (for phone verification)
COUNTRY_NAME = "Mozambique"           # Country name as it appears in dropdown
PHONE_NUMBER_FROM_FILE = True         # If True, reads phone from numbers.txt, if False uses config below
PHONE_NUMBER_DEFAULT = "573596-0999"  # Default phone if not reading from file

# ============================================================================

# Global lock for thread-safe file operations
file_lock = Lock()

# Global session for connection reuse
session = requests.Session()


def clear_console():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def savecompleted(filename, message):
    """Save results to file in a thread-safe manner"""
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def solve_captcha_yescaptcha(image_url, page):
    """
    Solve captcha using YesCaptcha API
    Returns the solved text or None if failed
    """
    try:
        # Download captcha image using page context
        logger.info("Downloading captcha image...")
        captcha_response = page.request.get(image_url)
        captcha_image_bytes = captcha_response.body()

        # Convert to base64
        captcha_base64 = base64.b64encode(captcha_image_bytes).decode('utf-8')
        logger.info(f"Captcha converted to base64 (length: {len(captcha_base64)})")

        # Create task
        data = {
            "clientKey": YESCAPTCHA_CLIENT_KEY,
            "task": {
                "type": "ImageToTextTaskMuggle",
                "body": captcha_base64
            }
        }

        logger.info("Sending captcha to YesCaptcha API...")
        response = requests.post("https://api.yescaptcha.com/createTask", json=data, timeout=30)
        result = response.json()

        if result.get("errorId") != 0:
            logger.error(f"YesCaptcha API error: {result.get('errorDescription')}")
            return None

        task_id = result.get("taskId")
        logger.info(f"Task created: {task_id}, waiting for solution...")

        # Poll for result (max 60 seconds)
        for attempt in range(30):  # 30 attempts * 2 seconds = 60 seconds
            time.sleep(2)

            get_result_data = {
                "clientKey": YESCAPTCHA_CLIENT_KEY,
                "taskId": task_id
            }

            get_response = requests.post("https://api.yescaptcha.com/getTaskResult", json=get_result_data, timeout=30)
            get_result = get_response.json()

            if get_result.get("status") == "ready":
                captcha_text = get_result.get("solution", {}).get("text")
                logger.success(f"Captcha solved: {captcha_text}")
                return captcha_text
            elif get_result.get("status") == "failed":
                logger.error("YesCaptcha failed to solve captcha")
                return None

        logger.error("Captcha solving timeout")
        return None

    except Exception as e:
        logger.error(f"Error solving captcha: {e}")
        return None


def get_verification_code(email_address, refresh_token, client_id, max_attempts=12):
    """
    Get verification code from Hotmail/Outlook inbox using IMAP with OAuth2
    """
    try:
        # Build OAuth2 string
        auth_string = f"user={email_address}\x01auth=Bearer {refresh_token}\x01\x01"

        # Connect to IMAP
        logger.info(f"Connecting to Outlook IMAP...")
        imap = imaplib.IMAP4_SSL('outlook.office365.com')

        # Authenticate using OAuth2
        logger.info(f"Authenticating with OAuth2...")
        imap.authenticate('XOAUTH2', lambda x: auth_string.encode())

        logger.info(f"Selecting INBOX...")
        imap.select('INBOX')

        # Try multiple times with delay
        for attempt in range(max_attempts):
            logger.info(f"Attempt {attempt + 1}/{max_attempts} to find verification email...")

            # Search for emails from AWS
            result, data = imap.search(None, '(FROM "no-reply-aws@amazon.com")')

            if result == 'OK' and data[0]:
                email_ids = data[0].split()

                # Get the most recent email
                latest_email_id = email_ids[-1]
                result, email_data = imap.fetch(latest_email_id, '(RFC822)')

                if result == 'OK':
                    raw_email = email_data[0][1]
                    email_message = email.message_from_bytes(raw_email)

                    # Get email body
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/html":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = email_message.get_payload(decode=True).decode()

                    # Try multiple regex patterns to extract 6-digit code
                    patterns = [
                        r'class="x_code"[^>]*>(\d{6})<',  # Outlook web format
                        r'class="code"[^>]*>(\d{6})<',     # Raw email format
                        r'Verification code.*?(\d{6})',    # Text-based search
                        r'>\s*(\d{6})\s*<'                 # Generic 6-digit code in tags
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, body)
                        if match:
                            code = match.group(1)
                            logger.success(f"Verification code found: {code}")
                            imap.close()
                            imap.logout()
                            return code

                    logger.warning(f"Email found but could not extract code on attempt {attempt + 1}")

            # Wait before next attempt
            if attempt < max_attempts - 1:
                time.sleep(10)

        logger.error("Could not find verification code after all attempts")
        imap.close()
        imap.logout()
        return None

    except Exception as e:
        logger.error(f"Error getting verification code: {e}")
        return None


def aws_login_and_complete(email_address, hotmail_password, refresh_token, client_id,
                           aws_password, phone_number, runner_id, progress_bar=None):
    """
    AWS Login and Completion Script
    Logs in to existing AWS account and completes phone verification
    """
    browser = None

    try:
        with sync_playwright() as p:
            # Launch browser
            logger.info(f"{runner_id}: Launching browser...")
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = context.new_page()
            stealth_sync(page)

            # Navigate to AWS login
            logger.info(f"{runner_id}: Navigating to AWS login page...")
            page.goto("https://signin.aws.amazon.com/signin")
            time.sleep(2)

            # Step 1: Enter email/account ID
            logger.info(f"{runner_id}: Entering email: {email_address}...")
            email_input = page.locator('input#resolving_input, input#username')
            email_input.wait_for(state="visible", timeout=10000)
            email_input.fill(email_address)
            time.sleep(0.5)

            # Click Next
            next_button = page.locator('button#next_button, button:has-text("Next")')
            next_button.click()
            time.sleep(2)

            # Step 2: Enter password
            logger.info(f"{runner_id}: Entering password...")
            password_input = page.locator('input#password, input[type="password"]')
            password_input.wait_for(state="visible", timeout=10000)
            password_input.fill(aws_password)
            time.sleep(0.5)

            # Click Sign In
            signin_button = page.locator('button#signin_button, button:has-text("Sign in")')
            signin_button.click()
            time.sleep(3)

            # Step 3: Handle email OTP verification if prompted
            logger.info(f"{runner_id}: Checking for OTP verification...")
            try:
                otp_input = page.locator('input[name="otp"], input#otp, input[placeholder*="verification"]')
                if otp_input.is_visible(timeout=5000):
                    logger.info(f"{runner_id}: OTP verification required, getting code from email...")

                    # Get verification code from email
                    time.sleep(5)
                    verification_code = get_verification_code(email_address, refresh_token, client_id)

                    if not verification_code:
                        logger.error(f"{runner_id}: Failed to get login OTP")
                        savecompleted('failed', f"{email_address} - Could not get login OTP")
                        browser.close()
                        if progress_bar:
                            progress_bar.update(1)
                        return

                    # Enter OTP
                    logger.info(f"{runner_id}: Entering login OTP: {verification_code}...")
                    otp_input.fill(verification_code)
                    time.sleep(0.5)

                    # Submit OTP
                    verify_button = page.locator('button:has-text("Verify"), button:has-text("Submit")')
                    verify_button.click()
                    time.sleep(3)
                else:
                    logger.info(f"{runner_id}: No OTP required, proceeding...")
            except Exception as e:
                logger.info(f"{runner_id}: No OTP verification needed: {e}")

            # Step 4: Navigate to phone verification page
            logger.info(f"{runner_id}: Navigating to phone verification page...")
            time.sleep(2)

            # Try to find the phone verification page or navigate directly
            try:
                # Check if already on phone verification page
                phone_input_check = page.locator('input#phoneNumber')
                if not phone_input_check.is_visible(timeout=3000):
                    # Navigate to signup continuation if needed
                    page.goto("https://portal.aws.amazon.com/billing/signup#/identityverification")
                    time.sleep(3)
            except:
                # Already on correct page or will handle below
                pass

            # Step 5: Select country for phone verification
            logger.info(f"{runner_id}: Selecting phone verification country {COUNTRY_NAME}...")
            phone_country_button = page.locator('button#country')
            phone_country_button.wait_for(state="visible", timeout=15000)
            phone_country_button.click()
            time.sleep(0.6)

            # Search for country
            phone_country_search = page.locator('input[role="combobox"]').first
            phone_country_search.fill(COUNTRY_NAME)
            time.sleep(0.6)

            # Select country
            country_option = page.locator(f'[role="option"]:has-text("{COUNTRY_NAME}")').first
            country_option.click()
            time.sleep(0.5)

            # Step 6: Enter phone number
            logger.info(f"{runner_id}: Entering phone number: {phone_number}...")
            verification_phone_input = page.locator('input#phoneNumber')
            verification_phone_input.fill(phone_number)
            time.sleep(0.5)

            # Step 7: Click "Send SMS"
            logger.info(f"{runner_id}: Clicking Send SMS...")
            send_sms_button = page.locator('button[type="submit"]').filter(has_text="Send SMS")
            send_sms_button.click()
            time.sleep(2)  # WAIT TIME AFTER SEND SMS - Change this if needed (in seconds)

            # Step 8: Solve captcha if appears (iframe-based)
            logger.info(f"{runner_id}: Checking for captcha...")
            try:
                iframe_element = page.locator('iframe#core-container, iframe[title="iframe"]').first
                iframe_element.wait_for(state="attached", timeout=15000)
                time.sleep(2)

                iframe = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
                logger.info(f"{runner_id}: Found captcha iframe")

                # Retry loop for captcha (up to 5 attempts)
                max_captcha_attempts = 5
                for attempt in range(1, max_captcha_attempts + 1):
                    logger.info(f"{runner_id}: Captcha attempt {attempt}/{max_captcha_attempts}")

                    try:
                        captcha_img = iframe.locator('img[alt="captcha"]')
                        captcha_img.wait_for(state="visible", timeout=20000)
                        time.sleep(0.8)

                        captcha_src = captcha_img.get_attribute("src")
                        logger.info(f"{runner_id}: Captcha found...")

                        # Solve captcha
                        captcha_solution = solve_captcha_yescaptcha(captcha_src, page)
                        if not captcha_solution:
                            logger.error(f"{runner_id}: Failed to solve captcha on attempt {attempt}")
                            if attempt < max_captcha_attempts:
                                time.sleep(0.8)
                                continue
                            else:
                                logger.warning(f"{runner_id}: Could not solve captcha, continuing anyway...")
                                break

                        # Enter captcha solution
                        logger.info(f"{runner_id}: Entering captcha solution: {captcha_solution}...")
                        captcha_input = iframe.locator('input[name="captchaGuess"], input[placeholder*="verification"], input[placeholder*="answer"]')
                        captcha_input.clear()
                        captcha_input.fill(captcha_solution)
                        time.sleep(1)

                        # Click Submit
                        logger.info(f"{runner_id}: Clicking Submit...")
                        submit_button = iframe.locator('button[type="submit"], button:has-text("Submit")').first
                        submit_button.click()
                        time.sleep(2)  # WAIT TIME AFTER CAPTCHA SUBMIT - Change this if needed (in seconds)

                        # Check for error
                        try:
                            error_message = iframe.locator('div.awsui_error_1i0s3_1goap_185, div[id*="form-error"]:has-text("wasn\'t quite right")').first
                            if error_message.is_visible(timeout=3000):
                                logger.warning(f"{runner_id}: Captcha error on attempt {attempt}")
                                if attempt < max_captcha_attempts:
                                    time.sleep(0.8)
                                    continue
                                else:
                                    logger.warning(f"{runner_id}: Captcha failed, continuing...")
                                    break
                        except:
                            logger.success(f"{runner_id}: Captcha solved successfully!")
                            break

                        break

                    except Exception as e:
                        logger.error(f"{runner_id}: Error on captcha attempt {attempt}: {e}")
                        if attempt < max_captcha_attempts:
                            time.sleep(0.8)
                            continue
                        else:
                            break

            except Exception as e:
                logger.info(f"{runner_id}: No captcha appeared or error handling it: {e}")

            # Step 9: Retry loop (3 times) - Refresh and resend SMS
            logger.info(f"{runner_id}: Starting retry loop (3 attempts)...")
            for retry in range(3):
                logger.info(f"{runner_id}: === Retry {retry + 1}/3 ===")

                # Refresh page
                logger.info(f"{runner_id}: Refreshing page...")
                page.reload(wait_until="domcontentloaded")
                time.sleep(1)

                # Re-select country
                try:
                    phone_country_button2 = page.locator('button#country')
                    phone_country_button2.wait_for(state="visible", timeout=10000)
                    phone_country_button2.click()
                    time.sleep(0.6)

                    phone_country_search2 = page.locator('input[role="combobox"]').first
                    phone_country_search2.fill(COUNTRY_NAME)
                    time.sleep(0.6)

                    country_option2 = page.locator(f'[role="option"]:has-text("{COUNTRY_NAME}")').first
                    country_option2.click()
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"{runner_id}: Error selecting country on retry {retry + 1}: {e}")

                # Re-enter phone
                try:
                    verification_phone_input2 = page.locator('input#phoneNumber')
                    verification_phone_input2.fill(phone_number)
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"{runner_id}: Error entering phone on retry {retry + 1}: {e}")

                # Click Send SMS
                try:
                    send_sms_button2 = page.locator('button[type="submit"]').filter(has_text="Send SMS")
                    send_sms_button2.click()
                    time.sleep(2)  # WAIT TIME AFTER SEND SMS - Change this if needed (in seconds)
                except Exception as e:
                    logger.warning(f"{runner_id}: Error clicking Send SMS on retry {retry + 1}: {e}")

                # Handle captcha if appears
                try:
                    iframe_retry = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
                    captcha_img_retry = iframe_retry.locator('img[alt="captcha"]')

                    if captcha_img_retry.is_visible(timeout=5000):
                        logger.info(f"{runner_id}: Captcha appeared on retry {retry + 1}")

                        captcha_src_retry = captcha_img_retry.get_attribute("src")
                        captcha_solution_retry = solve_captcha_yescaptcha(captcha_src_retry, page)

                        if captcha_solution_retry:
                            captcha_input_retry = iframe_retry.locator('input[name="captchaGuess"]')
                            captcha_input_retry.fill(captcha_solution_retry)
                            time.sleep(1)

                            submit_retry = iframe_retry.locator('button[type="submit"]').first
                            submit_retry.click()
                            time.sleep(2)  # WAIT TIME AFTER CAPTCHA SUBMIT - Change this if needed (in seconds)
                except Exception as e:
                    logger.info(f"{runner_id}: No captcha on retry {retry + 1}: {e}")

                time.sleep(1)

            # SUCCESS - Account login and phone verification completed
            logger.success(f"{runner_id}: ✅ Login and phone verification completed!")
            savecompleted('completed', f"{email_address}:{aws_password}")

            # Keep browser open for manual SMS code entry
            logger.info(f"{runner_id}: Browser will remain open for manual SMS code entry...")
            logger.info(f"{runner_id}: Press Ctrl+C when done or wait 60 seconds...")
            time.sleep(60)

            browser.close()
            if progress_bar:
                progress_bar.update(1)

    except Exception as e:
        logger.error(f"{runner_id}: Login/completion failed - {e}")
        savecompleted('failed', f"{email_address} - {e}")
        if browser:
            browser.close()
        if progress_bar:
            progress_bar.update(1)


def run_worker(account_data, phone_number, runner_id, progress_bar):
    """Worker function for threading"""
    # Parse account data: email:hotmail_password:refresh_token:client_id:aws_password
    parts = account_data.split(':')
    if len(parts) < 5:
        logger.error(f"{runner_id}: Invalid account format (expected 5 parts): {account_data}")
        if progress_bar:
            progress_bar.update(1)
        return

    email_address = parts[0]
    hotmail_password = parts[1]
    # Handle refresh tokens with colons
    refresh_token = ':'.join(parts[2:-2])
    client_id = parts[-2]
    aws_password = parts[-1]

    logger.info(f"{runner_id}: Starting AWS login and completion for {email_address}")
    aws_login_and_complete(email_address, hotmail_password, refresh_token, client_id,
                          aws_password, phone_number, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()

    # Read accounts from created.txt
    with open("created.txt", "r", encoding="utf8") as f:
        accounts = [line.strip() for line in f if line.strip()]

    # Read phone numbers from numbers.txt (one per line)
    if PHONE_NUMBER_FROM_FILE:
        with open("numbers.txt", "r", encoding="utf8") as f:
            phone_numbers = [line.strip() for line in f if line.strip()]
    else:
        phone_numbers = [PHONE_NUMBER_DEFAULT] * len(accounts)

    logger.info(f"Loaded {len(accounts)} accounts from created.txt")
    logger.info(f"Loaded {len(phone_numbers)} phone numbers")

    # Get number of threads
    max_threads = int(input("How many threads? "))

    # Progress bar
    progress_bar = tqdm(total=len(accounts), desc="Progress", unit="account")

    # Run with threading
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for idx, account in enumerate(accounts):
            # Get phone number for this account (cycle if not enough)
            phone_number = phone_numbers[idx % len(phone_numbers)]
            executor.submit(run_worker, account, phone_number, f"Worker-{idx+1}", progress_bar)

    progress_bar.close()
    logger.success("All accounts processed!")
