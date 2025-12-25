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
completed_accounts = set()  # Track completed accounts to avoid duplicates
completed_lock = Lock()


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def save_completed_account(email, password):
    """Save account to completed.txt only once"""
    account_key = f"{email}:{password}"
    with completed_lock:
        if account_key not in completed_accounts:
            completed_accounts.add(account_key)
            savecreated('completed', account_key)
            logger.success(f"Saved to completed.txt: {account_key}")


def remove_account_from_file(account_data):
    """Remove account from accounts.txt file"""
    try:
        with file_lock:
            with open("accounts.txt", "r", encoding="utf8") as file:
                lines = file.readlines()
            with open("accounts.txt", "w", encoding="utf8") as file:
                for line in lines:
                    if line.strip() != account_data:
                        file.write(line)
            logger.info(f"Removed account from accounts.txt: {account_data.split(':')[0]}")
    except Exception as e:
        logger.error(f"Error removing account from file: {e}")


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


def human_like_type(page, locator, text):
    """Type text like a human with random delays"""
    locator.click()
    time.sleep(random.uniform(0.1, 0.3))
    for char in text:
        locator.type(char, delay=random.randint(50, 150))  # 50-150ms per character
    time.sleep(random.uniform(0.2, 0.4))


def random_mouse_movement(page):
    """Perform random mouse movements to simulate human behavior"""
    for _ in range(random.randint(1, 3)):
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        page.mouse.move(x, y, steps=random.randint(5, 15))
        time.sleep(random.uniform(0.1, 0.3))


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
    # Small random movement before clicking
    random_mouse_movement(page)

    box = locator.bounding_box()
    if box:
        x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
        y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
        page.mouse.move(x, y, steps=random.randint(10, 20))
        time.sleep(random.uniform(0.2, 0.5))
        page.mouse.click(x, y)
    else:
        locator.click()
    time.sleep(random.uniform(0.3, 0.6))


def random_scroll(page):
    """Perform random scrolling to simulate human reading"""
    scroll_amount = random.randint(100, 400)
    page.mouse.wheel(0, scroll_amount)
    time.sleep(random.uniform(0.3, 0.7))


