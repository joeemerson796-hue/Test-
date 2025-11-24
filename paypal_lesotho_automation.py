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


def get_chrome_profile_path(profile_number):
    """Get Chrome profile path based on profile number (1-8)"""
    # Get user's home directory
    if os.name == 'nt':  # Windows
        user_home = os.path.expanduser('~')
        chrome_data_dir = os.path.join(user_home, 'AppData', 'Local', 'Google', 'Chrome', 'User Data')

        # Profile 1 is "Default", Profile 2-8 are "Profile 1" through "Profile 7"
        if profile_number == 1:
            return os.path.join(chrome_data_dir, 'Default')
        else:
            return os.path.join(chrome_data_dir, f'Profile {profile_number - 1}')
    else:  # Linux/Mac
        user_home = os.path.expanduser('~')
        if os.uname().sysname == 'Darwin':  # Mac
            chrome_data_dir = os.path.join(user_home, 'Library', 'Application Support', 'Google', 'Chrome')
        else:  # Linux
            chrome_data_dir = os.path.join(user_home, '.config', 'google-chrome')

        if profile_number == 1:
            return os.path.join(chrome_data_dir, 'Default')
        else:
            return os.path.join(chrome_data_dir, f'Profile {profile_number - 1}')


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


def paypal_lesotho_automation(email, password, phone_number, runner_id, progress_bar, profile_path):
    """
    Automates PayPal Lesotho signup process using Chrome profile
    """
    url = "https://www.paypal.com/ls/welcome/signup/#/login_info_phone"

    with sync_playwright() as playwright:
        try:
            # Launch persistent context with Chrome profile (with extensions enabled)
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=False,
                channel="chrome",  # Use installed Chrome instead of Chromium
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-features=BlockInsecurePrivateNetworkRequests',
                    '--disable-infobars',
                    '--disable-notifications',
                ],
                ignore_default_args=['--enable-automation', '--disable-extensions'],
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                accept_downloads=True,
                slow_mo=50  # Slow down operations by 50ms to appear more human
            )
            stealth_sync(context)

            # Wait for extensions to load
            time.sleep(3)
            page = context.pages[0] if context.pages else context.new_page()

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
                time.sleep(2)

                # Click on Lesotho option using data-value attribute
                lesotho_option = page.locator('div[role="option"][data-value="LS"]')
                lesotho_option.wait_for(state="visible", timeout=10000)
                lesotho_option.click()
                time.sleep(1)
            except Exception as e:
                logger.error(f"{runner_id}: Error selecting Lesotho: {e}")
                context.close()
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
                context.close()
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
                context.close()
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
                context.close()
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
                context.close()
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
                context.close()
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
                        context.close()
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
            context.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('failed', f"{email}:{password}:{phone_number} - Error: {str(e)}")
            try:
                context.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, account_data, progress_bar, num_profiles=8):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"
    email, password = account_data.split(':', 1)
    phone = get_next_phone()  # Get next phone from pool

    # Calculate which profile to use (cycle through 1-8)
    profile_number = (index % num_profiles) + 1
    profile_path = get_chrome_profile_path(profile_number)

    logger.info(f"{runner_id}: Starting automation for {email} with phone {phone} using Profile {profile_number}")
    paypal_lesotho_automation(email, password, phone, runner_id, progress_bar, profile_path)


if __name__ == "__main__":
    clear_console()
    logger.info("PayPal Lesotho Signup Automation Script")
    logger.info("=" * 50)
    logger.warning("IMPORTANT: Make sure Google Chrome is completely closed before running!")
    logger.warning("Chrome must be closed for profiles to load properly with extensions.")
    input("Press Enter when Chrome is closed and you're ready to continue...")

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

    # Ask for number of workers (max 8 for Chrome profiles)
    num_workers = int(input('Number of concurrent workers (max 8): '))
    if num_workers > 8:
        logger.warning("Maximum 8 workers allowed (one per Chrome profile). Setting to 8.")
        num_workers = 8
    elif num_workers < 1:
        logger.error("Number of workers must be at least 1.")
        exit(1)

    logger.info(f"Using {num_workers} Chrome profiles for automation")

    # Initialize progress bar
    with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(executor.map(lambda i: run_worker(i, accounts[i], progress_bar, num_workers), range(len(accounts))))

    logger.success("Script finished!")
    input('Press Enter to exit...')
