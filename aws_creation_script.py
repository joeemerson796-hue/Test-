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

# Country/Region Configuration (for phone number and address)
# You can change these values to use a different country
COUNTRY_NAME = "Mozambique"           # Country name as it appears in dropdown
PHONE_CODE = "+258"                    # International phone code
PHONE_NUMBER = "573596-0999"          # Phone number (without country code)
ADDRESS_LINE = "Avenue de Bouillon 38" # Street address
CITY = "Maputo"                        # City name
POSTAL_CODE = "1100"                   # Postal/ZIP code

# ============================================================================

# Global lock for thread-safe file operations
file_lock = Lock()

# Global session for connection reuse
session = requests.Session()


def clear_console():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    """Save results to file in a thread-safe manner"""
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def generate_random_string(length):
    """Generate a random string with letters only"""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))


def generate_random_numbers(length):
    """Generate a random numeric string"""
    return ''.join(random.choice(string.digits) for _ in range(length))


def check_and_handle_error_alert(page, button_locator, button_description, runner_id, max_retries=3):
    """
    Check for error alert and retry clicking button with human-like behavior
    Returns True if successful (no error alert), False if failed after retries
    """
    for attempt in range(max_retries):
        try:
            # Wait a moment for any error alert to appear after button action
            time.sleep(random.uniform(0.8, 1.2))

            # Check if error alert is visible
            error_alert = page.locator('div[data-testid="error-alert"][aria-hidden="false"]')
            is_error_visible = error_alert.is_visible(timeout=1500)

            if is_error_visible:
                logger.warning(f"{runner_id}: Error alert detected! Attempt {attempt + 1}/{max_retries} to fix...")

                # Dismiss the alert first
                try:
                    dismiss_button = error_alert.locator('button.awsui_dismiss-button_mx3cw_ocy3i_400').first
                    if dismiss_button.is_visible(timeout=1000):
                        dismiss_button.click(timeout=2000)
                        logger.info(f"{runner_id}: Dismissed error alert")
                        time.sleep(0.4)
                except Exception as dismiss_err:
                    logger.warning(f"{runner_id}: Could not dismiss alert: {dismiss_err}")

                # Wait a random amount (human-like)
                time.sleep(random.uniform(0.6, 1.2))

                # Retry clicking the button with human-like behavior
                logger.info(f"{runner_id}: Retrying {button_description} (attempt {attempt + 1})...")
                try:
                    button_locator.click(force=True, timeout=5000)
                    time.sleep(random.uniform(0.5, 0.9))
                except Exception as click_err:
                    logger.error(f"{runner_id}: Failed to click button: {click_err}")
                    if attempt == max_retries - 1:
                        return False
                    continue

                # Continue loop to check if error still appears

            else:
                # No error alert visible - success!
                logger.success(f"{runner_id}: No error alert - {button_description} successful")
                return True

        except Exception as e:
            logger.error(f"{runner_id}: Error in alert handling (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(random.uniform(0.5, 1.0))

    # If we exhausted all retries and still have errors
    logger.error(f"{runner_id}: Failed to clear error alert after {max_retries} attempts")
    return False


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


def aws_account_creation(email_address, hotmail_password, refresh_token, client_id,
                         aws_password, card_number, runner_id, progress_bar=None):
    """
    AWS Account Creation Script - Creates account up to payment submission
    Saves: email:hotmailpassword:refreshtoken:clientid:awspassword to created.txt
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

            # Navigate to AWS signup
            logger.info(f"{runner_id}: Navigating to AWS registration page...")
            page.goto("https://portal.aws.amazon.com/billing/signup")
            time.sleep(2)

            # Step 1: Enter email
            logger.info(f"{runner_id}: Entering email: {email_address}...")
            email_input = page.locator('input#emailAddress')
            email_input.fill(email_address)
            time.sleep(0.5)

            # Step 2: Enter account name
            account_name = email_address.split('@')[0]
            logger.info(f"{runner_id}: Entering account name: {account_name}...")
            account_name_input = page.locator('input#accountName')
            account_name_input.wait_for(state="visible", timeout=10000)
            account_name_input.fill(account_name)
            time.sleep(0.5)

            # Step 3: Click "Verify email address" button
            logger.info(f"{runner_id}: Clicking Verify email address button...")
            verify_button = page.locator('button[data-testid="collect-email-submit-button"]')
            verify_button.wait_for(state="visible", timeout=10000)
            verify_button.click()
            time.sleep(0.8)

            # Check for error alert and retry if needed (before captcha appears)
            logger.info(f"{runner_id}: Checking for error alert after verify button click...")
            if not check_and_handle_error_alert(page, verify_button, "Verify email address button", runner_id, max_retries=5):
                logger.error(f"{runner_id}: Failed to verify email address after retries")
                savecreated('failed', f"{email_address} - Email verification failed with persistent error alert")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            time.sleep(1.5)

            # Step 4: Handle captcha
            logger.info(f"{runner_id}: Looking for captcha iframe...")
            try:
                iframe_element = page.locator('iframe#core-container, iframe[title="iframe"]').first
                iframe_element.wait_for(state="attached", timeout=20000)
                time.sleep(2)

                iframe = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
                logger.info(f"{runner_id}: Found captcha iframe")

                # Retry loop for captcha (up to 5 attempts)
                max_captcha_attempts = 5
                captcha_solved = False

                for attempt in range(1, max_captcha_attempts + 1):
                    logger.info(f"{runner_id}: Captcha attempt {attempt}/{max_captcha_attempts}")

                    try:
                        captcha_img = iframe.locator('img[alt="captcha"]')
                        captcha_img.wait_for(state="visible", timeout=20000)
                        time.sleep(0.8)

                        captcha_src = captcha_img.get_attribute("src")
                        logger.info(f"{runner_id}: Captcha image found: {captcha_src[:100]}...")

                        # Solve captcha
                        captcha_solution = solve_captcha_yescaptcha(captcha_src, page)
                        if not captcha_solution:
                            logger.error(f"{runner_id}: Failed to solve captcha on attempt {attempt}")
                            if attempt < max_captcha_attempts:
                                logger.info(f"{runner_id}: Retrying captcha...")
                                time.sleep(0.8)
                                continue
                            else:
                                logger.error(f"{runner_id}: Failed to solve captcha after {max_captcha_attempts} attempts")
                                savecreated('failed', f"{email_address} - Failed to solve captcha")
                                browser.close()
                                if progress_bar:
                                    progress_bar.update(1)
                                return

                        # Enter captcha solution
                        logger.info(f"{runner_id}: Entering captcha solution: {captcha_solution}...")
                        captcha_input = iframe.locator('input[name="captchaGuess"], input[placeholder*="verification"], input[placeholder*="answer"]')
                        captcha_input.wait_for(state="visible", timeout=10000)
                        captcha_input.clear()
                        captcha_input.fill(captcha_solution)
                        time.sleep(1)

                        # Click Submit button
                        logger.info(f"{runner_id}: Clicking Submit button...")
                        submit_button = iframe.locator('button[type="submit"], button:has-text("Submit")').first
                        submit_button.click()
                        time.sleep(2)  # WAIT TIME AFTER CAPTCHA SUBMIT - Change this if needed (in seconds)

                        # Check for error
                        try:
                            error_message = iframe.locator('div.awsui_error_1i0s3_1goap_185, div[id*="form-error"]:has-text("wasn\'t quite right")').first
                            if error_message.is_visible(timeout=3000):
                                error_text = error_message.inner_text()
                                logger.warning(f"{runner_id}: Captcha error on attempt {attempt}: {error_text}")
                                if attempt < max_captcha_attempts:
                                    logger.info(f"{runner_id}: Retrying captcha...")
                                    time.sleep(0.8)
                                    continue
                                else:
                                    logger.error(f"{runner_id}: Captcha failed after {max_captcha_attempts} attempts")
                                    savecreated('failed', f"{email_address} - Captcha incorrect after {max_captcha_attempts} attempts")
                                    browser.close()
                                    if progress_bar:
                                        progress_bar.update(1)
                                    return
                        except:
                            logger.success(f"{runner_id}: Captcha solved successfully on attempt {attempt}!")
                            captcha_solved = True
                            time.sleep(0.8)
                            break

                        # Success
                        captcha_solved = True
                        break

                    except Exception as e:
                        logger.error(f"{runner_id}: Error on captcha attempt {attempt}: {e}")
                        if attempt < max_captcha_attempts:
                            logger.info(f"{runner_id}: Retrying captcha...")
                            time.sleep(0.8)
                            continue
                        else:
                            raise

                if not captcha_solved:
                    logger.error(f"{runner_id}: Failed to solve captcha")
                    savecreated('failed', f"{email_address} - Failed to solve captcha")
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return

            except Exception as e:
                logger.error(f"{runner_id}: Error handling iframe captcha: {e}")
                savecreated('failed', f"{email_address} - Captcha error: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 5: Get verification code from email
            logger.info(f"{runner_id}: Waiting for verification code email...")
            time.sleep(5)

            verification_code = get_verification_code(email_address, refresh_token, client_id)
            if not verification_code:
                logger.error(f"{runner_id}: Failed to get verification code")
                savecreated('failed', f"{email_address} - Could not get verification code")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 6: Enter verification code
            logger.info(f"{runner_id}: Entering verification code: {verification_code}...")
            otp_input = page.locator('input#otp')
            otp_input.wait_for(state="visible", timeout=15000)
            otp_input.fill(verification_code)
            time.sleep(0.5)

            # Click Verify button with error handling
            logger.info(f"{runner_id}: Clicking Verify button after OTP...")
            verify_button_otp = page.locator('button[data-testid="verify-email-submit-button"]')
            verify_button_otp.wait_for(state="visible", timeout=10000)
            verify_button_otp.click()
            time.sleep(0.8)

            # Check for error alert and retry
            if not check_and_handle_error_alert(page, verify_button_otp, "Verify button", runner_id):
                logger.error(f"{runner_id}: Failed to verify OTP after retries")
                savecreated('failed', f"{email_address} - OTP verification failed with error alert")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            time.sleep(1.5)

            # Step 7: Set password
            logger.info(f"{runner_id}: Setting password...")
            password_input = page.locator('input#password')
            password_input.wait_for(state="visible", timeout=15000)
            password_input.fill(aws_password)
            time.sleep(0.5)

            re_password_input = page.locator('input#rePassword')
            re_password_input.fill(aws_password)
            time.sleep(0.5)

            # Click Continue
            logger.info(f"{runner_id}: Clicking Continue (step 1 of 5)...")
            continue_step1_button = page.locator('button[data-testid="create-password-submit-button"]')
            continue_step1_button.click()
            time.sleep(2)

            # Step 8: Choose account plan (Free)
            logger.info(f"{runner_id}: Choosing account plan...")
            try:
                free_plan_button = page.locator('button:has-text("Choose free plan")')
                free_plan_button.wait_for(state="visible", timeout=15000)
                logger.info(f"{runner_id}: Clicking 'Choose free plan' button...")
                free_plan_button.click()
                time.sleep(1)
                logger.success(f"{runner_id}: Free plan selected")
            except Exception as e:
                logger.warning(f"{runner_id}: Could not find account plan selection, may have been skipped: {e}")

            # Step 9: Select account type (Personal)
            logger.info(f"{runner_id}: Selecting Personal account type...")
            personal_radio = page.locator('input[name="accountType"][value="Personal"]')
            personal_radio.wait_for(state="visible", timeout=15000)
            personal_radio.click()
            time.sleep(0.5)

            # Step 10: Select phone code
            logger.info(f"{runner_id}: Selecting phone code +258 (Mozambique)...")
            phone_code_button = page.locator('button#address\\.phoneCode')
            phone_code_button.click()
            time.sleep(0.5)

            phone_258 = page.locator('[role="option"]:has-text("+258")').first
            phone_258.click()
            time.sleep(0.5)

            # Step 11: Enter full name
            full_name = generate_random_string(12)
            logger.info(f"{runner_id}: Entering full name: {full_name}...")
            full_name_input = page.locator('input#address\\.fullName')
            full_name_input.wait_for(state="visible", timeout=10000)
            full_name_input.fill(full_name)
            time.sleep(0.5)

            # Step 12: Enter phone number
            logger.info(f"{runner_id}: Entering phone number: {PHONE_NUMBER}...")
            phone_input = page.locator('input#address\\.phoneNumber')
            phone_input.fill(PHONE_NUMBER)
            time.sleep(0.5)

            # Step 13: Select country
            logger.info(f"{runner_id}: Selecting country {COUNTRY_NAME}...")
            try:
                country_button = page.locator('button#address\\.country')
                country_button.wait_for(state="visible", timeout=10000)
                logger.info(f"{runner_id}: Clicking country dropdown...")
                country_button.click()
                time.sleep(0.6)

                logger.info(f"{runner_id}: Typing {COUNTRY_NAME} in search...")
                country_search = page.locator('input[role="combobox"]').last
                country_search.wait_for(state="visible", timeout=10000)
                time.sleep(0.3)
                country_search.fill(COUNTRY_NAME)
                time.sleep(0.6)

                logger.info(f"{runner_id}: Selecting {COUNTRY_NAME} from list...")
                country_option = page.locator(f'[role="option"]:has-text("{COUNTRY_NAME}")').first
                country_option.wait_for(state="visible", timeout=10000)
                country_option.click()
                time.sleep(0.5)
                logger.success(f"{runner_id}: Country set to {COUNTRY_NAME}")
            except Exception as e:
                logger.error(f"{runner_id}: Error selecting country: {e}")
                raise

            # Step 14: Fill address
            logger.info(f"{runner_id}: Entering address...")
            address_input = page.locator('input#address\\.addressLine1')
            address_input.fill(ADDRESS_LINE)
            time.sleep(0.5)

            city_input = page.locator('input#address\\.city')
            city_input.fill(CITY)
            time.sleep(0.5)

            state_input = page.locator('input#address\\.state')
            state_input.fill(CITY)
            time.sleep(0.5)

            postal_input = page.locator('input#address\\.postalCode')
            postal_input.fill(POSTAL_CODE)
            time.sleep(0.5)

            # Step 15: Check agreement
            logger.info(f"{runner_id}: Checking AWS Customer Agreement...")
            agreement_checkbox = page.locator('input#agreement')
            agreement_checkbox.check()
            time.sleep(0.5)

            # Step 16: Click Agree and Continue
            logger.info(f"{runner_id}: Clicking Agree and Continue (step 2 of 5)...")
            agree_button = page.locator('button[data-testid="contact-information-submit-button"]')
            agree_button.click()
            time.sleep(2)

            # Step 17: Fill card information
            logger.info(f"{runner_id}: Entering card number: {card_number}...")
            card_input = page.locator('input#cardNumber')
            card_input.wait_for(state="visible", timeout=15000)
            card_input.fill(card_number)
            time.sleep(0.5)

            # Select expiration month (May)
            logger.info(f"{runner_id}: Selecting expiration month...")
            month_button = page.locator('button#expirationMonth')
            month_button.wait_for(state="visible", timeout=10000)
            month_button.click()
            time.sleep(0.8)

            month_dropdown = page.locator('div.awsui_dropdown_qwoo0_8ly6o_153[aria-hidden="false"]').first
            month_dropdown.wait_for(state="visible", timeout=10000)
            time.sleep(0.5)

            month_option = page.locator('[role="option"]:has-text("May")').first
            month_option.wait_for(state="visible", timeout=10000)
            month_option.click()
            time.sleep(0.5)

            # Select expiration year (2027)
            logger.info(f"{runner_id}: Selecting expiration year 2027...")
            year_button = page.locator('button#expirationYear')
            year_button.wait_for(state="visible", timeout=10000)
            year_button.click()
            time.sleep(0.8)

            year_dropdown = page.locator('div.awsui_dropdown_qwoo0_8ly6o_153[aria-hidden="false"]').first
            year_dropdown.wait_for(state="visible", timeout=10000)
            time.sleep(0.5)

            year_option = page.locator('[role="option"]:has-text("2027")').first
            year_option.wait_for(state="visible", timeout=10000)
            year_option.click()
            time.sleep(0.5)

            # Enter CVV
            cvv = generate_random_numbers(3)
            logger.info(f"{runner_id}: Entering CVV: {cvv}...")
            cvv_input = page.locator('input#sor\\.cvv')
            cvv_input.fill(cvv)
            time.sleep(0.5)

            # Enter account holder name
            holder_name = generate_random_string(12)
            logger.info(f"{runner_id}: Entering account holder name: {holder_name}...")
            holder_input = page.locator('input#accountHolderName')
            holder_input.fill(holder_name)
            time.sleep(0.5)

            # Step 18: Click "Verify and continue (step 3 of 5)" - FINAL STEP FOR CREATION
            logger.info(f"{runner_id}: Clicking Verify and continue (step 3 of 5)...")
            verify_payment_button = page.locator('button[data-testid="payment-information-submit-button"]')
            verify_payment_button.click()
            time.sleep(3)

            # SUCCESS - Save account details to created.txt
            logger.success(f"{runner_id}: Account creation completed! Saving to created.txt...")
            savecreated('created', f"{email_address}:{hotmail_password}:{refresh_token}:{client_id}:{aws_password}")
            logger.success(f"{runner_id}: ✅ Account saved successfully!")

            # Keep browser open for a moment to ensure submission went through
            time.sleep(5)

            browser.close()
            if progress_bar:
                progress_bar.update(1)

    except Exception as e:
        logger.error(f"{runner_id}: Account creation failed - {e}")
        savecreated('failed', f"{email_address} - {e}")
        if browser:
            browser.close()
        if progress_bar:
            progress_bar.update(1)


def run_worker(account_data, aws_password, card_number, runner_id, progress_bar):
    """Worker function for threading"""
    # Parse account data: email:hotmail_password:refresh_token:client_id
    parts = account_data.split(':')
    if len(parts) < 4:
        logger.error(f"{runner_id}: Invalid account format: {account_data}")
        if progress_bar:
            progress_bar.update(1)
        return

    email_address = parts[0]
    hotmail_password = parts[1]
    refresh_token = ':'.join(parts[2:-1])  # Handle refresh tokens with colons
    client_id = parts[-1]

    logger.info(f"{runner_id}: Starting AWS account creation for {email_address}")
    aws_account_creation(email_address, hotmail_password, refresh_token, client_id,
                        aws_password, card_number, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()

    # Read accounts from file
    with open("accounts.txt", "r", encoding="utf8") as f:
        accounts = [line.strip() for line in f if line.strip()]

    # Read AWS password
    with open("password.txt", "r", encoding="utf8") as f:
        aws_password = f.read().strip()

    # Read card number
    with open("cards.txt", "r", encoding="utf8") as f:
        card_number = f.read().strip().split('\n')[0]

    logger.info(f"Loaded {len(accounts)} accounts")
    logger.info(f"AWS Password: {aws_password}")
    logger.info(f"Card: {card_number}")

    # Get number of threads
    max_threads = int(input("How many threads? "))

    # Progress bar
    progress_bar = tqdm(total=len(accounts), desc="Progress", unit="account")

    # Run with threading
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for idx, account in enumerate(accounts, 1):
            executor.submit(run_worker, account, aws_password, card_number, f"Worker-{idx}", progress_bar)

    progress_bar.close()
    logger.success("All accounts processed!")
