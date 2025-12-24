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
            logger.error("No more phone numbers available!")
            return None
        phone = phone_numbers[phone_index]
        phone_index += 1
        return phone


def generate_random_name(length):
    """Generate random name with first letter uppercase"""
    first_letter = random.choice(string.ascii_uppercase)
    rest_letters = ''.join(random.choices(string.ascii_lowercase, k=length-1))
    return first_letter + rest_letters


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
    box = locator.bounding_box()
    if box:
        x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
        y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.1, 0.3))
        page.mouse.click(x, y)
    else:
        locator.click()


def dsb_registration_automation(email, password, iterations, runner_id, progress_bar):
    """
    Automates DSB registration process with multiple phone number iterations
    """
    url = "https://www.dsb.dk/auth/opret"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            stealth_sync(context)
            page = context.new_page()

            logger.info(f"{runner_id}: Navigating to DSB registration page...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)

            # Step 1: Handle cookie consent - Click "Afvis" (Decline)
            logger.info(f"{runner_id}: Handling cookie consent...")
            try:
                decline_button = page.locator('button#declineButton.coi-banner__decline')
                if decline_button.is_visible(timeout=5000):
                    decline_button.click()
                    time.sleep(2)
                    logger.success(f"{runner_id}: Declined cookies")
            except Exception as e:
                logger.warning(f"{runner_id}: Cookie banner not found or already dismissed: {e}")

            # Step 2: Enter email
            logger.info(f"{runner_id}: Entering email {email}...")
            email_input = page.locator('input[type="email"][data-testid="email-email-input"]')
            email_input.wait_for(state="visible", timeout=15000)
            email_input.fill(email)
            time.sleep(1)

            # Step 3: Enter password
            logger.info(f"{runner_id}: Entering password...")
            password_input = page.locator('input[type="password"][data-testid="password-password-input"]')
            password_input.wait_for(state="visible", timeout=10000)
            password_input.fill(password)
            time.sleep(1)

            # Step 4: Enter password confirmation
            logger.info(f"{runner_id}: Confirming password...")
            confirm_password_input = page.locator('input[type="password"][data-testid="confirmPassword-password-input"]')
            confirm_password_input.wait_for(state="visible", timeout=10000)
            confirm_password_input.fill(password)
            time.sleep(1)

            # Step 5: Enter birthdate (11/11/2000)
            logger.info(f"{runner_id}: Entering birthdate...")
            birthdate_input = page.locator('input[type="date"][data-testid="birthdate-date-input"]')
            birthdate_input.wait_for(state="visible", timeout=10000)
            birthdate_input.fill("2000-11-11")  # Date format: YYYY-MM-DD for HTML5 date input
            time.sleep(1)

            # Step 6: Click "Opret profil" button
            logger.info(f"{runner_id}: Clicking 'Opret profil' button...")
            create_profile_button = page.locator('button[type="submit"].flex.items-center.justify-center:has-text("Opret profil")')
            create_profile_button.wait_for(state="visible", timeout=15000)

            # Wait for button to be enabled (not disabled)
            logger.info(f"{runner_id}: Waiting for button to be enabled...")
            time.sleep(2)

            # Scroll button into view
            create_profile_button.scroll_into_view_if_needed()
            time.sleep(1)

            # Try clicking the button multiple times if needed
            click_success = False
            for attempt in range(3):
                try:
                    logger.info(f"{runner_id}: Click attempt {attempt + 1}...")
                    create_profile_button.click(force=True, timeout=5000)
                    click_success = True
                    logger.success(f"{runner_id}: Button clicked successfully!")
                    break
                except Exception as e:
                    logger.warning(f"{runner_id}: Click attempt {attempt + 1} failed: {e}")
                    time.sleep(2)

            if not click_success:
                raise Exception("Failed to click 'Opret profil' button after 3 attempts")

            # Wait for page to load
            logger.info(f"{runner_id}: Waiting for next page to load...")
            time.sleep(8)

            # Now start iterations with different phone numbers
            for iteration in range(iterations):
                logger.info(f"{runner_id}: Starting iteration {iteration + 1}/{iterations}")

                # Get next phone number
                phone = get_next_phone()
                if phone is None:
                    logger.error(f"{runner_id}: No more phone numbers available, stopping iterations")
                    break

                # Step 7: Generate and enter first name (8 chars)
                first_name = generate_random_name(8)
                logger.info(f"{runner_id}: Entering first name: {first_name}")
                first_name_input = page.locator('input#firstName[name="firstName"]')
                first_name_input.wait_for(state="visible", timeout=15000)
                first_name_input.fill(first_name)
                time.sleep(1)

                # Step 8: Generate and enter last name (10 chars)
                last_name = generate_random_name(10)
                logger.info(f"{runner_id}: Entering last name: {last_name}")
                last_name_input = page.locator('input#lastName[name="lastName"]')
                last_name_input.wait_for(state="visible", timeout=10000)
                last_name_input.fill(last_name)
                time.sleep(1)

                # Step 9: Select Armenia (+374) from country code dropdown
                logger.info(f"{runner_id}: Selecting Armenia (+374)...")
                country_select = page.locator('select#country-code[name="countryCode"]')
                country_select.wait_for(state="visible", timeout=10000)
                country_select.select_option(value="+374")
                time.sleep(1)

                # Step 10: Enter phone number
                logger.info(f"{runner_id}: Entering phone number: {phone}")
                phone_input = page.locator('input#phoneNumber[name="phoneNumber"]')
                phone_input.wait_for(state="visible", timeout=10000)
                phone_input.fill(phone)
                time.sleep(1)

                # Step 11: Click "Næste" button
                logger.info(f"{runner_id}: Clicking 'Næste' button...")
                next_button = page.locator('button[type="submit"]:has-text("Næste")')
                next_button.wait_for(state="visible", timeout=10000)
                human_like_click(page, next_button)
                time.sleep(3)

                # Step 12: Wait for "Tilbage" button and click it
                logger.info(f"{runner_id}: Waiting for 'Tilbage' button...")
                tilbage_button = page.locator('a.flex.items-center[href="/auth/opret/personlig-information"]:has-text("Tilbage")')
                tilbage_button.wait_for(state="visible", timeout=15000)
                time.sleep(2)

                logger.info(f"{runner_id}: Clicking 'Tilbage' button...")
                tilbage_button.click()
                time.sleep(3)

                # Save progress for this iteration
                savecreated('dsb_completed', f"{email}:{password}:{phone}:{first_name}:{last_name}")
                logger.success(f"{runner_id}: Iteration {iteration + 1}/{iterations} completed with phone {phone}")

            logger.success(f"{runner_id}: All {iterations} iterations completed successfully for {email}!")
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('dsb_failed', f"{email}:{password} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, account_data, iterations, progress_bar):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"
    email, password = account_data.split(':', 1)

    logger.info(f"{runner_id}: Starting automation for {email} with {iterations} iterations")
    dsb_registration_automation(email, password, iterations, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("DSB Registration Automation Script")
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

    # Ask for number of iterations per account
    iterations = int(input('Number of iterations per account (phone numbers per account): '))

    # Validate we have enough phone numbers
    total_phones_needed = len(accounts) * iterations
    if total_phones_needed > len(phone_numbers):
        logger.warning(f"Warning: Need {total_phones_needed} phone numbers but only have {len(phone_numbers)}")
        logger.warning(f"Some accounts may not complete all iterations")

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, accounts[i], iterations, progress_bar), range(len(accounts)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
