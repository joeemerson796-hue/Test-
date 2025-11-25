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


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with open(workcard, "a", encoding="utf8") as file:
        file.writelines(message + '\n')


def parse_cookies_from_file(filename="cookies.txt"):
    """
    Parse cookies from file. Each cookie set is separated by blank lines.
    Format: name\tvalue\tdomain\tpath\t...
    Returns list of cookie sets (each set is a list of cookie dicts)
    """
    cookie_sets = []
    current_set = []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Empty line means end of current cookie set
                if not line:
                    if current_set:
                        cookie_sets.append(current_set)
                        current_set = []
                    continue

                # Parse cookie line (tab-separated)
                parts = line.split('\t')
                if len(parts) >= 4:
                    cookie = {
                        "name": parts[0],
                        "value": parts[1],
                        "domain": parts[2],
                        "path": parts[3]
                    }
                    current_set.append(cookie)

            # Add last set if exists
            if current_set:
                cookie_sets.append(current_set)

        logger.info(f"Loaded {len(cookie_sets)} cookie sets from {filename}")
        return cookie_sets
    except FileNotFoundError:
        logger.error(f"'{filename}' not found. Create a file with cookie sets (separated by blank lines)")
        return []


def generate_random_tracking_id(length=32):
    """Generate a random numeric tracking ID"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def randomize_cookies(cookies):
    """
    Randomize non-critical tracking cookies to make each session unique
    Safe to randomize: TLTDID, TLTSID, tsrce, l7_az
    """
    datacenters = ["dcg16.slc", "dcg17.phx", "dcg18.sjc", "dcg19.lvs", "dcg20.ord"]
    traffic_sources = ["privacynodeweb", "merchantweb", "p2pnodeweb", "unifiedlogin"]

    for cookie in cookies:
        if cookie["name"] == "TLTDID":
            cookie["value"] = generate_random_tracking_id(32)
        elif cookie["name"] == "TLTSID":
            cookie["value"] = generate_random_tracking_id(32)
        elif cookie["name"] == "l7_az":
            cookie["value"] = random.choice(datacenters)
        elif cookie["name"] == "tsrce":
            cookie["value"] = random.choice(traffic_sources)

    return cookies


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


def paypal_lesotho_automation(phone_number, cookies, runner_id, progress_bar):
    """
    Automates PayPal Lesotho phone verification using cookies for authentication
    """
    url = "https://www.paypal.com/ls/welcome/signup/#/login_info_phone"

    # Randomize tracking cookies for each session
    cookies = randomize_cookies(cookies)

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

            # Navigate to PayPal first to establish domain
            logger.info(f"{runner_id}: Navigating to PayPal base domain...")
            page.goto("https://www.paypal.com", wait_until="domcontentloaded")
            time.sleep(2)

            # Add cookies to the context
            logger.info(f"{runner_id}: Setting authentication cookies...")
            context.add_cookies(cookies)

            # Reload to apply cookies
            logger.info(f"{runner_id}: Reloading with cookies...")
            page.reload(wait_until="domcontentloaded")
            time.sleep(2)

            # Check if cookies worked by looking at the page
            current_url = page.url
            logger.info(f"{runner_id}: Current URL after cookie auth: {current_url}")

            # Now navigate to the phone entry page
            logger.info(f"{runner_id}: Navigating to phone entry page...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)

            # Check final URL
            final_url = page.url
            logger.info(f"{runner_id}: Final URL: {final_url}")

            # Step 1: Enter phone number directly
            logger.info(f"{runner_id}: Entering phone number...")
            try:
                # Wait for phone input field
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

            # Step 2: Click Next button (after phone)
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

            # Step 3: Keep clicking "Resend code" until error appears
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
                        savecreated('completed', f"{phone_number}")
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
            savecreated('failed', f"{phone_number} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, phone_number, cookies, progress_bar):
    """
    Worker function to process a single phone number with specific cookies
    """
    runner_id = f"Worker-{index + 1}"

    logger.info(f"{runner_id}: Starting automation for phone {phone_number}")
    paypal_lesotho_automation(phone_number, cookies, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("PayPal Lesotho Phone Verification Automation Script")
    logger.info("=" * 50)

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

    # Load cookie sets from file
    cookie_sets = parse_cookies_from_file("cookies.txt")
    if len(cookie_sets) == 0:
        logger.error("No cookie sets loaded. Please add cookies to cookies.txt")
        exit(1)

    # Pair phone numbers with cookies (reuse cookies if more numbers than cookie sets)
    tasks = []
    for i, phone in enumerate(phone_numbers):
        cookie_set = cookie_sets[i % len(cookie_sets)]  # Cycle through cookie sets
        tasks.append((i, phone, cookie_set))

    logger.info(f"Created {len(tasks)} tasks (Phone numbers: {len(phone_numbers)}, Cookie sets: {len(cookie_sets)})")

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(tasks), desc="Progress", unit="phone") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda task: run_worker(task[0], task[1], task[2], progress_bar), tasks)

    logger.success("Script finished!")
    input('Press Enter to exit...')
