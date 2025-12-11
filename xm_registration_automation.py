import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
from loguru import logger
from threading import Lock
from tqdm import tqdm
import xm_email_verifier

# Global lock for thread-safe file operations
file_lock = Lock()
phone_numbers = []
phone_index = 0
phone_lock = Lock()


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    """Save results to file"""
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def get_next_phone():
    """Get next phone number from the pool in a thread-safe manner"""
    global phone_index, phone_numbers, phone_lock

    with phone_lock:
        if phone_index >= len(phone_numbers):
            logger.warning("No more phone numbers available!")
            return None
        phone = phone_numbers[phone_index]
        phone_index += 1
        return phone


def remove_phone_from_file(phone):
    """Remove a phone number from numbers.txt file"""
    try:
        with file_lock:
            with open("numbers.txt", "r", encoding="utf8") as file:
                lines = file.readlines()
            with open("numbers.txt", "w", encoding="utf8") as file:
                for line in lines:
                    if line.strip() != phone:
                        file.write(line)
            logger.info(f"Removed phone {phone} from numbers.txt")
    except Exception as e:
        logger.error(f"Error removing phone from file: {e}")


def human_like_type(element, text, delay_range=(0.05, 0.15)):
    """Type text with human-like delays"""
    for char in text:
        element.type(char)
        time.sleep(random.uniform(*delay_range))


