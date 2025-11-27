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
    with file_lock:
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


def generate_random_string(length=8):
    """Generate random alphabetical string"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def generate_random_numbers(length=8):
    """Generate random numerical string"""
    return ''.join(random.choices(string.digits, k=length))


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
    try:
        box = locator.bounding_box()
        if box:
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))
            page.mouse.click(x, y)
        else:
            locator.click()
    except:
        locator.click()


def get_priyo_email(page):
    """Get temporary email from priyo.email"""
    logger.info("Opening priyo.email to get temporary email...")
    page.goto("https://priyo.email/", wait_until="domcontentloaded")
    time.sleep(3)

    # Get email from the input field value attribute
    try:
        # Find the email input field and get its value
        email_input = page.locator('input#email[type="text"]')
        email_input.wait_for(state="visible", timeout=10000)
        email = email_input.get_attribute('value')
        logger.success(f"Got email: {email}")
        return email
    except Exception as e:
        logger.error(f"Failed to get email from priyo.email: {e}")
        return None


def wait_for_oracle_verification_email(page, runner_id):
    """Wait for and click Oracle verification email"""
    logger.info(f"{runner_id}: Waiting for Oracle verification email...")

    max_wait = 120  # Wait up to 2 minutes
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            # Look for the parent div that contains oracle-acct_ww@oracle.com
            # The clickable element is the parent div with wire:click attribute
            oracle_email_row = page.locator('div[wire\\:click^="updateView"]:has-text("oracle-acct_ww@oracle.com")')

            if oracle_email_row.is_visible(timeout=2000):
                logger.success(f"{runner_id}: Oracle verification email received!")

                # Click on the email row to open it
                human_like_click(page, oracle_email_row)
                time.sleep(3)

                # Find the alternative verification URL (plain text paragraph)
                # Look for paragraph containing the verification URL
                logger.info(f"{runner_id}: Looking for verification URL in email body...")

                # Try to find the paragraph with the full URL text
                url_paragraph = page.locator('p:has-text("profile.oracle.com/myprofile/account/verify.jspx")')
                url_paragraph.wait_for(state="visible", timeout=10000)

                # Get the text content which contains the URL
                verify_url = url_paragraph.inner_text().strip()
                logger.info(f"{runner_id}: Found verification URL: {verify_url}")

                # Navigate to verification URL in a new page
                logger.info(f"{runner_id}: Opening verification link in new tab...")
                verify_page = page.context.new_page()
                verify_page.goto(verify_url)
                time.sleep(5)

                logger.success(f"{runner_id}: Email verified successfully!")
                return True
        except Exception as e:
            logger.debug(f"{runner_id}: Waiting for email... {e}")
            pass

        time.sleep(3)

    logger.error(f"{runner_id}: Verification email not received within {max_wait} seconds")
    return False


def create_oracle_account(page, email, password, runner_id):
    """Create Oracle account"""
    logger.info(f"{runner_id}: Creating Oracle account...")

    # Open Oracle registration page in new tab
    oracle_page = page.context.new_page()
    stealth_sync(oracle_page.context)

    oracle_page.goto("https://profile.oracle.com/myprofile/account/create-account.jspx",
                      wait_until="domcontentloaded")
    time.sleep(3)

    # FIRST: Select country - Oman (OM) - BEFORE filling any other fields
    logger.info(f"{runner_id}: Selecting country (Oman)...")
    country_select = oracle_page.locator('select#sView1\\:r1\\:0\\:country\\:\\:content')
    country_select.wait_for(state="visible", timeout=15000)

    # Human-like country selection with mouse movement and delays
    time.sleep(random.uniform(0.5, 1.2))  # Random pause before interaction

    # Move mouse to the select element
    box = country_select.bounding_box()
    if box:
        x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
        y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
        oracle_page.mouse.move(x, y)
        time.sleep(random.uniform(0.2, 0.5))

    # Click to open dropdown
    logger.info(f"{runner_id}: Opening country dropdown...")
    country_select.click()
    time.sleep(random.uniform(0.5, 1.0))  # Time to "look" at options

    # Find and click on Oman option (more human-like than select_option)
    logger.info(f"{runner_id}: Clicking on Oman option...")
    oman_option = oracle_page.locator('select#sView1\\:r1\\:0\\:country\\:\\:content option[value="OM"]')

    # Move mouse to Oman option and click
    oman_box = oman_option.bounding_box()
    if oman_box:
        oman_x = oman_box['x'] + oman_box['width'] * random.uniform(0.3, 0.7)
        oman_y = oman_box['y'] + oman_box['height'] * random.uniform(0.3, 0.7)
        oracle_page.mouse.move(oman_x, oman_y)
        time.sleep(random.uniform(0.2, 0.4))
        oracle_page.mouse.click(oman_x, oman_y)
    else:
        # Fallback to regular select if bounding box not available
        country_select.select_option(value="OM")

    time.sleep(random.uniform(0.8, 1.5))  # Pause after selection

    # NOW fill email
    logger.info(f"{runner_id}: Filling registration form with email: {email}")
    email_input = oracle_page.locator('input#sView1\\:r1\\:0\\:email\\:\\:content')
    email_input.wait_for(state="visible", timeout=15000)

    # Type slowly like a human
    email_input.click()
    time.sleep(random.uniform(0.3, 0.6))
    email_input.type(email, delay=random.randint(50, 150))  # Random typing speed
    time.sleep(random.uniform(1, 2))

    # Fill password
    password_input = oracle_page.locator('input#sView1\\:r1\\:0\\:password\\:\\:content')
    password_input.click()
    time.sleep(random.uniform(0.3, 0.6))
    password_input.type(password, delay=random.randint(50, 150))
    time.sleep(random.uniform(1, 2))

    # Retype password
    retype_password_input = oracle_page.locator('input#sView1\\:r1\\:0\\:retypePassword\\:\\:content')
    retype_password_input.click()
    time.sleep(random.uniform(0.3, 0.6))
    retype_password_input.type(password, delay=random.randint(50, 150))
    time.sleep(random.uniform(1, 2))

    # Fill personal details with random data
    first_name = generate_random_string(8)
    last_name = generate_random_string(8)
    job_title = generate_random_string(8)
    work_phone = generate_random_numbers(8)
    company_name = generate_random_string(8)
    address = generate_random_string(8)
    city = generate_random_string(8)
    postal_code = generate_random_numbers(8)

    logger.info(f"{runner_id}: Filling personal details...")

    # First name - type like human
    fn_input = oracle_page.locator('input#sView1\\:r1\\:0\\:firstName\\:\\:content')
    fn_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    fn_input.type(first_name, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # Last name
    ln_input = oracle_page.locator('input#sView1\\:r1\\:0\\:lastName\\:\\:content')
    ln_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    ln_input.type(last_name, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # Job title
    jt_input = oracle_page.locator('input#sView1\\:r1\\:0\\:jobTitle\\:\\:content')
    jt_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    jt_input.type(job_title, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # Work phone
    wp_input = oracle_page.locator('input#sView1\\:r1\\:0\\:workPhone\\:\\:content')
    wp_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    wp_input.type(work_phone, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # Company name
    cn_input = oracle_page.locator('input#sView1\\:r1\\:0\\:companyName\\:\\:content')
    cn_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    cn_input.type(company_name, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # Address
    addr_input = oracle_page.locator('input#sView1\\:r1\\:0\\:address1\\:\\:content')
    addr_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    addr_input.type(address, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # City
    city_input = oracle_page.locator('input#sView1\\:r1\\:0\\:city\\:\\:content')
    city_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    city_input.type(city, delay=random.randint(80, 200))
    time.sleep(random.uniform(0.5, 1.0))

    # Postal code
    pc_input = oracle_page.locator('input#sView1\\:r1\\:0\\:postalCode\\:\\:content')
    pc_input.click()
    time.sleep(random.uniform(0.2, 0.5))
    pc_input.type(postal_code, delay=random.randint(80, 200))
    time.sleep(random.uniform(1, 2))

    # Click Create Account - with human-like behavior
    logger.info(f"{runner_id}: Scrolling to and clicking Create Account button...")
    create_button = oracle_page.locator('div#sView1\\:r1\\:0\\:b1 a')

    # Scroll to button
    create_button.scroll_into_view_if_needed()
    time.sleep(random.uniform(1, 2))

    # Move mouse to button and click (human-like)
    create_button.wait_for(state="visible", timeout=10000)
    human_like_click(oracle_page, create_button)

    logger.info(f"{runner_id}: Create Account button clicked, waiting for response...")
    time.sleep(8)  # Wait longer for Oracle to process

    # Take screenshot for debugging
    try:
        oracle_page.screenshot(path=f"oracle_submit_{runner_id}.png")
        logger.info(f"{runner_id}: Screenshot saved for debugging")
    except:
        pass

    return oracle_page


def oracle_login_and_2fa(email, password, phone_numbers_for_account, runner_id):
    """Login to Oracle and set up 2FA with phone numbers"""
    logger.info(f"{runner_id}: Starting Oracle login and 2FA setup...")

    with sync_playwright() as playwright:
        try:
            # Use more realistic browser settings to avoid detection
            browser = playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                color_scheme='light'
            )
            stealth_sync(context)
            page = context.new_page()

            # Step 1: Get email from priyo.email
            temp_email = get_priyo_email(page)
            if not temp_email:
                logger.error(f"{runner_id}: Failed to get temporary email")
                browser.close()
                return False

            # Step 2: Create Oracle account
            oracle_page = create_oracle_account(page, temp_email, password, runner_id)

            # Step 3: Switch back to priyo.email tab and wait for verification email
            logger.info(f"{runner_id}: Switching back to priyo.email to check for verification email...")
            page.bring_to_front()  # Bring priyo.email tab to front
            time.sleep(2)

            # Refresh the page to see new emails
            logger.info(f"{runner_id}: Refreshing priyo.email page...")
            page.reload()
            time.sleep(3)

            # Wait for verification email
            if not wait_for_oracle_verification_email(page, runner_id):
                logger.error(f"{runner_id}: Failed to verify email")
                browser.close()
                return False

            time.sleep(5)

            # Step 4: Login to Oracle
            logger.info(f"{runner_id}: Logging in to Oracle...")
            login_page = context.new_page()
            login_page.goto("https://signon.oracle.com/signin", wait_until="domcontentloaded")
            time.sleep(3)

            # Enter username
            username_input = login_page.locator('input#idcs-signin-basic-signin-form-username')
            username_input.wait_for(state="visible", timeout=15000)
            username_input.fill(temp_email)
            time.sleep(1)

            # Click Next
            next_button = login_page.locator('button:has-text("Next")')
            next_button.click()
            time.sleep(3)

            # Enter password
            password_input = login_page.locator('input#idcs-auth-pwd-input\\|input')
            password_input.wait_for(state="visible", timeout=15000)
            password_input.fill(password)
            time.sleep(1)

            # Click Sign In
            signin_button = login_page.locator('button:has-text("Sign In")')
            signin_button.click()
            time.sleep(5)

            # Save account
            savecreated('oracle_accounts', f"{temp_email}:{password}")
            logger.success(f"{runner_id}: Account created and saved: {temp_email}")

            # Step 5: Set up 2FA with phone numbers (2 numbers, 4 loops each = 8 total loops)
            logger.info(f"{runner_id}: Starting 2FA setup with phone numbers...")

            for phone_idx, phone_number in enumerate(phone_numbers_for_account):
                logger.info(f"{runner_id}: Using phone number {phone_idx + 1}/2: {phone_number}")

                # Perform 4 loops for this phone number
                for loop_num in range(4):
                    logger.info(f"{runner_id}: Loop {loop_num + 1}/4 for phone {phone_number}")

                    try:
                        # Navigate to signin page for 2FA setup
                        login_page.goto("https://signon.oracle.com/signin", wait_until="domcontentloaded")
                        time.sleep(3)

                        # Click "Phone Number" option
                        phone_option = login_page.locator('div.oj-idaas-signin-buttonset-label:has-text("Phone Number")')
                        phone_option.wait_for(state="visible", timeout=10000)
                        phone_option.click()
                        time.sleep(2)

                        # Click country code selector
                        country_selector = login_page.locator('span#ojChoiceId_country-code_selected')
                        country_selector.click()
                        time.sleep(1)

                        # Search for Malaysia
                        search_input = login_page.locator('input.oj-listbox-input[role="combobox"]')
                        search_input.fill("Malaysia")
                        time.sleep(2)

                        # Select Malaysia +60
                        malaysia_option = login_page.locator('li:has-text("Malaysia +60")')
                        malaysia_option.first.click()
                        time.sleep(1)

                        # Enter phone number
                        phone_input = login_page.locator('input#regMobileNumber\\|input')
                        phone_input.wait_for(state="visible", timeout=10000)
                        phone_input.fill(phone_number)
                        time.sleep(1)

                        # Click "Text Me" (first time)
                        text_me_button = login_page.locator('span.oj-button-text:has-text("Text Me")')
                        text_me_button.first.click()
                        time.sleep(2)

                        # Click "Mobile App"
                        mobile_app_option = login_page.locator('div.oj-idaas-signin-buttonset-label:has-text("Mobile App")')
                        mobile_app_option.click()
                        time.sleep(2)

                        # Click "Phone Number" again
                        phone_option.click()
                        time.sleep(2)

                        # Click "Text Me" (second time)
                        text_me_button.click()
                        time.sleep(2)

                        logger.success(f"{runner_id}: Completed loop {loop_num + 1}/4 for phone {phone_number}")

                    except Exception as e:
                        logger.warning(f"{runner_id}: Error in loop {loop_num + 1}: {e}")
                        time.sleep(2)

            logger.success(f"{runner_id}: 2FA setup completed for account {temp_email}")
            browser.close()
            return True

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('oracle_failed', f"{email}:{password} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            return False


def run_worker(index, password, progress_bar):
    """Worker function to process a single account"""
    runner_id = f"Worker-{index + 1}"

    # Get 2 phone numbers for this account
    phone1 = get_next_phone()
    phone2 = get_next_phone()
    phone_numbers_for_account = [phone1, phone2]

    logger.info(f"{runner_id}: Starting Oracle automation with phones {phone1}, {phone2}")
    oracle_login_and_2fa(None, password, phone_numbers_for_account, runner_id)

    if progress_bar:
        progress_bar.update(1)


if __name__ == "__main__":
    clear_console()
    logger.info("Oracle Account Creation & 2FA Setup Script")
    logger.info("=" * 50)

    # Load password from file
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            password = file.read().strip()
        logger.info(f"Loaded password from password.txt")
    except FileNotFoundError:
        logger.error("'password.txt' not found. Create a file with the password to use")
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

    # Calculate how many accounts we can create (each account uses 2 phone numbers)
    num_accounts = len(phone_numbers) // 2
    logger.info(f"Can create {num_accounts} accounts with {len(phone_numbers)} phone numbers")

    if num_accounts == 0:
        logger.error("Need at least 2 phone numbers to create 1 account")
        exit(1)

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=num_accounts, desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: run_worker(i, password, progress_bar), range(num_accounts))

    logger.success("Script finished!")
    input('Press Enter to exit...')
