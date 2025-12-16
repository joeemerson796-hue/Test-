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
            elif get_result.get("status") == "processing":
                logger.info(f"Still processing... (attempt {attempt + 1}/30)")
                continue
            else:
                logger.error(f"Unexpected status: {get_result.get('status')}")
                return None

        logger.error("Captcha solving timeout")
        return None

    except Exception as e:
        logger.error(f"Error solving captcha: {e}")
        return None


def get_access_token(client_id, refresh_token):
    """Get OAuth access token from Microsoft"""
    data = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    try:
        response = session.post('https://login.live.com/oauth20_token.srf', data=data, timeout=10)
        return response.json().get('access_token')
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        return None


def generate_auth_string(user, token):
    """Generate IMAP XOAUTH2 authentication string"""
    return f"user={user}\1auth=Bearer {token}\1\1"


def extract_aws_verification_code(email_address, access_token):
    """Extract AWS 6-digit verification code from email"""
    try:
        mail = imaplib.IMAP4_SSL('outlook.office365.com', timeout=15)
        mail.authenticate('XOAUTH2', lambda x: generate_auth_string(email_address, access_token))
        mail.select("INBOX")

        # Search for AWS emails
        status, messages = mail.search(None, 'FROM "no-reply@signup.aws"')

        if status != 'OK' or not messages[0]:
            mail.logout()
            logger.warning(f"No AWS verification email found for {email_address}")
            return None

        email_ids = messages[0].split()

        # Get the most recent AWS email
        if email_ids:
            last_email_id = email_ids[-1]
            status, msg_data = mail.fetch(last_email_id, '(RFC822)')
            if status == 'OK':
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract HTML content
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/html":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                        elif content_type == "text/plain" and not body:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                if body:
                    # Extract 6-digit verification code - try multiple patterns
                    verification_code = None

                    # Pattern 1: class="x_code" (Outlook web adds x_ prefix)
                    match = re.search(r'class="x_code">(\d{6})<', body)
                    if match:
                        verification_code = match.group(1)

                    # Pattern 2: class="code" (raw email)
                    if not verification_code:
                        match = re.search(r'class="code">(\d{6})<', body)
                        if match:
                            verification_code = match.group(1)

                    # Pattern 3: Look for 6 digits after "Verification code" text
                    if not verification_code:
                        match = re.search(r'Verification code.*?(\d{6})', body, re.DOTALL | re.IGNORECASE)
                        if match:
                            verification_code = match.group(1)

                    # Pattern 4: Look for any 6-digit code (last resort)
                    if not verification_code:
                        match = re.search(r'>\s*(\d{6})\s*<', body)
                        if match:
                            verification_code = match.group(1)

                    if verification_code:
                        logger.success(f"Found AWS verification code: {verification_code}")
                        mail.logout()
                        return verification_code
                    else:
                        logger.warning(f"Could not find verification code in email body")
                        # Debug: print first 500 chars of body
                        logger.debug(f"Email body preview: {body[:500]}")

        mail.logout()
    except Exception as e:
        logger.error(f"Error extracting AWS verification code: {e}")
        return None
    return None


def get_verification_code(email_address, refresh_token, client_id, max_attempts=12):
    """Get AWS verification code from email with retry logic"""
    access_token = get_access_token(client_id, refresh_token)
    if not access_token:
        logger.error(f"Failed to get access token for {email_address}")
        return None

    for attempt in range(max_attempts):
        logger.info(f"Checking email inbox for verification code (attempt {attempt + 1}/{max_attempts})...")
        verification_code = extract_aws_verification_code(email_address, access_token)

        if verification_code:
            return verification_code

        time.sleep(5)

    logger.error(f"No verification code received after {max_attempts * 5} seconds")
    return None


def human_like_type(page, locator, text):
    """Simulate human-like typing with random delays"""
    locator.click()
    time.sleep(random.uniform(0.1, 0.2))

    for char in text:
        locator.type(char)
        time.sleep(random.uniform(0.05, 0.15))


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
    try:
        box = locator.bounding_box()
        if box:
            # Random position within the element
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)

            # Move mouse to element with slight delay
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.2))

            # Click
            page.mouse.click(x, y)
        else:
            # Fallback to regular click
            locator.click()
    except:
        # Final fallback
        locator.click()


