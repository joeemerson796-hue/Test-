import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration
MAX_WORKERS = 1  # Run one at a time for stability
HEADLESS = False  # Set to True to hide browser

# File paths
NAMES_FILE = "names.txt"
ACCOUNTS_FILE = "accounts.txt"
PASSWORD_FILE = "password.txt"
NUMBERS_FILE = "numbers.txt"

# Thread lock for file operations
file_lock = threading.Lock()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

def clear_console():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_file_lines(filepath):
    """Read all non-empty lines from a file"""
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return []

    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            return lines
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return []

def read_password():
    """Read the password from password.txt"""
    passwords = read_file_lines(PASSWORD_FILE)
    if not passwords:
        logger.error(f"No password found in {PASSWORD_FILE}")
        return None
    return passwords[0]

def remove_line_from_file(filepath, line_to_remove):
    """Remove a specific line from a file"""
    with file_lock:
        try:
            if not os.path.exists(filepath):
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            with open(filepath, 'w', encoding='utf-8') as f:
                for line in lines:
                    if line.strip() != line_to_remove.strip():
                        f.write(line)

            logger.info(f"Removed from {filepath}: {line_to_remove}")
        except Exception as e:
            logger.error(f"Error removing line from {filepath}: {e}")

def process_paypal_signup(account_email, full_name, phone_number, password):
    """Process a single PayPal business account signup"""

    # Parse full name
    name_parts = full_name.split(' ', 1)
    if len(name_parts) < 2:
        logger.error(f"Invalid name format: {full_name}. Expected 'FirstName LastName'")
        return False

    first_name = name_parts[0]
    last_name = name_parts[1]

    logger.info("=" * 60)
    logger.info(f"Processing: {account_email}")
    logger.info(f"Name: {first_name} {last_name}")
    logger.info(f"Phone: {phone_number}")
    logger.info("=" * 60)

    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            # Step 1: Go to PayPal ZA home page
            logger.info("Opening PayPal home page...")
            page.goto("https://www.paypal.com/za/home", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)

            # Step 2: Click Sign Up
            logger.info("Clicking Sign Up...")
            try:
                signup_button = page.locator('a[id="_signup-button_ye2x1_1"]')
                signup_button.wait_for(state="visible", timeout=10000)
                signup_button.click()
                page.wait_for_timeout(3000)
            except:
                logger.warning("Signup button not found with ID, trying alternative...")
                signup_button = page.locator('a:has-text("Sign Up")').first
                signup_button.click()
                page.wait_for_timeout(3000)

            # Step 3: Choose Business account
            logger.info("Selecting Business account type...")
            try:
                business_radio = page.locator('input[id="account-selection-Business"]')
                business_radio.wait_for(state="visible", timeout=10000)
                business_radio.click()
                page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"Error selecting Business account: {e}")

            # Step 4: Click Get Started
            logger.info("Clicking Get Started...")
            try:
                get_started_btn = page.get_by_role("link", name="Get a Business Account").first
                get_started_btn.wait_for(state="visible", timeout=10000)
                get_started_btn.click()
                page.wait_for_timeout(5000)
            except Exception as e:
                logger.error(f"Error clicking Get Started: {e}")
                browser.close()
                return False

            # Step 5: Fill in first name
            logger.info(f"Entering first name: {first_name}")
            try:
                first_name_input = page.locator('input[name="personName-givenName"]')
                first_name_input.wait_for(state="visible", timeout=15000)
                first_name_input.fill(first_name)
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Error entering first name: {e}")
                browser.close()
                return False

            # Step 6: Fill in last name
            logger.info(f"Entering last name: {last_name}")
            try:
                last_name_input = page.locator('input[name="personName-surname"]')
                last_name_input.fill(last_name)
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Error entering last name: {e}")
                browser.close()
                return False

            # Step 7: Fill in email
            logger.info(f"Entering email: {account_email}")
            try:
                email_input = page.locator('input[name="email"]')
                email_input.fill(account_email)
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Error entering email: {e}")
                browser.close()
                return False

            # Step 8: Fill in password
            logger.info("Entering password...")
            try:
                password_input = page.locator('input[name="password"]')
                password_input.fill(password)
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Error entering password: {e}")
                browser.close()
                return False

            # Step 9: Select country code ZA +27
            logger.info("Selecting country code ZA +27...")
            try:
                # Click dropdown button
                dropdown_button = page.locator('button[id="dropdownMenuButton_individualHomePhoneNumberDropdownMenu"]')
                dropdown_button.click()
                page.wait_for_timeout(1000)

                # Select ZA +27
                za_option = page.locator('div[data-value="ZA_27"]')
                za_option.click()
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"Error selecting country code (may already be ZA): {e}")

            # Step 10: Fill in phone number
            logger.info(f"Entering phone number: {phone_number}")
            try:
                phone_input = page.locator('input[name="individualHomePhoneNumber"]')
                phone_input.fill(phone_number)
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Error entering phone number: {e}")
                browser.close()
                return False

            # Step 11: Click agree checkbox
            logger.info("Clicking agree checkbox...")
            try:
                agree_checkbox = page.locator('span._10hpw4g2').first
                agree_checkbox.click()
                page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Error clicking agree checkbox: {e}")

            # Step 12: Click "Agree and Create Account"
            logger.info("Clicking 'Agree and Create Account'...")
            try:
                create_btn = page.locator('button[data-test-id="createAccountButton"]')
                create_btn.wait_for(state="visible", timeout=5000)
                create_btn.click()
                page.wait_for_timeout(5000)
            except Exception as e:
                logger.error(f"Error clicking create account: {e}")
                browser.close()
                return False

            # Step 13: Handle security challenge if it appears
            logger.info("Checking for security challenge...")
            try:
                challenge_checkbox = page.locator('div[id="checkbox"][role="checkbox"]')
                if challenge_checkbox.is_visible(timeout=5000):
                    logger.warning("Security challenge detected! Clicking checkbox...")
                    challenge_checkbox.click()
                    page.wait_for_timeout(3000)
            except:
                logger.info("No security challenge detected")

            # Step 14: Wait for verification page and click "Text You a Code"
            logger.info("Waiting for verification page...")
            try:
                text_code_btn = page.locator('button.addPhoneNumberButton:has-text("Text You a Code")')
                text_code_btn.wait_for(state="visible", timeout=20000)
                text_code_btn.click()
                page.wait_for_timeout(3000)
                logger.info("Clicked 'Text You a Code'")
            except Exception as e:
                logger.error(f"Error clicking 'Text You a Code': {e}")

            # Step 15: Click "Send New Code" repeatedly until alert appears
            logger.info("Clicking 'Send New Code' repeatedly...")
            send_count = 0
            max_attempts = 50

            while send_count < max_attempts:
                try:
                    # Check for critical alert
                    alert_icon = page.locator('span[aria-label="critical icon"][data-test-id="dialogIcon"]')
                    if alert_icon.is_visible(timeout=1000):
                        logger.success("Critical alert appeared! Stopping...")
                        break

                    # Click Send New Code
                    send_new_code = page.locator('a.resend[data-nemo="resendLink"]:has-text("Send New Code")')
                    if send_new_code.is_visible(timeout=2000):
                        send_new_code.click()
                        send_count += 1
                        logger.info(f"Clicked 'Send New Code' #{send_count}")
                        page.wait_for_timeout(2000)
                    else:
                        logger.warning("Send New Code button not clickable")
                        page.wait_for_timeout(2000)

                except Exception as e:
                    logger.info(f"Checking for alert... (attempt {send_count})")
                    page.wait_for_timeout(2000)

                    # Final check for alert
                    try:
                        alert_icon = page.locator('span[aria-label="critical icon"][data-test-id="dialogIcon"]')
                        if alert_icon.is_visible(timeout=1000):
                            logger.success("Critical alert appeared! Stopping...")
                            break
                    except:
                        pass

            logger.success(f"Finished processing {account_email}")
            logger.info(f"Total 'Send New Code' clicks: {send_count}")

            # Close browser
            page.wait_for_timeout(2000)
            browser.close()

            # Remove used account and phone number from files
            remove_line_from_file(ACCOUNTS_FILE, account_email)
            remove_line_from_file(NAMES_FILE, full_name)
            remove_line_from_file(NUMBERS_FILE, phone_number)

            return True

    except Exception as e:
        logger.error(f"Error processing {account_email}: {e}")
        return False

