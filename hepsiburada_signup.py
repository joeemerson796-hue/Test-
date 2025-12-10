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
            return None  # No more numbers available
        phone = phone_numbers[phone_index]
        phone_index += 1
        return phone


def human_like_type(element, text):
    """Simulate human-like typing with random delays between characters"""
    for char in text:
        element.type(char)
        time.sleep(random.uniform(0.05, 0.15))


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


def hepsiburada_signup_automation(phone_number, runner_id, iteration):
    """
    Automates Hepsiburada signup form submission for a single phone number
    """
    url = "https://giris.hepsiburada.com/?ReturnUrl=https%3A%2F%2Foauth.hepsiburada.com%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3DSPA%26redirect_uri%3Dhttps%253A%252F%252Fwww.hepsiburada.com%252Fuyelik%252Fcallback%26response_type%3Dcode%26scope%3Dopenid%2520profile%26state%3D4aa0e099a09a46fea99464647adcc880%26code_challenge%3DLKWyoKssZapoiPs8nkVhi9Xe60yn1kMUWXH2arc8xLo%26code_challenge_method%3DS256%26response_mode%3Dquery%26ActivePage%3DSIGN_UP%26oidcReturnUrl%3Dhttps%253A%252F%252Fwww.hepsiburada.com%252F"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(
                headless=True,  # Headless for maximum speed
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ]
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )

            stealth_sync(context)
            page = context.new_page()

            # Fast page load
            page.goto(url, wait_until="load", timeout=15000)

            # Step 1: Find and fill the username/phone input field
            try:
                username_input = page.locator('input#txtUserName[name="username"]')
                username_input.wait_for(state="visible", timeout=8000)

                # Instant fill - no delays
                username_input.fill(phone_number)

            except Exception as e:
                logger.error(f"{runner_id} [Iteration {iteration}]: Failed to fill phone number - {e}")
                savecreated('failed', f"{phone_number} - Error filling field: {str(e)}")
                browser.close()
                return False

            # Step 2: Click the submit button
            try:
                submit_button = page.locator('button#btnSignUpSubmit[name="btnSignUpSubmit"]')
                submit_button.wait_for(state="visible", timeout=5000)

                # Instant click
                submit_button.click()

                # Minimal wait for submission
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"{runner_id} [Iteration {iteration}]: Failed to click submit button - {e}")
                savecreated('failed', f"{phone_number} - Error clicking button: {str(e)}")
                browser.close()
                return False

            # Log success
            savecreated('submitted', f"{phone_number} - Iteration {iteration}")
            logger.success(f"{runner_id} [Iter {iteration}]: ✓ {phone_number}")

            browser.close()
            return True

        except Exception as e:
            logger.error(f"{runner_id} [Iteration {iteration}]: Automation failed - {e}")
            savecreated('failed', f"{phone_number} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            return False


def run_worker(worker_index, progress_bar):
    """
    Worker function to process phone numbers until none are left
    Each worker will:
    1. Get a phone number
    2. Submit it (3 times per number)
    3. Repeat until numbers.txt is empty
    """
    runner_id = f"Worker-{worker_index + 1}"
    processed_count = 0

    while True:
        phone = get_next_phone()  # Get next phone from pool

        if phone is None:
            # No more numbers available
            break

        # Process this phone 3 times
        for iteration in range(1, 4):
            success = hepsiburada_signup_automation(phone, runner_id, iteration)

            if not success:
                logger.warning(f"{runner_id}: Failed {phone}")

            if progress_bar:
                progress_bar.update(1)

        processed_count += 1

    logger.success(f"{runner_id}: DONE ✓ Processed {processed_count} numbers ({processed_count * 3} submissions)")


if __name__ == "__main__":
    clear_console()
    logger.info("Hepsiburada Signup Automation - FAST MODE")
    logger.info("=" * 50)

    # Load phone numbers from file
    try:
        with open("numbers.txt", "r", encoding="utf8") as file:
            phone_numbers = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(phone_numbers)} numbers")
    except FileNotFoundError:
        logger.error("'numbers.txt' not found")
        exit(1)

    if len(phone_numbers) == 0:
        logger.error("No phone numbers loaded")
        exit(1)

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Calculate total submissions (each number gets submitted 3 times)
    total_submissions = len(phone_numbers) * 3
    logger.info(f"Starting {num_workers} workers")
    logger.info(f"Total: {len(phone_numbers)} numbers → {total_submissions} submissions")

    # Initialize progress bar
    with tqdm(total=total_submissions, desc="Progress", unit="submission", ncols=80) as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, progress_bar), range(num_workers))

    logger.success("✓ ALL NUMBERS PROCESSED!")
    logger.info(f"Check submitted.txt and failed.txt for results")