def aws_registration_automation(email_address, hotmail_password, refresh_token, client_id,
                                aws_password, card_number, phone_number, runner_id, progress_bar):
    """
    Automates AWS account registration process
    """
    registration_url = "https://signin.aws.amazon.com/signup?request_type=register"

    with sync_playwright() as playwright:
        try:
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
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            stealth_sync(context)
            page = context.new_page()

            # Step 1: Navigate to registration page
            logger.info(f"{runner_id}: Navigating to AWS registration page...")
            page.goto(registration_url, wait_until="domcontentloaded")
            time.sleep(1)

            # Step 2: Enter email address
            logger.info(f"{runner_id}: Entering email: {email_address}...")
            email_input = page.locator('input#emailAddress')
            email_input.wait_for(state="visible", timeout=15000)
            email_input.fill(email_address)
            time.sleep(1)

            # Step 3: Enter account name (username from email)
            account_name = email_address.split('@')[0]
            logger.info(f"{runner_id}: Entering account name: {account_name}...")
            account_name_input = page.locator('input#accountName')
            account_name_input.wait_for(state="visible", timeout=10000)
            account_name_input.fill(account_name)
            time.sleep(0.5)

            # Step 4: Click "Verify email address" button
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

            # Step 5: Handle AWS Security Verification (iframe-based captcha)
            logger.info(f"{runner_id}: Waiting for security verification iframe (appears automatically)...")

            # Find and switch to the iframe (no need to click Verify - iframe appears automatically)
            logger.info(f"{runner_id}: Looking for captcha iframe...")
            try:
                # Wait for iframe to load
                iframe_element = page.locator('iframe#core-container, iframe[title="iframe"]').first
                iframe_element.wait_for(state="attached", timeout=20000)
                time.sleep(2)

                # Get the iframe
                iframe = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
                logger.info(f"{runner_id}: Found captcha iframe")

                # Retry loop for captcha solving (up to 5 attempts)
                max_captcha_attempts = 5
                captcha_solved = False

                for attempt in range(1, max_captcha_attempts + 1):
                    logger.info(f"{runner_id}: Captcha attempt {attempt}/{max_captcha_attempts}")

                    try:
                        # Wait for captcha image inside iframe
                        logger.info(f"{runner_id}: Waiting for captcha image inside iframe...")
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

                        # Step 6: Enter captcha solution inside iframe
                        logger.info(f"{runner_id}: Entering captcha solution: {captcha_solution}...")
                        captcha_input = iframe.locator('input[name="captchaGuess"], input[placeholder*="verification"], input[placeholder*="answer"]')
                        captcha_input.wait_for(state="visible", timeout=10000)
                        captcha_input.clear()
                        captcha_input.fill(captcha_solution)
                        time.sleep(1)

                        # Step 7: Click Submit button inside iframe
                        logger.info(f"{runner_id}: Clicking Submit button...")
                        submit_button = iframe.locator('button[type="submit"], button:has-text("Submit")').first
                        submit_button.click()
                        time.sleep(2)  # WAIT TIME AFTER CAPTCHA SUBMIT - Change this if needed (in seconds)

                        # Check for error message
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
                            # No error message, captcha was successful
                            logger.success(f"{runner_id}: Captcha solved successfully on attempt {attempt}!")
                            captcha_solved = True
                            time.sleep(0.8)
                            break

                        # If we get here without error, captcha was successful
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
                # Try fallback: look for captcha outside iframe
                logger.info(f"{runner_id}: Trying fallback - looking for captcha outside iframe...")
                try:
                    captcha_img = page.locator('img[alt="captcha"]')
                    captcha_img.wait_for(state="visible", timeout=10000)
                    time.sleep(2)

                    captcha_src = captcha_img.get_attribute("src")
                    logger.info(f"{runner_id}: Captcha image found (fallback): {captcha_src[:100]}...")

                    # Solve captcha
                    captcha_solution = solve_captcha_yescaptcha(captcha_src, page)
                    if not captcha_solution:
                        logger.error(f"{runner_id}: Failed to solve captcha (fallback)")
                        savecreated('failed', f"{email_address} - Failed to solve captcha")
                        browser.close()
                        if progress_bar:
                            progress_bar.update(1)
                        return

                    # Enter captcha solution
                    logger.info(f"{runner_id}: Entering captcha solution (fallback): {captcha_solution}...")
                    captcha_input = page.locator('input[name="captchaGuess"]')
                    captcha_input.wait_for(state="visible", timeout=10000)
                    captcha_input.fill(captcha_solution)
                    time.sleep(1)

                    # Click Submit button
                    logger.info(f"{runner_id}: Clicking Submit button (fallback)...")
                    submit_button = page.locator('button[type="submit"]').filter(has_text="Submit")
                    submit_button.click()
                    time.sleep(2)
                except Exception as fallback_error:
                    logger.error(f"{runner_id}: Fallback also failed: {fallback_error}")
                    savecreated('failed', f"{email_address} - Could not handle captcha")
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return

            # Step 8: Get verification code from email
            logger.info(f"{runner_id}: Waiting for verification code email...")
            verification_code = get_verification_code(email_address, refresh_token, client_id)

            if not verification_code:
                logger.error(f"{runner_id}: No verification code received")
                savecreated('failed', f"{email_address} - No verification code")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 9: Enter verification code
            logger.info(f"{runner_id}: Entering verification code: {verification_code}...")
            otp_input = page.locator('input#otp')
            otp_input.wait_for(state="visible", timeout=15000)
            otp_input.fill(verification_code)
            time.sleep(0.5)

            # Click Verify button (after OTP) with error alert handling
            logger.info(f"{runner_id}: Clicking Verify button after OTP...")
            verify_button_otp = page.locator('button[data-testid="verify-email-submit-button"]')
            verify_button_otp.wait_for(state="visible", timeout=10000)
            verify_button_otp.click()
            time.sleep(0.8)

            # Check for error alert and retry if needed
            if not check_and_handle_error_alert(page, verify_button_otp, "Verify button", runner_id):
                logger.error(f"{runner_id}: Failed to verify OTP after retries")
                savecreated('failed', f"{email_address} - OTP verification failed with error alert")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            time.sleep(1.5)

            # Step 10: Set password
            logger.info(f"{runner_id}: Setting password...")
            password_input = page.locator('input#password')
            password_input.wait_for(state="visible", timeout=15000)
            password_input.fill(aws_password)
            time.sleep(0.5)

            # Re-enter password
            re_password_input = page.locator('input#rePassword')
            re_password_input.fill(aws_password)
            time.sleep(0.5)

            # Click "Continue (step 1 of 5)" button
            logger.info(f"{runner_id}: Clicking Continue (step 1 of 5)...")
            continue_step1_button = page.locator('button[data-testid="create-password-submit-button"]')
            continue_step1_button.click()
            time.sleep(2)

            # NEW STEP: Choose account plan (Free plan for 6 months trial)
            logger.info(f"{runner_id}: Choosing account plan...")
            try:
                # Wait for account plan page to appear
                free_plan_button = page.locator('button:has-text("Choose free plan")')
                free_plan_button.wait_for(state="visible", timeout=15000)
                logger.info(f"{runner_id}: Clicking 'Choose free plan' button...")
                free_plan_button.click()
                time.sleep(1)
                logger.success(f"{runner_id}: Free plan selected")
            except Exception as e:
                logger.warning(f"{runner_id}: Could not find account plan selection, may have been skipped: {e}")

            # Step 11: Select account type (Personal)
            logger.info(f"{runner_id}: Selecting Personal account type...")
            personal_radio = page.locator('input[name="accountType"][value="Personal"]')
            personal_radio.wait_for(state="visible", timeout=15000)
            personal_radio.click()
            time.sleep(0.5)

            # Step 12: Select phone code (Mozambique +258)
            logger.info(f"{runner_id}: Selecting phone code +258 (Mozambique)...")
            phone_code_button = page.locator('button#address\\.phoneCode')
            phone_code_button.wait_for(state="visible", timeout=10000)
            phone_code_button.click()
            time.sleep(1)

            # Search for Mozambique
            search_input = page.locator('input[role="combobox"]').first
            search_input.fill("Mozambique")
            time.sleep(1)

            # Select Mozambique option
            mozambique_option = page.locator('span:has-text("+258")').first
            mozambique_option.click()
            time.sleep(1)

            # Step 13: Fill full name (random 12 characters)
            full_name = generate_random_string(12)
            logger.info(f"{runner_id}: Entering full name: {full_name}...")
            full_name_input = page.locator('input#address\\.fullName')
            full_name_input.wait_for(state="visible", timeout=10000)
            full_name_input.fill(full_name)
            time.sleep(0.5)

            # Step 14: Enter phone number (using configuration)
            logger.info(f"{runner_id}: Entering phone number: {PHONE_NUMBER}...")
            phone_input = page.locator('input#address\\.phoneNumber')
            phone_input.fill(PHONE_NUMBER)
            time.sleep(0.5)

            # Step 15: Select country (using configuration)
            logger.info(f"{runner_id}: Selecting country {COUNTRY_NAME}...")
            try:
                # Click country dropdown button
                country_button = page.locator('button#address\\.country')
                country_button.wait_for(state="visible", timeout=10000)
                logger.info(f"{runner_id}: Clicking country dropdown...")
                country_button.click()
                time.sleep(0.6)

                # Type country name directly in the search input
                logger.info(f"{runner_id}: Typing {COUNTRY_NAME} in search...")
                country_search = page.locator('input[role="combobox"]').last  # Use .last to get the country search
                country_search.wait_for(state="visible", timeout=10000)
                time.sleep(0.3)
                country_search.fill(COUNTRY_NAME)
                time.sleep(0.6)

                # Select country from the dropdown options
                logger.info(f"{runner_id}: Selecting {COUNTRY_NAME} from list...")
                country_option = page.locator(f'[role="option"]:has-text("{COUNTRY_NAME}")').first
                country_option.wait_for(state="visible", timeout=10000)
                country_option.click()
                time.sleep(0.5)
                logger.success(f"{runner_id}: Country set to {COUNTRY_NAME}")
            except Exception as e:
                logger.error(f"{runner_id}: Error selecting country: {e}")
                # Take a screenshot for debugging
                try:
                    page.screenshot(path=f"country_error_{runner_id}.png")
                    logger.info(f"{runner_id}: Screenshot saved to country_error_{runner_id}.png")
                except:
                    pass
                raise  # Re-raise to stop execution

            # Step 16: Fill address line 1 (using configuration)
            logger.info(f"{runner_id}: Entering address...")
            address_input = page.locator('input#address\\.addressLine1')
            address_input.fill(ADDRESS_LINE)
            time.sleep(0.5)

            # Step 17: Fill city (using configuration)
            city_input = page.locator('input#address\\.city')
            city_input.fill(CITY)
            time.sleep(0.5)

            # Step 18: Fill state
            state_input = page.locator('input#address\\.state')
            state_input.fill(CITY)  # Using city as state for simplicity
            time.sleep(0.5)

            # Step 19: Fill postal code (using configuration)
            postal_input = page.locator('input#address\\.postalCode')
            postal_input.fill(POSTAL_CODE)
            time.sleep(0.5)

            # Step 20: Check AWS Customer Agreement checkbox
            logger.info(f"{runner_id}: Checking AWS Customer Agreement...")
            agreement_checkbox = page.locator('input#agreement')
            agreement_checkbox.check()
            time.sleep(0.5)

            # Step 21: Click "Agree and Continue (step 2 of 5)"
            logger.info(f"{runner_id}: Clicking Agree and Continue (step 2 of 5)...")
            agree_button = page.locator('button[data-testid="contact-information-submit-button"]')
            agree_button.click()
            time.sleep(2)

            # Save account after step 2 completion (with full hotmail details)
            logger.success(f"{runner_id}: Account created! Saving to created.txt...")
            savecreated('created', f"{email_address}:{hotmail_password}:{refresh_token}:{client_id}:{aws_password}")

            # Step 22: Fill card number
            logger.info(f"{runner_id}: Entering card number: {card_number}...")
            card_input = page.locator('input#cardNumber')
            card_input.wait_for(state="visible", timeout=15000)
            card_input.fill(card_number)
            time.sleep(0.5)

            # Step 23: Select expiration month (random)
            logger.info(f"{runner_id}: Selecting expiration month...")
            month_button = page.locator('button#expirationMonth')
            month_button.wait_for(state="visible", timeout=10000)
            month_button.click()
            time.sleep(0.8)

            # Wait for month dropdown to open and select month (May)
            logger.info(f"{runner_id}: Waiting for month dropdown to open...")
            month_dropdown = page.locator('div.awsui_dropdown_qwoo0_8ly6o_153[aria-hidden="false"]').first
            month_dropdown.wait_for(state="visible", timeout=10000)
            time.sleep(0.5)

            # Select May as the expiry month
            month_option = page.locator('[role="option"]:has-text("May")').first
            month_option.wait_for(state="visible", timeout=10000)
            month_option.click()
            time.sleep(0.5)

            # Step 24: Select expiration year (2027)
            logger.info(f"{runner_id}: Selecting expiration year 2027...")
            year_button = page.locator('button#expirationYear')
            year_button.wait_for(state="visible", timeout=10000)
            year_button.click()
            time.sleep(0.8)

            # Wait for year dropdown to open and select year 2027
            logger.info(f"{runner_id}: Waiting for year dropdown to open...")
            year_dropdown = page.locator('div.awsui_dropdown_qwoo0_8ly6o_153[aria-hidden="false"]').first
            year_dropdown.wait_for(state="visible", timeout=10000)
            time.sleep(0.5)

            year_option = page.locator('[role="option"]:has-text("2027")').first
            year_option.wait_for(state="visible", timeout=10000)
            year_option.click()
            time.sleep(0.5)

            # Step 25: Enter CVV (random 3 digits)
            cvv = generate_random_numbers(3)
            logger.info(f"{runner_id}: Entering CVV: {cvv}...")
            cvv_input = page.locator('input#sor\\.cvv')
            cvv_input.fill(cvv)
            time.sleep(0.5)

            # Step 26: Enter account holder name (random 12 characters)
            holder_name = generate_random_string(12)
            logger.info(f"{runner_id}: Entering account holder name: {holder_name}...")
            holder_input = page.locator('input#accountHolderName')
            holder_input.fill(holder_name)
            time.sleep(0.5)

            # Step 27: Click "Verify and continue (step 3 of 5)"
            logger.info(f"{runner_id}: Clicking Verify and continue (step 3 of 5)...")
            verify_payment_button = page.locator('button[data-testid="payment-information-submit-button"]')
            verify_payment_button.click()
            time.sleep(2)

            # Step 28: Phone verification - select country Mozambique (+258)
            logger.info(f"{runner_id}: Selecting phone verification country Mozambique (+258)...")
            phone_country_button = page.locator('button#country')
            phone_country_button.wait_for(state="visible", timeout=15000)
            phone_country_button.click()
            time.sleep(1)

            # Search for Mozambique
            phone_country_search = page.locator('input[role="combobox"]').first
            phone_country_search.fill("Mozambique")
            time.sleep(1)

            # Select Mozambique
            mozambique_phone = page.locator('[role="option"]:has-text("Mozambique")').first
            mozambique_phone.click()
            time.sleep(1)

            # Step 29: Enter phone number from numbers.txt
            logger.info(f"{runner_id}: Entering phone number: {phone_number}...")
            verification_phone_input = page.locator('input#phoneNumber')
            verification_phone_input.fill(phone_number)
            time.sleep(1)

            # Step 30: Click "Send SMS (step 4 of 5)"
            logger.info(f"{runner_id}: Clicking Send SMS (step 4 of 5)...")
            send_sms_button = page.locator('button[type="submit"]').filter(has_text="Send SMS")
            send_sms_button.click()
            time.sleep(1)

            # Step 31: Solve second captcha (iframe-based) with retry logic
            logger.info(f"{runner_id}: Waiting for second captcha iframe (appears automatically)...")

            # Handle second captcha with iframe
            try:
                # Wait for iframe modal
                logger.info(f"{runner_id}: Looking for second captcha iframe...")
                iframe_element2 = page.locator('iframe#core-container, iframe[title="iframe"]').first
                iframe_element2.wait_for(state="attached", timeout=15000)
                time.sleep(2)

                # Get the iframe
                iframe2 = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
                logger.info(f"{runner_id}: Found second captcha iframe")

                # Retry loop for second captcha (up to 5 attempts)
                max_captcha_attempts2 = 5
                captcha_solved2 = False

                for attempt in range(1, max_captcha_attempts2 + 1):
                    logger.info(f"{runner_id}: Second captcha attempt {attempt}/{max_captcha_attempts2}")

                    try:
                        # Wait for captcha image inside iframe
                        captcha_img2 = iframe2.locator('img[alt="captcha"]')
                        captcha_img2.wait_for(state="visible", timeout=20000)
                        time.sleep(0.8)

                        captcha_src2 = captcha_img2.get_attribute("src")
                        logger.info(f"{runner_id}: Second captcha found...")

                        # Solve captcha
                        captcha_solution2 = solve_captcha_yescaptcha(captcha_src2, page)
                        if not captcha_solution2:
                            logger.error(f"{runner_id}: Failed to solve second captcha on attempt {attempt}")
                            if attempt < max_captcha_attempts2:
                                time.sleep(0.8)
                                continue
                            else:
                                logger.warning(f"{runner_id}: Could not solve second captcha, continuing anyway...")
                                break

                        # Enter captcha solution inside iframe
                        logger.info(f"{runner_id}: Entering second captcha solution: {captcha_solution2}...")
                        captcha_input2 = iframe2.locator('input[name="captchaGuess"], input[placeholder*="verification"], input[placeholder*="answer"]')
                        captcha_input2.clear()
                        captcha_input2.fill(captcha_solution2)
                        time.sleep(1)

                        # Click Submit inside iframe
                        logger.info(f"{runner_id}: Clicking Submit...")
                        submit_captcha_button = iframe2.locator('button[type="submit"], button:has-text("Submit")').first
                        submit_captcha_button.click()
                        time.sleep(2)  # WAIT TIME AFTER CAPTCHA SUBMIT - Change this if needed (in seconds)

                        # Check for error message
                        try:
                            error_message2 = iframe2.locator('div.awsui_error_1i0s3_1goap_185, div[id*="form-error"]:has-text("wasn\'t quite right")').first
                            if error_message2.is_visible(timeout=3000):
                                error_text2 = error_message2.inner_text()
                                logger.warning(f"{runner_id}: Second captcha error on attempt {attempt}: {error_text2}")
                                if attempt < max_captcha_attempts2:
                                    time.sleep(0.8)
                                    continue
                                else:
                                    logger.warning(f"{runner_id}: Second captcha failed after {max_captcha_attempts2} attempts, continuing...")
                                    break
                        except:
                            # No error message, captcha was successful
                            logger.success(f"{runner_id}: Second captcha solved successfully on attempt {attempt}!")
                            captcha_solved2 = True
                            time.sleep(0.8)
                            break

                        # If we get here without error, captcha was successful
                        captcha_solved2 = True
                        break

                    except Exception as e:
                        logger.error(f"{runner_id}: Error on second captcha attempt {attempt}: {e}")
                        if attempt < max_captcha_attempts2:
                            time.sleep(0.8)
                            continue
                        else:
                            logger.warning(f"{runner_id}: Second captcha failed, continuing anyway...")
                            break

            except Exception as e:
                logger.error(f"{runner_id}: Error handling second iframe captcha: {e}")
                # Fallback: try without iframe
                logger.info(f"{runner_id}: Trying second captcha fallback...")
                try:
                    captcha_img2 = page.locator('img[alt="captcha"]')
                    captcha_img2.wait_for(state="visible", timeout=10000)
                    time.sleep(2)

                    captcha_src2 = captcha_img2.get_attribute("src")
                    logger.info(f"{runner_id}: Second captcha found (fallback)...")

                    captcha_solution2 = solve_captcha_yescaptcha(captcha_src2, page)
                    if captcha_solution2:
                        captcha_input2 = page.locator('input[name="captchaGuess"]')
                        captcha_input2.fill(captcha_solution2)
                        time.sleep(1)

                        submit_captcha_button = page.locator('button[type="submit"]').filter(has_text="Submit")
                        submit_captcha_button.click()
                        time.sleep(1)
                    else:
                        logger.warning(f"{runner_id}: Second captcha solve failed (fallback)")
                except Exception as fallback_error:
                    logger.warning(f"{runner_id}: Second captcha fallback also failed: {fallback_error}")
                    # Continue anyway - may not always need captcha

            # Step 32: Retry loop (3 times total)
            logger.info(f"{runner_id}: Starting retry loop (3 attempts)...")
            for retry in range(3):
                logger.info(f"{runner_id}: === Retry {retry + 1}/3 ===")

                # Refresh the page
                logger.info(f"{runner_id}: Refreshing page...")
                page.reload(wait_until="domcontentloaded")
                time.sleep(1)

                # Re-select country
                try:
                    phone_country_button2 = page.locator('button#country')
                    phone_country_button2.wait_for(state="visible", timeout=10000)
                    phone_country_button2.click()
                    time.sleep(1)

                    phone_country_search2 = page.locator('input[role="combobox"]').first
                    phone_country_search2.fill("Mozambique")
                    time.sleep(1)

                    mozambique_phone2 = page.locator('[role="option"]:has-text("Mozambique")').first
                    mozambique_phone2.click()
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"{runner_id}: Error selecting country on retry {retry + 1}: {e}")

                # Re-enter phone number
                try:
                    verification_phone_input2 = page.locator('input#phoneNumber')
                    verification_phone_input2.fill(phone_number)
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"{runner_id}: Error entering phone on retry {retry + 1}: {e}")

                # Click Send SMS again
                try:
                    send_sms_button2 = page.locator('button[type="submit"]').filter(has_text="Send SMS")
                    send_sms_button2.click()
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"{runner_id}: Error clicking Send SMS on retry {retry + 1}: {e}")

                # Solve captcha again if it appears (iframe-based, with retry logic)
                try:
                    # Try iframe captcha
                    iframe_retry = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
                    captcha_img3 = iframe_retry.locator('img[alt="captcha"]')

                    if captcha_img3.is_visible(timeout=5000):
                        # Retry loop for retry captcha (up to 3 attempts)
                        for captcha_retry_attempt in range(1, 4):
                            logger.info(f"{runner_id}: Retry {retry + 1} - Captcha attempt {captcha_retry_attempt}/3")

                            try:
                                captcha_src3 = captcha_img3.get_attribute("src")
                                captcha_solution3 = solve_captcha_yescaptcha(captcha_src3, page)

                                if captcha_solution3:
                                    captcha_input3 = iframe_retry.locator('input[name="captchaGuess"], input[placeholder*="verification"]')
                                    captcha_input3.clear()
                                    captcha_input3.fill(captcha_solution3)
                                    time.sleep(1)

                                    submit_button3 = iframe_retry.locator('button[type="submit"], button:has-text("Submit")').first
                                    submit_button3.click()
                                    time.sleep(1)

                                    # Check for error
                                    try:
                                        error_msg3 = iframe_retry.locator('div.awsui_error_1i0s3_1goap_185, div[id*="form-error"]:has-text("wasn\'t quite right")').first
                                        if error_msg3.is_visible(timeout=2000):
                                            logger.warning(f"{runner_id}: Retry captcha error on attempt {captcha_retry_attempt}")
                                            if captcha_retry_attempt < 3:
                                                time.sleep(0.8)
                                                # Reload captcha image
                                                captcha_img3 = iframe_retry.locator('img[alt="captcha"]')
                                                continue
                                            else:
                                                logger.warning(f"{runner_id}: Retry captcha failed after 3 attempts")
                                                break
                                    except:
                                        logger.success(f"{runner_id}: Retry captcha solved on attempt {captcha_retry_attempt}!")
                                        break

                                    break
                            except Exception as e:
                                logger.warning(f"{runner_id}: Error on retry captcha attempt {captcha_retry_attempt}: {e}")
                                if captcha_retry_attempt < 3:
                                    time.sleep(0.8)
                                    continue
                                else:
                                    break
                except Exception as iframe_error:
                    # Fallback to non-iframe
                    try:
                        captcha_img3 = page.locator('img[alt="captcha"]')
                        if captcha_img3.is_visible(timeout=3000):
                            captcha_src3 = captcha_img3.get_attribute("src")
                            captcha_solution3 = solve_captcha_yescaptcha(captcha_src3, page)

                            if captcha_solution3:
                                captcha_input3 = page.locator('input[name="captchaGuess"]')
                                captcha_input3.clear()
                                captcha_input3.fill(captcha_solution3)
                                time.sleep(1)

                                submit_button3 = page.locator('button[type="submit"]').filter(has_text="Submit")
                                submit_button3.click()
                                time.sleep(1)
                    except Exception as e:
                        logger.info(f"{runner_id}: No captcha on retry {retry + 1} or error: {e}")

            logger.success(f"{runner_id}: AWS automation completed successfully!")
            logger.info(f"{runner_id}: Closing browser...")

            time.sleep(2)
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('failed', f"{email_address} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, account_data, aws_password, card_number, phone_number, progress_bar):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"

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

    logger.info(f"{runner_id}: Starting AWS registration for {email_address}")
    aws_registration_automation(email_address, hotmail_password, refresh_token, client_id,
                                aws_password, card_number, phone_number, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("AWS Account Registration Automation Script")
    logger.info("=" * 50)

    # Load accounts from file (format: email:hotmail_password:refresh_token:client_id)
    try:
        with open("accounts.txt", "r", encoding="utf8") as file:
            accounts = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(accounts)} accounts from accounts.txt")
    except FileNotFoundError:
        logger.error("'accounts.txt' not found. Create a file with format: email:hotmail_password:refresh_token:client_id")
        exit(1)

    # Load AWS password from file
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            aws_password = file.read().strip()
        logger.info(f"AWS Password: {'*' * len(aws_password)}")
    except FileNotFoundError:
        logger.error("'password.txt' not found. Create a file with AWS password")
        exit(1)

    # Load card numbers from file
    try:
        with open("cards.txt", "r", encoding="utf8") as file:
            cards = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(cards)} cards from cards.txt")
    except FileNotFoundError:
        logger.error("'cards.txt' not found. Create a file with card numbers (one per line)")
        exit(1)

    # Load phone numbers from file
    try:
        with open("numbers.txt", "r", encoding="utf8") as file:
            phone_numbers = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(phone_numbers)} phone numbers from numbers.txt")
    except FileNotFoundError:
        logger.error("'numbers.txt' not found. Create a file with phone numbers (one per line)")
        exit(1)

    if len(accounts) == 0:
        logger.error("No accounts loaded. Please add accounts to accounts.txt")
        exit(1)

    if len(cards) == 0:
        logger.error("No cards loaded. Please add cards to cards.txt")
        exit(1)

    if len(phone_numbers) == 0:
        logger.error("No phone numbers loaded. Please add numbers to numbers.txt")
        exit(1)

    # Create tasks (pair accounts with cards and phone numbers)
    tasks = []
    for i, account in enumerate(accounts):
        card = cards[i % len(cards)]
        phone = phone_numbers[i % len(phone_numbers)]
        tasks.append((i, account, aws_password, card, phone))

    logger.info(f"Created {len(tasks)} tasks")

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(tasks), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda task: run_worker(task[0], task[1], task[2], task[3], task[4], progress_bar), tasks)

    logger.success("Script finished!")
    input('Press Enter to exit...')