def xm_registration_automation(email_address, password, refresh_token, client_id, country, xm_password, phone_number, runner_id, progress_bar):
    """
    Automates XM registration process
    """
    registration_url = "https://www.xm.com/register/profile-account"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)  # Changed to headless=False for debugging
            context = browser.new_context()
            stealth_sync(context)
            page = context.new_page()

            # Step 1: Navigate to registration page
            logger.info(f"{runner_id}: Navigating to XM registration page...")
            page.goto(registration_url, wait_until="domcontentloaded")
            time.sleep(3)

            # Step 2: Handle "Accept All" cookie button (wait max 5 seconds)
            logger.info(f"{runner_id}: Checking for cookie consent button...")
            try:
                accept_button = page.locator('button:has-text("Accept All")')
                accept_button.wait_for(state="visible", timeout=5000)
                accept_button.click()
                logger.success(f"{runner_id}: Clicked Accept All button")
                time.sleep(2)
            except:
                logger.info(f"{runner_id}: No cookie consent button found, continuing...")

            # Step 3: Select country
            logger.info(f"{runner_id}: Selecting country: {country}...")
            country_input = page.locator('input[placeholder="Country of Residence"]')
            country_input.wait_for(state="visible", timeout=15000)
            country_input.click()
            time.sleep(1)
            country_input.fill(country)
            time.sleep(2)

            # Click on the country option from dropdown
            country_option = page.locator(f'li:has-text("{country}")').first
            country_option.wait_for(state="visible", timeout=10000)
            country_option.click()
            time.sleep(2)

            # Step 4: Enter email
            logger.info(f"{runner_id}: Entering email: {email_address}...")
            email_input = page.locator('input[type="text"][placeholder="Email"]')
            email_input.wait_for(state="visible", timeout=10000)
            email_input.fill(email_address)
            time.sleep(1)

            # Step 5: Enter XM password
            logger.info(f"{runner_id}: Entering password...")
            password_input = page.locator('input[type="password"][placeholder="Password"]')
            password_input.wait_for(state="visible", timeout=10000)
            password_input.fill(xm_password)
            time.sleep(1)

            # Step 6: Click Register button
            logger.info(f"{runner_id}: Clicking Register button...")
            register_button = page.locator('button:has-text("Register")')
            register_button.wait_for(state="visible", timeout=10000)
            register_button.click()
            logger.success(f"{runner_id}: Registration form submitted")
            time.sleep(5)

            # Step 7: Wait for verification email and extract link
            logger.info(f"{runner_id}: Waiting for verification email (max 60 seconds)...")
            verification_link = None
            max_attempts = 12  # 12 * 5 seconds = 60 seconds total

            for attempt in range(max_attempts):
                logger.info(f"{runner_id}: Checking email inbox (attempt {attempt + 1}/{max_attempts})...")
                verification_link = xm_email_verifier.get_verification_link(email_address, refresh_token, client_id)

                if verification_link:
                    logger.success(f"{runner_id}: Verification link found!")
                    break

                time.sleep(5)

            if not verification_link:
                logger.error(f"{runner_id}: No verification email received after 60 seconds")
                savecreated('failed', f"{email_address}:{xm_password} - No verification email")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 8: Open verification link in new tab
            logger.info(f"{runner_id}: Opening verification link...")
            verification_page = context.new_page()
            verification_page.goto(verification_link, wait_until="domcontentloaded")
            time.sleep(3)
            logger.success(f"{runner_id}: Email verified successfully")

            # Save created account
            savecreated('created', f"{email_address}:{xm_password}")
            logger.success(f"{runner_id}: Account saved to created.txt")

            verification_page.close()

            # Step 9: Navigate to phone verification page
            logger.info(f"{runner_id}: Navigating to phone verification page...")
            phone_url = "https://my.xm.com/profile/validate/phone/verify"
            page.goto(phone_url, wait_until="domcontentloaded")
            time.sleep(3)

            # Step 10: Enter phone number
            logger.info(f"{runner_id}: Entering phone number: {phone_number}...")
            phone_input = page.locator('input[type="tel"]')
            phone_input.wait_for(state="visible", timeout=15000)
            phone_input.fill(phone_number)
            time.sleep(2)

            # Step 11: Click "Receive code" button
            logger.info(f"{runner_id}: Clicking Receive code button...")
            receive_code_button = page.locator('button:has-text("Receive code")')
            receive_code_button.wait_for(state="visible", timeout=10000)
            receive_code_button.click()
            logger.success(f"{runner_id}: Phone verification code requested")
            time.sleep(3)

            # Step 12: Remove phone number from file
            remove_phone_from_file(phone_number)

            logger.success(f"{runner_id}: XM automation completed successfully!")
            savecreated('completed', f"{email_address}:{xm_password}:{phone_number}")

            time.sleep(3)
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('failed', f"{email_address}:{xm_password} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, account_data, country, xm_password, progress_bar):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"

    # Parse account data: email:password:refresh_token:client_id
    parts = account_data.split(':')
    if len(parts) < 4:
        logger.error(f"{runner_id}: Invalid account format: {account_data}")
        if progress_bar:
            progress_bar.update(1)
        return

    email_address = parts[0]
    password = parts[1]
    refresh_token = ':'.join(parts[2:-1])  # Handle refresh tokens with colons
    client_id = parts[-1]

    phone = get_next_phone()
    if not phone:
        logger.error(f"{runner_id}: No phone number available for {email_address}")
        savecreated('failed', f"{email_address}:{xm_password} - No phone number available")
        if progress_bar:
            progress_bar.update(1)
        return

    logger.info(f"{runner_id}: Starting XM registration for {email_address} with phone {phone}")
    xm_registration_automation(email_address, password, refresh_token, client_id, country, xm_password, phone, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("XM Registration Automation Script")
    logger.info("=" * 50)

    # Load country from file
    try:
        with open("country.txt", "r", encoding="utf8") as file:
            country = file.read().strip()
        logger.info(f"Country: {country}")
    except FileNotFoundError:
        logger.error("'country.txt' not found. Create a file with country name (e.g., Lebanon)")
        exit(1)

    # Load XM password from file
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            xm_password = file.read().strip()
        logger.info(f"XM Password: {'*' * len(xm_password)}")
    except FileNotFoundError:
        logger.error("'password.txt' not found. Create a file with XM password")
        exit(1)

    # Load accounts from file (format: email:password:refresh_token:client_id)
    try:
        with open("accounts.txt", "r", encoding="utf8") as file:
            accounts = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(accounts)} accounts from accounts.txt")
    except FileNotFoundError:
        logger.error("'accounts.txt' not found. Create a file with format: email:password:refresh_token:client_id")
        exit(1)

    # Load phone numbers from file
    try:
        with open("numbers.txt", "r", encoding="utf8") as file:
            phone_numbers = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(phone_numbers)} phone numbers from numbers.txt")
    except FileNotFoundError:
        logger.error("'numbers.txt' not found. Create a file with phone numbers (one per line)")
        exit(1)

    if len(phone_numbers) == 0:
        logger.error("No phone numbers loaded. Please add numbers to numbers.txt")
        exit(1)

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, accounts[i], country, xm_password, progress_bar), range(len(accounts)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
