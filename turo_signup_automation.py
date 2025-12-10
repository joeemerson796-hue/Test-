import os
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
from loguru import logger
from threading import Lock
from tqdm import tqdm

# Global locks for thread-safe file operations
file_lock = Lock()
accounts_lock = Lock()
passwords_lock = Lock()
countries_lock = Lock()
numbers_lock = Lock()

# Global data
accounts = []
passwords = []
countries = []
numbers = []
account_index = 0
password_index = 0
country_index = 0
number_index = 0


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def generate_random_name(length=10):
    """Generate random string of specified length"""
    return ''.join(random.choices(string.ascii_letters, k=length))


def get_next_account():
    """Get next account from the pool in a thread-safe manner"""
    global account_index, accounts, accounts_lock
    with accounts_lock:
        if account_index >= len(accounts):
            return None
        account = accounts[account_index]
        account_index += 1
        return account


def get_next_password():
    """Get next password from the pool in a thread-safe manner"""
    global password_index, passwords, passwords_lock
    with passwords_lock:
        if password_index >= len(passwords):
            password_index = 0  # Loop back to start
        password = passwords[password_index]
        password_index += 1
        return password


def get_next_country():
    """Get next country from the pool in a thread-safe manner"""
    global country_index, countries, countries_lock
    with countries_lock:
        if country_index >= len(countries):
            country_index = 0  # Loop back to start
        country = countries[country_index]
        country_index += 1
        return country


def get_next_number():
    """Get next number from the pool in a thread-safe manner"""
    global number_index, numbers, numbers_lock
    with numbers_lock:
        if number_index >= len(numbers):
            return None
        number = numbers[number_index]
        number_index += 1
        return number


def remove_number_from_file(number):
    """Remove a phone number from numbers.txt file"""
    try:
        with file_lock:
            with open("numbers.txt", "r", encoding="utf8") as file:
                lines = file.readlines()
            with open("numbers.txt", "w", encoding="utf8") as file:
                for line in lines:
                    if line.strip() != number:
                        file.write(line)
            logger.info(f"Removed number {number} from numbers.txt")
    except Exception as e:
        logger.error(f"Error removing number from file: {e}")


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
    try:
        # Get element bounding box
        box = locator.bounding_box()
        if box:
            # Random position within the element
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)

            # Move mouse to element with slight delay
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))

            # Click
            page.mouse.click(x, y)
        else:
            # Fallback to regular click
            locator.click()
    except:
        # Fallback to regular click
        locator.click()


