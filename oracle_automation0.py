import os
import time
import random
import string
import re
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
from loguru import logger
from threading import Lock
from tqdm import tqdm

# Global lock for thread-safe file operations
file_lock = Lock()
country_name = ""
country_code = ""


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def generate_random_string(length=8):
    """Generate random alphabetical string"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def generate_random_numbers(length=8):
    """Generate random numerical string"""
    return ''.join(random.choices(string.digits, k=length))


def get_mailtm_email(page, runner_id):
    """Get temporary email from mail.tm"""
    logger.info(f"{runner_id}: Opening mail.tm to get temporary email...")

    try:
        page.goto("https://mail.tm/en/", wait_until="domcontentloaded", timeout=30000)
        logger.info(f"{runner_id}: Page loaded, waiting for email to appear...")
        time.sleep(2)

        email = None
        max_attempts = 15

        for attempt in range(max_attempts):
            # Method 1: Try to get from input field
            try:
                email_input = page.locator('input#Dont_use_WEB_use_API_OK')
                if email_input.count() > 0:
                    email = email_input.get_attribute('value')
                    if email and email != "..." and '@' in email:
                        logger.success(f"{runner_id}: Got email: {email}")
                        return email
            except:
                pass

            # Method 2: Try JavaScript extraction
            try:
                email = page.evaluate(
                    """
                    () => {
                        const input = document.getElementById('Dont_use_WEB_use_API_OK');
                        if (input && input.value && input.value.includes('@')) {
                            return input.value;
                        }
                        const bodyText = document.body.innerText;
                        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
                        const matches = bodyText.match(emailRegex);
                        if (matches && matches.length > 0) {
                            for (let email of matches) {
                                if (email.includes('.')) {
                                    return email;
                                }
                            }
                        }
                        return '';
                    }
                    """
                )

                if email and '@' in email and '.' in email:
                    logger.success(f"{runner_id}: Got email: {email}")
                    return email
            except Exception as e:
                logger.debug(f"{runner_id}: JavaScript method failed: {e}")

            logger.info(f"{runner_id}: Attempt {attempt + 1}/{max_attempts} - waiting...")
            time.sleep(1)

        logger.error(f"{runner_id}: Failed to get email after {max_attempts} attempts")
        return None

    except Exception as e:
        logger.error(f"{runner_id}: Failed to get email from mail.tm: {e}")
        return None


def wait_for_oracle_verification_email(page, runner_id):
    """Wait for and extract Oracle verification link from mail.tm"""
    logger.info(f"{runner_id}: Waiting for Oracle verification email...")

    max_wait = 120
    start_time = time.time()
    first_check = True

    while time.time() - start_time < max_wait:
        try:
            if not first_check:
                page.reload(wait_until="domcontentloaded", timeout=10000)
                time.sleep(1)
            else:
                first_check = False
                time.sleep(1)

            oracle_message = None

            # Look for Oracle email
            try:
                spans = page.locator('span.truncate')
                count = spans.count()

                for i in range(count):
                    span = spans.nth(i)
                    text = span.inner_text()
                    if 'oracle-acct_ww@oracle.com' in text.lower():
                        oracle_message = span.locator('xpath=ancestor::li').first
                        logger.success(f"{runner_id}: Found Oracle email!")
                        break
            except:
                pass

            # Fallback: check for any message
            if not oracle_message:
                try:
                    clickable_messages = page.locator('li.cursor-pointer, li[role="button"]')
                    if clickable_messages.count() > 0:
                        oracle_message = clickable_messages.first
                except:
                    pass

            if oracle_message:
                logger.info(f"{runner_id}: Clicking on message...")
                oracle_message.click()
                time.sleep(3)

                # Extract verification link
                try:
                    verify_link = page.locator('a[href*="verify.jspx"]').first
                    verify_url = verify_link.get_attribute('href', timeout=5000)

                    if verify_url:
                        logger.success(f"{runner_id}: Found verification URL!")
                        return verify_url
                except:
                    pass

                # Fallback: regex extraction
                page_content = page.content()
                url_pattern = r'https://profile\.oracle\.com/myprofile/account/verify\.jspx\?key=[A-F0-9]+'
                match = re.search(url_pattern, page_content)

                if match:
                    verify_url = match.group(0)
                    logger.success(f"{runner_id}: Found verification URL via regex!")
                    return verify_url
                else:
                    try:
                        page.go_back()
                        time.sleep(2)
                    except:
                        pass

        except Exception as e:
            logger.debug(f"{runner_id}: Waiting... {e}")
            pass

        time.sleep(5)

    logger.error(f"{runner_id}: Verification email not received")
    return None


def verify_email(verify_url, page, runner_id):
    """Open verification URL"""
    try:
        logger.info(f"{runner_id}: Opening verification URL...")
        verify_page = page.context.new_page()
        verify_page.goto(verify_url, wait_until="domcontentloaded")
        time.sleep(3)

        page_content = verify_page.content()

        if 'Success. Your account is ready to use.' in page_content or 'x289' in page_content:
            logger.success(f"{runner_id}: Email verified successfully!")
        else:
            logger.info(f"{runner_id}: Verification page opened")

        verify_page.close()
        return True

    except Exception as e:
        logger.error(f"{runner_id}: Error during verification: {e}")
        return False


def create_oracle_account(page, email, password, runner_id):
    """Create Oracle account"""
    logger.info(f"{runner_id}: Creating Oracle account...")

    oracle_page = page.context.new_page()

    logger.info(f"{runner_id}: Loading Oracle registration page...")
    oracle_page.goto("https://profile.oracle.com/myprofile/account/create-account.jspx",
                      wait_until="domcontentloaded", timeout=20000)

    # Wait for form
    country_select = oracle_page.locator('select#sView1\\:r1\\:0\\:country\\:\\:content')
    country_select.wait_for(state="visible", timeout=10000)

    # Select country
    logger.info(f"{runner_id}: Selecting country ({country_name})...")
    time.sleep(0.3)

    box = country_select.bounding_box()
    if box:
        x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
        y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
        oracle_page.mouse.move(x, y)
        time.sleep(0.2)

    country_select.click()
    time.sleep(0.3)

    # Find country option value from the country code
    # Extract just the code part (e.g., "EG" from "Egypt +20")
    oracle_page.locator(f'select#sView1\\:r1\\:0\\:country\\:\\:content').select_option(label=country_name)
    time.sleep(0.3)

    # Fill email
    logger.info(f"{runner_id}: Filling form with email: {email}")
    email_input = oracle_page.locator('input#sView1\\:r1\\:0\\:email\\:\\:content')
    email_input.wait_for(state="visible", timeout=10000)
    email_input.fill(email)
    time.sleep(0.2)

    # Fill password
    password_input = oracle_page.locator('input#sView1\\:r1\\:0\\:password\\:\\:content')
    password_input.fill(password)
    time.sleep(0.2)

    # Retype password
    retype_password_input = oracle_page.locator('input#sView1\\:r1\\:0\\:retypePassword\\:\\:content')
    retype_password_input.fill(password)
    time.sleep(0.2)

    # Fill personal details
    first_name = generate_random_string(8)
    last_name = generate_random_string(8)
    job_title = generate_random_string(8)
    work_phone = generate_random_numbers(8)
    company_name = generate_random_string(8)
    address = generate_random_string(8)
    city = generate_random_string(8)
    postal_code = generate_random_numbers(8)

    logger.info(f"{runner_id}: Filling personal details...")

    oracle_page.locator('input#sView1\\:r1\\:0\\:firstName\\:\\:content').fill(first_name)
    oracle_page.locator('input#sView1\\:r1\\:0\\:lastName\\:\\:content').fill(last_name)
    oracle_page.locator('input#sView1\\:r1\\:0\\:jobTitle\\:\\:content').fill(job_title)
    oracle_page.locator('input#sView1\\:r1\\:0\\:workPhone\\:\\:content').fill(work_phone)
    oracle_page.locator('input#sView1\\:r1\\:0\\:companyName\\:\\:content').fill(company_name)
    oracle_page.locator('input#sView1\\:r1\\:0\\:address1\\:\\:content').fill(address)
    oracle_page.locator('input#sView1\\:r1\\:0\\:city\\:\\:content').fill(city)
    oracle_page.locator('input#sView1\\:r1\\:0\\:postalCode\\:\\:content').fill(postal_code)

    time.sleep(0.5)

    # Click Create Account
    logger.info(f"{runner_id}: Clicking Create Account button...")
    create_button = oracle_page.locator('div#sView1\\:r1\\:0\\:b1 a')
    create_button.scroll_into_view_if_needed()
    time.sleep(0.3)
    create_button.wait_for(state="visible", timeout=10000)
    create_button.click()

    logger.info(f"{runner_id}: Account creation submitted...")
    time.sleep(2)

    return oracle_page


def create_account_worker(index, password, progress_bar):
    """Worker to create a single Oracle account"""
    runner_id = f"Worker-{index + 1}"

    logger.info(f"{runner_id}: Starting account creation...")

    with sync_playwright() as playwright:
        try:
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

            # Get temporary email
            temp_email = get_mailtm_email(page, runner_id)
            if not temp_email:
                logger.error(f"{runner_id}: Failed to get email")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return False

            # Create Oracle account
            oracle_page = create_oracle_account(page, temp_email, password, runner_id)

            # Wait for verification email
            logger.info(f"{runner_id}: Switching to mail.tm to check for verification email...")
            page.bring_to_front()
            time.sleep(0.5)

            verify_url = wait_for_oracle_verification_email(page, runner_id)

            if not verify_url:
                logger.error(f"{runner_id}: Failed to get verification URL")
                savecreated('oracle_failed', f"{temp_email}:{password} - No verification email")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return False

            # Verify email
            if not verify_email(verify_url, page, runner_id):
                logger.error(f"{runner_id}: Verification failed")
                savecreated('oracle_failed', f"{temp_email}:{password} - Verification failed")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return False

            # Save successful account
            savecreated('oracle_accounts', f"{temp_email}:{password}")
            logger.success(f"{runner_id}: Account created successfully: {temp_email}")

            browser.close()
            if progress_bar:
                progress_bar.update(1)
            return True

        except Exception as e:
            logger.error(f"{runner_id}: Failed - {e}")
            savecreated('oracle_failed', f"Unknown:{password} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)
            return False


if __name__ == "__main__":
    clear_console()
    logger.info("Oracle Account Creation Script (No Login/2FA)")
    logger.info("=" * 60)

    # Load password
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            password = file.read().strip()
        logger.info(f"Loaded password from password.txt")
    except FileNotFoundError:
        logger.error("'password.txt' not found")
        exit(1)

    # Load country
    try:
        with open("country.txt", "r", encoding="utf8") as file:
            country_line = file.read().strip()
            if country_line and '+' in country_line:
                parts = country_line.rsplit('+', 1)
                country_name = parts[0].strip()
                country_code = '+' + parts[1].strip()
                logger.info(f"Loaded country: {country_name} {country_code}")
            else:
                logger.error("Invalid format in country.txt. Expected: 'Egypt +20'")
                exit(1)
    except FileNotFoundError:
        logger.error("'country.txt' not found")
        exit(1)

    # Ask for number of accounts and workers
    num_accounts = int(input('Number of accounts to create: '))
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=num_accounts, desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda i: create_account_worker(i, password, progress_bar), range(num_accounts))

    logger.success("Script finished!")
    input('Press Enter to exit...')
