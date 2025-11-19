import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
from loguru import logger
from threading import Lock
from tqdm import tqdm

# Global lock for thread-safe file operations
file_lock = Lock()
phone_numbers = []
phone_index = 0
phone_lock = Lock()

# Configuration
NUMBERS_PER_ACCOUNT = 10  # Use 10 numbers for each account


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with open(workcard, "a", encoding="utf8") as file:
        file.writelines(message + '\n')


def get_next_phones(count):
    """Get next N phone numbers from the pool in a thread-safe manner"""
    global phone_index, phone_numbers, phone_lock

    with phone_lock:
        phones = []
        for _ in range(count):
            if phone_index >= len(phone_numbers):
                phone_index = 0  # Reset to beginning if we run out
            if len(phone_numbers) > 0:
                phones.append(phone_numbers[phone_index])
                phone_index += 1
        return phones


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


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
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


def mcafee_login_automation(email, password, phone_numbers_list, runner_id, progress_bar):
    """
    Automates McAfee login and 2FA setup process with 10 numbers
    """
    url = "https://myaccount.mcafee.com/v2/profile/en-us/0"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)  # Set to False for visible browser
            context = browser.new_context()
            stealth_sync(context)
            page = context.new_page()

            logger.info(f"{runner_id}: Navigating to McAfee login page...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)

            # Step 1: Enter email
            logger.info(f"{runner_id}: Entering email...")
            email_input = page.locator('input[type="email"][name="email"]')
            email_input.wait_for(state="visible", timeout=15000)
            email_input.fill(email)
            time.sleep(1)

            # Step 2: Enter password
            logger.info(f"{runner_id}: Entering password...")
            password_input = page.locator('input[type="password"][name="password"]')
            password_input.fill(password)
            time.sleep(1)

            # Step 3: Click sign in button (human-like)
            logger.info(f"{runner_id}: Clicking sign in button...")
            sign_in_button = page.locator('button#sign-in-button[aria-label="Sign in"]')
            sign_in_button.wait_for(state="visible", timeout=5000)
            time.sleep(random.uniform(0.5, 1.5))
            human_like_click(page, sign_in_button)

            # Wait 11 seconds for sign-in button to reappear
            logger.info(f"{runner_id}: Waiting 11 seconds...")
            time.sleep(11)

            # Check if sign-in button appeared again and click it
            try:
                if sign_in_button.is_visible(timeout=1000):
                    logger.info(f"{runner_id}: Sign-in button reappeared, clicking again...")
                    time.sleep(random.uniform(0.5, 1.5))
                    human_like_click(page, sign_in_button)
                    time.sleep(2)
            except:
                pass

            # Check for login error
            try:
                login_error = page.locator('div#login-error-id[data-testid="error-div"]')
                if login_error.is_visible(timeout=2000):
                    logger.error(f"{runner_id}: Login failed - Invalid credentials")
                    savecreated('failed', f"{email}:{password} - Invalid credentials")
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return
            except:
                pass

            # Step 4: Search for Enable 2FA button
            logger.info(f"{runner_id}: Searching for Enable 2FA button...")
            enable_2fa_button = page.locator('button.pgs-button.pgs-button--secondary.pgs-button--md.pgs-button__width--normal.pgs-button__shape--pill.mr-8.mt-24.fs-unmask')
            enable_2fa_button.wait_for(state="visible", timeout=15000)
            logger.success(f"{runner_id}: Enable 2FA button found!")
            enable_2fa_button.click()
            time.sleep(3)

            # Step 5: Change country to Yemen
            logger.info(f"{runner_id}: Changing country to Yemen...")
            country_button = page.locator('button[name="action"][value="pick-country-code"]')
            country_button.wait_for(state="visible", timeout=15000)
            country_button.click()
            time.sleep(2)

            logger.info(f"{runner_id}: Searching for Yemen...")
            search_input = page.locator('input[type="search"][name="with-search"]')
            search_input.wait_for(state="visible", timeout=10000)
            search_input.fill("yemen")
            time.sleep(2)

            logger.info(f"{runner_id}: Selecting Yemen...")
            yemen_option = page.locator('span:has-text("Yemen (+967)")')
            yemen_option.first.click()
            time.sleep(2)

            # Step 6: Use 10 numbers with Edit button approach
            logger.info(f"{runner_id}: Starting 10-number cycle...")

            for attempt_num, phone_number in enumerate(phone_numbers_list[:NUMBERS_PER_ACCOUNT], 1):
                logger.info(f"{runner_id}: Attempt {attempt_num}/10 - Using phone {phone_number}")

                # Enter phone number
                phone_input = page.locator('input[name="phone"][type="text"]')
                phone_input.wait_for(state="visible", timeout=10000)

                # Clear existing value and enter new number
                phone_input.fill("")  # Clear first
                time.sleep(0.5)
                phone_input.fill(phone_number)
                time.sleep(1)

                # Click continue button
                logger.info(f"{runner_id}: Clicking continue...")
                continue_button = page.locator('button[name="action"][value="default"][data-action-button-primary="true"]')
                continue_button.click()
                time.sleep(3)

                # Check for immediate block alert
                try:
                    immediate_alert = page.locator('div#prompt-alert[data-error-code="too-many-sms"]')
                    if immediate_alert.is_visible(timeout=2000):
                        logger.warning(f"{runner_id}: Phone {phone_number} already blocked!")
                        # Remove this number and continue to next
                        remove_phone_from_file(phone_number)

                        # If this was the last attempt, save to completed
                        if attempt_num == NUMBERS_PER_ACCOUNT:
                            logger.success(f"{runner_id}: Account DONE - Completed 10 attempts")
                            all_phones = ":".join(phone_numbers_list[:NUMBERS_PER_ACCOUNT])
                            savecreated('completed', f"{email}:{password}:{all_phones}")
                            browser.close()
                            if progress_bar:
                                progress_bar.update(1)
                            return

                        # Click Edit button to try next number
                        time.sleep(1)
                        edit_button = page.locator('a.ceef21d30.ce025ff9f.cc6e2a95c.c4a61485b[aria-label="Edit phone number"]')
                        if edit_button.is_visible(timeout=2000):
                            edit_button.click()
                            time.sleep(2)
                            continue
                except:
                    pass

                # Remove the used number from file
                remove_phone_from_file(phone_number)

                # Check if we've completed all 10 attempts
                if attempt_num == NUMBERS_PER_ACCOUNT:
                    logger.success(f"{runner_id}: Account DONE - Completed 10 attempts")
                    all_phones = ":".join(phone_numbers_list[:NUMBERS_PER_ACCOUNT])
                    savecreated('completed', f"{email}:{password}:{all_phones}")
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return

                # Click Edit button for next number
                time.sleep(2)
                logger.info(f"{runner_id}: Clicking Edit button for next number...")
                edit_button = page.locator('a.ceef21d30.ce025ff9f.cc6e2a95c.c4a61485b[aria-label="Edit phone number"]')

                if edit_button.is_visible(timeout=3000):
                    edit_button.click()
                    time.sleep(2)
                else:
                    logger.warning(f"{runner_id}: Edit button not found")
                    break

            logger.success(f"{runner_id}: Automation completed!")
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            phones_str = ":".join(phone_numbers_list[:NUMBERS_PER_ACCOUNT]) if phone_numbers_list else "no_phones"
            savecreated('failed', f"{email}:{password}:{phones_str} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, account_data, progress_bar):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"
    email, password = account_data.split(':', 1)

    # Get 10 phone numbers for this account
    phones = get_next_phones(NUMBERS_PER_ACCOUNT)

    if len(phones) < NUMBERS_PER_ACCOUNT:
        logger.warning(f"{runner_id}: Not enough phone numbers available (need {NUMBERS_PER_ACCOUNT}, got {len(phones)})")
        if progress_bar:
            progress_bar.update(1)
        return

    logger.info(f"{runner_id}: Starting automation for {email} with {len(phones)} phone numbers")
    mcafee_login_automation(email, password, phones, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("McAfee Login Automation Script - V3")
    logger.info("=" * 50)
    logger.info(f"Using {NUMBERS_PER_ACCOUNT} numbers per account")

    # Load accounts from file (format: email:password)
    try:
        with open("accounts.txt", "r", encoding="utf8") as file:
            accounts = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(accounts)} accounts from accounts.txt")
    except FileNotFoundError:
        logger.error("'accounts.txt' not found. Create a file with format: email:password")
        exit(1)

    # Load phone numbers from file
    try:
        with open("numbers.txt", "r", encoding="utf8") as file:
            phone_numbers = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(phone_numbers)} phone numbers from numbers.txt")
    except FileNotFoundError:
        logger.error("'numbers.txt' not found. Create a file with phone numbers (one per line)")
        exit(1)

    if len(phone_numbers) < NUMBERS_PER_ACCOUNT:
        logger.error(f"Not enough phone numbers! Need at least {NUMBERS_PER_ACCOUNT} numbers, found {len(phone_numbers)}")
        exit(1)

    # Calculate how many accounts can be processed
    max_accounts = len(phone_numbers) // NUMBERS_PER_ACCOUNT
    logger.info(f"Can process up to {max_accounts} accounts with available phone numbers")

    if len(accounts) > max_accounts:
        logger.warning(f"Note: Only {max_accounts} accounts will be processed (limited by phone numbers)")
        accounts = accounts[:max_accounts]

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, accounts[i], progress_bar), range(len(accounts)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