def turo_signup_automation(email, password, country, phone_number, runner_id, progress_bar):
    """
    Automates Turo signup process
    """
    signup_url = "https://turo.com/us/en/sign-up/email?next=%2Fus%2Fen%2Fdrivers%2F52266563"
    phone_url = "https://turo.com/us/en/account/change-phone-number?next=/us/en/account"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)  # True False Headless mode - no visible browser
            context = browser.new_context()
            stealth_sync(context)
            page = context.new_page()

            # Step 1: Navigate to signup page
            logger.info(f"{runner_id}: Navigating to Turo signup page...")
            page.goto(signup_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 3))

            # Step 2: Click "Continue with email"
            logger.info(f"{runner_id}: Clicking 'Continue with email'...")
            continue_email_btn = page.locator('button:has-text("Continue with email")')
            continue_email_btn.wait_for(state="visible", timeout=15000)
            time.sleep(random.uniform(0.5, 1))

            # Click and wait for navigation
            logger.info(f"{runner_id}: Clicking button and waiting for navigation...")
            human_like_click(page, continue_email_btn)

            # Wait for URL to change to sign-up/email
            page.wait_for_url("**/sign-up/email**", timeout=15000)
            logger.info(f"{runner_id}: Navigated to: {page.url}")
            time.sleep(random.uniform(3, 4))

            # Try to find iframe, if not found use page directly
            logger.info(f"{runner_id}: Looking for form...")
            try:
                # Check if iframe exists
                page.locator('iframe[data-testid="managedIframe"]').wait_for(state="attached", timeout=5000)
                logger.info(f"{runner_id}: Found iframe, using iframe context...")
                context = page.frame_locator('iframe[data-testid="managedIframe"]')
            except:
                logger.info(f"{runner_id}: No iframe found, using page context...")
                context = page

            # Step 3: Fill in first name (10 random characters)
            first_name = generate_random_name(10)
            logger.info(f"{runner_id}: Entering first name: {first_name}...")
            first_name_input = context.locator('input[data-testid="firstName"]')
            first_name_input.wait_for(state="visible", timeout=30000)
            first_name_input.fill(first_name)
            time.sleep(random.uniform(0.5, 1))

            # Step 4: Fill in last name (10 random characters)
            last_name = generate_random_name(10)
            logger.info(f"{runner_id}: Entering last name: {last_name}...")
            last_name_input = context.locator('input[data-testid="lastName"]')
            last_name_input.fill(last_name)
            time.sleep(random.uniform(0.5, 1))

            # Step 5: Fill in email
            logger.info(f"{runner_id}: Entering email: {email}...")
            email_input = context.locator('input[data-testid="email"]')
            email_input.fill(email)
            time.sleep(random.uniform(0.5, 1))

            # Step 6: Fill in password
            logger.info(f"{runner_id}: Entering password...")
            password_input = context.locator('input[data-testid="password"]')
            password_input.fill(password)
            time.sleep(random.uniform(0.5, 1))

            # Step 7: Check TOS checkbox
            logger.info(f"{runner_id}: Checking TOS checkbox...")
            tos_checkbox = context.locator('input[data-testid="tos"]')
            tos_checkbox.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(0.3, 0.7))
            tos_checkbox.check()
            time.sleep(random.uniform(0.5, 1))

            # Step 8: Click signup button
            logger.info(f"{runner_id}: Clicking signup button...")
            signup_button = context.locator('button[data-testid="submitSignupButton"]')
            signup_button.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(0.5, 1))
            signup_button.click()

            # Step 9: Save created account
            logger.success(f"{runner_id}: Account created! Saving to created.txt...")
            savecreated('created', f"{email}:{password}")

            # Step 10: Wait 2 seconds
            logger.info(f"{runner_id}: Waiting 2 seconds...")
            time.sleep(2)

            # Step 11: Navigate to phone change page
            logger.info(f"{runner_id}: Navigating to phone change page...")
            page.goto(phone_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 3))

            # Step 12: Select country
            logger.info(f"{runner_id}: Selecting country: {country}...")
            country_select = page.locator('select[id="countryCode"]')
            country_select.wait_for(state="visible", timeout=15000)
            time.sleep(random.uniform(0.5, 1))
            # Select by text (value attribute is country code, but we match by visible text)
            page.select_option('select[id="countryCode"]', label=country)
            time.sleep(random.uniform(0.5, 1))

            # Step 13: Enter phone number
            logger.info(f"{runner_id}: Entering phone number: {phone_number}...")
            phone_input = page.locator('input[id="phoneNumber"]')
            phone_input.wait_for(state="visible", timeout=10000)
            phone_input.fill(phone_number)
            time.sleep(random.uniform(0.5, 1))

            # Step 14: Click send code button
            logger.info(f"{runner_id}: Clicking send code button...")
            send_code_button = page.locator('button[type="submit"]:has-text("Send code")')
            send_code_button.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(0.5, 1))
            human_like_click(page, send_code_button)
            time.sleep(2)

            # Step 15: Remove used number from file
            logger.info(f"{runner_id}: Removing used number from numbers.txt...")
            remove_number_from_file(phone_number)

            logger.success(f"{runner_id}: Automation completed successfully!")
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('failed', f"{email}:{password} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, progress_bar):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"

    # Get next data from pools
    email = get_next_account()
    if not email:
        logger.warning(f"{runner_id}: No more accounts available")
        if progress_bar:
            progress_bar.update(1)
        return

    password = get_next_password()
    country = get_next_country()
    phone = get_next_number()

    if not phone:
        logger.warning(f"{runner_id}: No more phone numbers available")
        savecreated('failed', f"{email}:{password} - No phone number available")
        if progress_bar:
            progress_bar.update(1)
        return

    logger.info(f"{runner_id}: Starting automation for {email} with phone {phone}")
    turo_signup_automation(email, password, country, phone, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("Turo Signup Automation Script")
    logger.info("=" * 50)

    # Load accounts from file
    try:
        with open("accounts.txt", "r", encoding="utf8") as file:
            accounts = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(accounts)} accounts from accounts.txt")
    except FileNotFoundError:
        logger.error("'accounts.txt' not found. Create a file with email addresses (one per line)")
        exit(1)

    # Load passwords from file
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            passwords = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(passwords)} passwords from password.txt")
    except FileNotFoundError:
        logger.error("'password.txt' not found. Create a file with passwords (one per line)")
        exit(1)

    # Load countries from file
    try:
        with open("country.txt", "r", encoding="utf8") as file:
            countries = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(countries)} countries from country.txt")
    except FileNotFoundError:
        logger.error("'country.txt' not found. Create a file with country names (one per line)")
        exit(1)

    # Load phone numbers from file
    try:
        with open("numbers.txt", "r", encoding="utf8") as file:
            numbers = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(numbers)} phone numbers from numbers.txt")
    except FileNotFoundError:
        logger.error("'numbers.txt' not found. Create a file with phone numbers (one per line)")
        exit(1)

    if len(accounts) == 0:
        logger.error("No accounts loaded. Please add emails to accounts.txt")
        exit(1)

    if len(passwords) == 0:
        logger.error("No passwords loaded. Please add passwords to password.txt")
        exit(1)

    if len(countries) == 0:
        logger.error("No countries loaded. Please add countries to country.txt")
        exit(1)

    if len(numbers) == 0:
        logger.error("No phone numbers loaded. Please add numbers to numbers.txt")
        exit(1)

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, progress_bar), range(len(accounts)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
