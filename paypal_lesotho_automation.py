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


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with open(workcard, "a", encoding="utf8") as file:
        file.writelines(message + '\n')


def get_next_phone():
    """Get next phone number from the pool in a thread-safe manner"""
    global phone_index, phone_numbers, phone_lock

    with phone_lock:
        if phone_index >= len(phone_numbers):
            phone_index = 0  # Reset to beginning if we run out
        phone = phone_numbers[phone_index]
        phone_index += 1
        return phone


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


def paypal_lesotho_automation(email, password, phone_number, runner_id, progress_bar):
    """
    Automates PayPal Lesotho signup process
    """
    url = "https://www.paypal.com/ls/welcome/signup/#/login_info_phone"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)  # Visible browser for debugging
            context = browser.new_context()
            stealth_sync(context)
            page = context.new_page()

            logger.info(f"{runner_id}: Navigating to PayPal signup page...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)

            # Step 1: Select Lesotho from country dropdown
            logger.info(f"{runner_id}: Selecting Lesotho from country dropdown...")
            try:
                # Click on the country input to open dropdown
                country_input = page.locator('input[name="combo_t_/paypalAccountData/countryselector"]')
                country_input.wait_for(state="visible", timeout=15000)
                country_input.click()
                time.sleep(1)

                # Clear existing value and type "Lesotho"
                country_input.fill("")
                time.sleep(0.5)
                country_input.type("Lesotho", delay=100)
                time.sleep(2)

                # Select Lesotho from dropdown options
                lesotho_option = page.locator('text=Lesotho').first
                lesotho_option.click()
                time.sleep(1)
            except Exception as e:
                logger.error(f"{runner_id}: Error selecting Lesotho: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 2: Click "Get Started" button
            logger.info(f"{runner_id}: Clicking Get Started button...")
            try:
                get_started_button = page.locator('button#paypalAccountData_submit[name="/appData/action"]').first
                get_started_button.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.5, 1.5))
                human_like_click(page, get_started_button)
                time.sleep(3)
            except Exception as e:
                logger.error(f"{runner_id}: Error clicking Get Started: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 3: Enter email address
            logger.info(f"{runner_id}: Entering email address...")
            try:
                email_input = page.locator('input[type="email"][name="/paypalAccountData/email"]')
                email_input.wait_for(state="visible", timeout=15000)
                email_input.fill(email)
                time.sleep(1)
            except Exception as e:
                logger.error(f"{runner_id}: Error entering email: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 4: Click Next button (after email)
            logger.info(f"{runner_id}: Clicking Next button (after email)...")
            try:
                next_button = page.locator('button#paypalAccountData_submit[value="login_info_phone"]').first
                next_button.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.5, 1.5))
                human_like_click(page, next_button)
                time.sleep(3)
            except Exception as e:
                logger.error(f"{runner_id}: Error clicking Next (after email): {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 5: Enter phone number
            logger.info(f"{runner_id}: Entering phone number...")
            try:
                # Wait for phone input field (the name pattern suggests it might have dynamic parts)
                phone_input = page.locator('input[type="tel"]').first
                phone_input.wait_for(state="visible", timeout=15000)
                phone_input.fill(phone_number)
                time.sleep(1)
            except Exception as e:
                logger.error(f"{runner_id}: Error entering phone number: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 6: Click Next button (after phone)
            logger.info(f"{runner_id}: Clicking Next button (after phone)...")
            try:
                next_button_phone = page.locator('button#paypalAccountData_submit[value="init_phone_confirmation"]').first
                next_button_phone.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.5, 1.5))
                human_like_click(page, next_button_phone)
                time.sleep(3)
            except Exception as e:
                logger.error(f"{runner_id}: Error clicking Next (after phone): {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 7: Keep clicking "Resend code" until error appears
            logger.info(f"{runner_id}: Starting resend loop...")
            resend_count = 0
            max_resends = 100  # Safety limit

            while resend_count < max_resends:
                # Check if error message appears (target: "Sorry, we can't send a new code right now. Try again later.")
                try:
                    error_div = page.locator('div.twd77p3')
                    error_text = page.locator('span.globalNotification:has-text("Sorry, we can\'t send a new code right now")')

                    if error_text.is_visible(timeout=1000):
                        logger.success(f"{runner_id}: Account DONE (resend limit reached after {resend_count} resends)")
                        savecreated('completed', f"{email}:{password}:{phone_number}")
                        browser.close()
                        if progress_bar:
                            progress_bar.update(1)
                        return
                except:
                    pass

                # Click "Resend code" button
                try:
                    # Look for the resend button with message icon
                    resend_button = page.locator('button#paypalAccountData_nextBtn[data-automation-id="send_again"]').first
                    if resend_button.is_visible(timeout=3000):
                        time.sleep(random.uniform(1, 2))  # Human-like delay
                        resend_button.click()
                        resend_count += 1
                        logger.info(f"{runner_id}: Resend clicked ({resend_count} times)")
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
    paypal_lesotho_automation(email, password, phone, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("PayPal Lesotho Signup Automation Script")
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
            list(executor.map(lambda i: run_worker(i, accounts[i], progress_bar), range(len(accounts))))

    logger.success("Script finished!")
    input('Press Enter to exit...')
