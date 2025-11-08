import os
import time
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

            # Step 3: Click sign in button
            logger.info(f"{runner_id}: Clicking sign in button...")
            sign_in_button = page.locator('button#sign-in-button[aria-label="Sign in"]')
            sign_in_button.click()
            time.sleep(5)

            # Step 4: Wait for and click "Enable 2FA" button
            logger.info(f"{runner_id}: Waiting for Enable 2FA button...")
            enable_2fa_button = page.locator('a#ctl00_MainContent_ctl00_m_EnableTwoFactorButtonLabel')
            enable_2fa_button.wait_for(state="visible", timeout=30000)
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
            time.sleep(5)

            # Step 8: Keep clicking resend until max attempts message appears
            logger.info(f"{runner_id}: Starting resend loop...")
            resend_count = 0
            max_resends = 100  # Safety limit

            while resend_count < max_resends:
                try:
                    # Check if max attempts message is visible
                    max_attempts_msg = page.locator('p:has-text("You\'ve reached the maximum number of resend attempts")')
                    if max_attempts_msg.is_visible(timeout=2000):
                        logger.success(f"{runner_id}: Max resend attempts reached! Message displayed.")
                        savecreated('completed', f"{email}:{password}:{phone_number}")
                        break
                except:
                    pass

                # Click resend button
                try:
                    resend_button = page.locator('button[name="action"][value="resend-code"]')
                    if resend_button.is_visible(timeout=3000):
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
    email, password, phone = account_data.split(':', 2)

    logger.info(f"{runner_id}: Starting automation for {email}")
    mcafee_login_automation(email, password, phone, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("McAfee Login Automation Script")
    logger.info("=" * 50)

    # Option 1: Single account mode
    mode = input("Run mode? (1: Single account, 2: Multiple accounts from file): ").strip()

    if mode == "1":
        # Single account mode
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
        phone = input("Enter phone number: ").strip()

        logger.info("Starting single account automation...")
        mcafee_login_automation(email, password, phone, "Single-Worker", None)

    elif mode == "2":
        # Multiple accounts mode
        num_workers = int(input('Number of concurrent workers: '))

        # Load accounts from file (format: email:password:phone)
        try:
            with open("accounts.txt", "r", encoding="utf8") as file:
                accounts = [line.strip() for line in file if line.strip()]
            logger.info(f"Loaded {len(accounts)} accounts from accounts.txt")
        except FileNotFoundError:
            logger.error("'accounts.txt' not found. Create a file with format: email:password:phone")
            exit(1)

        # Initialize progress bar
        with tqdm(total=len(accounts), desc="Progress", unit="account") as progress_bar:
            # Execute workers
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                executor.map(lambda i: run_worker(i, accounts[i], progress_bar), range(len(accounts)))

    else:
        logger.error("Invalid mode selection")
        exit(1)

    logger.success("Script finished!")
    input('Press Enter to exit...')