def dsb_registration_automation(email, password, iterations, runner_id, progress_bar, account_data):
    """
    Automates DSB registration process with multiple phone number iterations
    """
    url = "https://www.dsb.dk/auth/opret"

    with sync_playwright() as playwright:
        try:
            # Random viewport sizes to appear more human
            viewports = [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
                {'width': 1536, 'height': 864},
                {'width': 1440, 'height': 900},
            ]
            viewport = random.choice(viewports)

            # Random user agents
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            ]
            user_agent = random.choice(user_agents)

            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale='da-DK',  # Danish locale
                timezone_id='Europe/Copenhagen',
            )
            stealth_sync(context)
            page = context.new_page()

            logger.info(f"{runner_id}: Navigating to DSB registration page...")
            page.goto(url, wait_until="networkidle")  # Wait for all network activity to finish
            time.sleep(random.uniform(3, 5))  # Much longer delay after page load

            # Random scroll to simulate reading the page
            logger.info(f"{runner_id}: Simulating reading the page...")
            for _ in range(random.randint(2, 4)):
                random_scroll(page)
                time.sleep(random.uniform(1, 2))

            # Step 1: Handle cookie consent - Click "Afvis" (Decline)
            logger.info(f"{runner_id}: Handling cookie consent...")
            try:
                decline_button = page.locator('button#declineButton.coi-banner__decline')
                if decline_button.is_visible(timeout=5000):
                    time.sleep(random.uniform(1.5, 3.0))  # Wait longer before clicking
                    human_like_click(page, decline_button)
                    logger.success(f"{runner_id}: Declined cookies")
                    time.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.warning(f"{runner_id}: Cookie banner not found or already dismissed")

            # Step 2: Enter email
            logger.info(f"{runner_id}: Entering email {email}...")
            email_input = page.locator('input[type="email"][data-testid="email-email-input"]')
            email_input.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(1, 2))  # Wait before interacting
            human_like_type(page, email_input, email)
            time.sleep(random.uniform(1.5, 2.5))  # Longer pause after email

            # Step 3: Enter password
            logger.info(f"{runner_id}: Entering password...")
            password_input = page.locator('input[type="password"][data-testid="password-password-input"]')
            password_input.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(0.8, 1.5))
            human_like_type(page, password_input, password)
            time.sleep(random.uniform(1.5, 2.5))  # Longer pause

            # Step 4: Enter password confirmation
            logger.info(f"{runner_id}: Confirming password...")
            confirm_password_input = page.locator('input[type="password"][data-testid="confirmPassword-password-input"]')
            confirm_password_input.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(0.8, 1.5))
            human_like_type(page, confirm_password_input, password)
            time.sleep(random.uniform(1.5, 2.5))  # Longer pause

            # Step 5: Enter birthdate (11/11/2000)
            logger.info(f"{runner_id}: Entering birthdate...")
            birthdate_input = page.locator('input[type="date"][data-testid="birthdate-date-input"]')
            birthdate_input.wait_for(state="visible", timeout=10000)
            time.sleep(random.uniform(1, 1.5))
            birthdate_input.click()
            time.sleep(random.uniform(0.5, 1.0))
            birthdate_input.fill("2000-11-11")  # Date picker works better with fill
            time.sleep(random.uniform(1.5, 2.5))

            # Step 6: Click "Opret profil" button
            logger.info(f"{runner_id}: Clicking 'Opret profil' button...")
            create_profile_button = page.locator('button[type="submit"].flex.items-center.justify-center:has-text("Opret profil")')
            create_profile_button.wait_for(state="visible", timeout=15000)

            # Random scroll before clicking
            random_scroll(page)
            time.sleep(random.uniform(2, 3))  # Much longer wait

            # Scroll button into view
            create_profile_button.scroll_into_view_if_needed()
            time.sleep(random.uniform(1.5, 2.5))  # Longer wait

            # Try clicking the button multiple times if needed
            click_success = False
            for attempt in range(3):
                try:
                    logger.info(f"{runner_id}: Click attempt {attempt + 1}...")
                    human_like_click(page, create_profile_button)
                    click_success = True
                    logger.success(f"{runner_id}: Button clicked successfully!")
                    break
                except Exception as e:
                    logger.warning(f"{runner_id}: Click attempt {attempt + 1} failed: {e}")
                    time.sleep(random.uniform(1.0, 2.0))

            if not click_success:
                raise Exception("Failed to click 'Opret profil' button after 3 attempts")

            # Wait and check for error message (profile already exists)
            logger.info(f"{runner_id}: Checking for errors...")
            time.sleep(2)

            try:
                error_msg = page.locator('p.mt-4.text-sm.text-border-error:has-text("Der findes en profil med denne e-mail")')
                if error_msg.is_visible(timeout=2000):
                    logger.warning(f"{runner_id}: Account already exists! Marking as completed and moving to next account")
                    save_completed_account(email, password)
                    remove_account_from_file(account_data)
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return
            except:
                pass

            # Wait for page to load
            logger.info(f"{runner_id}: Waiting for next page to load...")
            time.sleep(random.uniform(4, 6))  # Much longer wait

            # Now start iterations with different phone numbers
            for iteration in range(iterations):
                logger.info(f"{runner_id}: Starting iteration {iteration + 1}/{iterations}")

                # Delay between iterations to avoid rate limiting
                if iteration > 0:
                    delay = random.uniform(5, 10)
                    logger.info(f"{runner_id}: Waiting {delay:.1f}s between iterations to avoid detection...")
                    time.sleep(delay)

                # Get next phone number
                phone = get_next_phone()
                if phone is None:
                    logger.error(f"{runner_id}: No more phone numbers available, stopping iterations")
                    break

                # Step 7: Generate and enter first name (8 chars)
                first_name = generate_random_name(8)
                logger.info(f"{runner_id}: Entering first name: {first_name}")
                first_name_input = page.locator('input#firstName[name="firstName"]')
                first_name_input.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(1, 1.5))
                human_like_type(page, first_name_input, first_name)
                time.sleep(random.uniform(1, 2))

                # Step 8: Generate and enter last name (10 chars)
                last_name = generate_random_name(10)
                logger.info(f"{runner_id}: Entering last name: {last_name}")
                last_name_input = page.locator('input#lastName[name="lastName"]')
                last_name_input.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.8, 1.5))
                human_like_type(page, last_name_input, last_name)
                time.sleep(random.uniform(1, 2))

                # Step 9: Select Armenia (+374) from country code dropdown
                logger.info(f"{runner_id}: Selecting Armenia (+374)...")
                country_select = page.locator('select#country-code[name="countryCode"]')
                country_select.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.8, 1.2))
                country_select.click()
                time.sleep(random.uniform(0.5, 1.0))
                country_select.select_option(value="+374")
                time.sleep(random.uniform(1, 1.5))

                # Step 10: Enter phone number
                logger.info(f"{runner_id}: Entering phone number: {phone}")
                phone_input = page.locator('input#phoneNumber[name="phoneNumber"]')
                phone_input.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.8, 1.2))
                human_like_type(page, phone_input, phone)
                time.sleep(random.uniform(1, 2))

                # Step 11: Click "Næste" button
                logger.info(f"{runner_id}: Clicking 'Næste' button...")
                next_button = page.locator('button[type="submit"].flex.items-center.justify-center:has-text("Næste")')
                next_button.wait_for(state="visible", timeout=15000)

                # Random scroll before clicking
                random_scroll(page)
                time.sleep(random.uniform(1.5, 2.5))  # Much longer wait

                # Scroll button into view
                next_button.scroll_into_view_if_needed()
                time.sleep(random.uniform(1, 2))  # Longer wait

                # Try clicking the button multiple times if needed
                click_success = False
                for attempt in range(3):
                    try:
                        logger.info(f"{runner_id}: Næste button click attempt {attempt + 1}...")
                        human_like_click(page, next_button)
                        click_success = True
                        logger.success(f"{runner_id}: Næste button clicked successfully!")
                        break
                    except Exception as e:
                        logger.warning(f"{runner_id}: Næste click attempt {attempt + 1} failed: {e}")
                        time.sleep(random.uniform(1.0, 2.0))

                if not click_success:
                    raise Exception("Failed to click 'Næste' button after 3 attempts")

                time.sleep(random.uniform(2, 4))  # Longer wait after clicking

                # Step 12: Wait for "Tilbage" button and click it
                logger.info(f"{runner_id}: Waiting for 'Tilbage' button...")
                tilbage_button = page.locator('a.flex.items-center[href="/auth/opret/personlig-information"]:has-text("Tilbage")')
                tilbage_button.wait_for(state="visible", timeout=15000)
                time.sleep(random.uniform(1.5, 2.5))  # Longer wait

                logger.info(f"{runner_id}: Clicking 'Tilbage' button...")
                human_like_click(page, tilbage_button)
                time.sleep(random.uniform(2, 3))  # Longer wait after going back

                logger.success(f"{runner_id}: Iteration {iteration + 1}/{iterations} completed with phone {phone}")

            # Save account as completed ONCE after all iterations
            save_completed_account(email, password)

            # Remove account from accounts.txt
            remove_account_from_file(account_data)

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

    # Add delay between starting different accounts to avoid triggering anti-bot
    if index > 0:
        delay = random.uniform(10, 20)
        logger.info(f"{runner_id}: Waiting {delay:.1f}s before starting account to avoid detection...")
        time.sleep(delay)

    email, password = account_data.split(':', 1)

    logger.info(f"{runner_id}: Starting automation for {email} with {iterations} iterations")
    dsb_registration_automation(email, password, iterations, runner_id, progress_bar, account_data)


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
    print("\n⚠️  IMPORTANT: To avoid reCAPTCHA, it's strongly recommended to use only 1 worker.")
    print("Multiple concurrent workers from the same IP will likely trigger anti-bot detection.\n")
    num_workers = int(input('Number of concurrent workers (recommended: 1): '))

    if num_workers > 1:
        logger.warning(f"Using {num_workers} workers may trigger reCAPTCHA. Consider using 1 worker instead.")

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, accounts[i], iterations, progress_bar), range(len(accounts)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