def main():
    """Main function to run PayPal automation"""
    clear_console()

    logger.info("PayPal Business Account Creation Automation - V1")
    logger.info("=" * 60)

    # Read all required files
    accounts = read_file_lines(ACCOUNTS_FILE)
    names = read_file_lines(NAMES_FILE)
    numbers = read_file_lines(NUMBERS_FILE)
    password = read_password()

    if not accounts:
        logger.error(f"No accounts found in {ACCOUNTS_FILE}")
        return

    if not names:
        logger.error(f"No names found in {NAMES_FILE}")
        return

    if not numbers:
        logger.error(f"No phone numbers found in {NUMBERS_FILE}")
        return

    if not password:
        logger.error(f"No password found in {PASSWORD_FILE}")
        return

    # Check counts
    min_count = min(len(accounts), len(names), len(numbers))
    logger.info(f"Accounts: {len(accounts)} | Names: {len(names)} | Numbers: {len(numbers)}")
    logger.info(f"Will process: {min_count} accounts")
    logger.info("=" * 60)

    # Process accounts sequentially
    success_count = 0
    fail_count = 0

    for i in range(min_count):
        account = accounts[i]
        name = names[i]
        number = numbers[i]

        logger.info(f"\nProcessing account {i+1}/{min_count}")

        result = process_paypal_signup(account, name, number, password)

        if result:
            success_count += 1
        else:
            fail_count += 1

        # Small delay between accounts
        if i < min_count - 1:
            logger.info("Waiting 5 seconds before next account...")
            time.sleep(5)

    # Final summary
    logger.info("=" * 60)
    logger.info("AUTOMATION COMPLETE!")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
