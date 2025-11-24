import os
import sys
import time
import threading
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration
HEADLESS = False  # Set to True to hide browser

# File paths
ACCOUNTS_FILE = "accounts.txt"
NUMBERS_FILE = "numbers.txt"

# Thread lock for file operations
file_lock = threading.Lock()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

def clear_console():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_file_lines(filepath):
    """Read all non-empty lines from a file"""
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return []

    with file_lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            return lines
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return []

def remove_line_from_file(filepath, line_to_remove):
    """Remove a specific line from a file"""
    with file_lock:
        try:
            if not os.path.exists(filepath):
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            with open(filepath, 'w', encoding='utf-8') as f:
                for line in lines:
                    if line.strip() != line_to_remove.strip():
                        f.write(line)

            logger.info(f"Removed from {filepath}: {line_to_remove}")
        except Exception as e:
            logger.error(f"Error removing line from {filepath}: {e}")

def process_paypal_lesotho_signup(account_email, phone_number):
    """Process a single PayPal Lesotho account signup"""

    logger.info("=" * 60)
    logger.info(f"Processing: {account_email}")
    logger.info(f"Phone: {phone_number}")
    logger.info("=" * 60)

    try:
        with sync_playwright() as p:
            # Launch browser with stealth args
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--start-maximized'
                ]
            )

            # Create stealth context
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Africa/Johannesburg',
                no_viewport=True,
                ignore_https_errors=False
            )

            page = context.new_page()

            # Add comprehensive stealth JavaScript
            page.add_init_script("""
                // Overwrite webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // Mock plugins with realistic data
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', filename: 'internal-nacl-plugin'}
                    ],
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                // Chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };

                // Permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Hide automation
                delete navigator.__proto__.webdriver;

                // Canvas fingerprint spoofing
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function() {
                    if (this.width === 16 && this.height === 16) {
                        return originalToDataURL.apply(this, arguments);
                    }
                    const context = this.getContext('2d');
                    const shift = {
                        'r': Math.floor(Math.random() * 10) - 5,
                        'g': Math.floor(Math.random() * 10) - 5,
                        'b': Math.floor(Math.random() * 10) - 5,
                        'a': Math.floor(Math.random() * 10) - 5
                    };
                    return originalToDataURL.apply(this, arguments);
                };

                // WebGL fingerprint spoofing
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.call(this, parameter);
                };

                // Hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4,
                });

                // Device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });
            """)

            # Step 1: Open PayPal Lesotho signup page
            logger.info("Opening PayPal Lesotho signup page...")
            page.goto("https://www.paypal.com/ls/welcome/signup/#/login_info_phone", wait_until="networkidle", timeout=60000)

            # Human-like behavior after page load
            import random
            page.wait_for_timeout(random.randint(2000, 4000))

            # Random mouse movements
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                page.mouse.move(x, y)
                page.wait_for_timeout(random.randint(300, 800))

            # Random scroll
            page.evaluate("window.scrollBy(0, {})".format(random.randint(100, 300)))
            page.wait_for_timeout(random.randint(1000, 2000))
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(random.randint(500, 1500))

            # Step 2: Select Lesotho from country dropdown
            logger.info("Selecting Lesotho from country dropdown...")
            try:
                country_input = page.locator('input[name="combo_t_/paypalAccountData/countryselector"]')
                country_input.wait_for(state="visible", timeout=10000)

                # Move mouse to element first
                box = country_input.bounding_box()
                if box:
                    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    page.wait_for_timeout(random.randint(300, 700))

                country_input.click()
                page.wait_for_timeout(random.randint(800, 1500))

                # Type Lesotho with human-like delays
                country_input.fill("")
                page.wait_for_timeout(random.randint(300, 600))
                country_input.type("Lesotho", delay=random.randint(80, 150))
                page.wait_for_timeout(random.randint(800, 1500))

                # Press Enter to select
                page.keyboard.press("Enter")
                page.wait_for_timeout(random.randint(1500, 2500))
                logger.success("Selected Lesotho")
            except Exception as e:
                logger.error(f"Error selecting Lesotho: {e}")
                browser.close()
                return False

            # Step 3: Click Get Started
            logger.info("Clicking Get Started...")
            try:
                get_started_btn = page.locator('button[id="paypalAccountData_submit"]')
                get_started_btn.wait_for(state="visible", timeout=10000)
                get_started_btn.click()
                page.wait_for_timeout(5000)
            except Exception as e:
                logger.error(f"Error clicking Get Started: {e}")
                browser.close()
                return False

            # Step 4: Enter email
            logger.info(f"Entering email: {account_email}")
            try:
                email_input = page.locator('input[type="email"][name="/paypalAccountData/email"]')
                email_input.wait_for(state="visible", timeout=15000)

                # Move mouse and click
                box = email_input.bounding_box()
                if box:
                    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    page.wait_for_timeout(random.randint(300, 700))

                email_input.click()
                page.wait_for_timeout(random.randint(400, 800))

                # Type email with human delays
                email_input.type(account_email, delay=random.randint(70, 130))
                page.wait_for_timeout(random.randint(800, 1500))
            except Exception as e:
                logger.error(f"Error entering email: {e}")
                browser.close()
                return False

            # Step 5: Click Next (after email)
            logger.info("Clicking Next (after email)...")
            try:
                next_btn = page.locator('button[id="paypalAccountData_submit"][value="login_info_phone"]')
                next_btn.wait_for(state="visible", timeout=10000)
                next_btn.click()
                page.wait_for_timeout(5000)
            except Exception as e:
                logger.error(f"Error clicking Next after email: {e}")
                browser.close()
                return False

            # Step 6: Enter phone number
            logger.info(f"Entering phone number: {phone_number}")
            try:
                phone_input = page.locator('input[type="tel"][id*="paypalAccountData_ph"]')
                phone_input.wait_for(state="visible", timeout=15000)

                # Move mouse and click
                box = phone_input.bounding_box()
                if box:
                    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    page.wait_for_timeout(random.randint(300, 700))

                phone_input.click()
                page.wait_for_timeout(random.randint(400, 800))

                # Type phone with human delays
                phone_input.type(phone_number, delay=random.randint(70, 130))
                page.wait_for_timeout(random.randint(800, 1500))
            except Exception as e:
                logger.error(f"Error entering phone number: {e}")
                browser.close()
                return False

            # Step 7: Click Next (after phone)
            logger.info("Clicking Next (after phone)...")
            try:
                next_phone_btn = page.locator('button[id="paypalAccountData_submit"][value="init_phone_confirmation"]')
                next_phone_btn.wait_for(state="visible", timeout=10000)
                next_phone_btn.click()
                page.wait_for_timeout(5000)
            except Exception as e:
                logger.error(f"Error clicking Next after phone: {e}")
                browser.close()
                return False

            # Step 8: Click Resend code repeatedly until error appears
            logger.info("Clicking 'Resend code' repeatedly...")
            resend_count = 0
            max_attempts = 100

            while resend_count < max_attempts:
                try:
                    # Check for error message first
                    error_message = page.locator('span:has-text("Sorry, we can\'t send a new code right now")')
                    if error_message.is_visible(timeout=2000):
                        logger.success("Error message appeared! Stopping...")
                        break

                    # Click Resend code button
                    resend_btn = page.locator('button[id="paypalAccountData_nextBtn"][data-automation-id="send_again"]')
                    if resend_btn.is_visible(timeout=3000):
                        resend_btn.click()
                        resend_count += 1
                        logger.info(f"Clicked 'Resend code' #{resend_count}")
                        page.wait_for_timeout(2000)
                    else:
                        logger.warning("Resend button not visible, checking for error...")
                        page.wait_for_timeout(2000)

                except Exception as e:
                    logger.info(f"Checking for error message... (attempt {resend_count})")

                    # Final check for error
                    try:
                        error_message = page.locator('span:has-text("Sorry, we can\'t send a new code right now")')
                        if error_message.is_visible(timeout=2000):
                            logger.success("Error message appeared! Stopping...")
                            break
                    except:
                        pass

                    page.wait_for_timeout(2000)

            logger.success(f"Finished processing {account_email}")
            logger.info(f"Total 'Resend code' clicks: {resend_count}")

            # Close browser
            page.wait_for_timeout(2000)
            browser.close()

            # Remove used account and phone number from files
            remove_line_from_file(ACCOUNTS_FILE, account_email)
            remove_line_from_file(NUMBERS_FILE, phone_number)

            return True

    except Exception as e:
        logger.error(f"Error processing {account_email}: {e}")
        return False

def main():
    """Main function to run PayPal Lesotho automation"""
    clear_console()

    logger.info("PayPal Lesotho Account Creation Automation - V1")
    logger.info("=" * 60)

    # Read all required files
    accounts = read_file_lines(ACCOUNTS_FILE)
    numbers = read_file_lines(NUMBERS_FILE)

    if not accounts:
        logger.error(f"No accounts found in {ACCOUNTS_FILE}")
        return

    if not numbers:
        logger.error(f"No phone numbers found in {NUMBERS_FILE}")
        return

    # Check counts
    min_count = min(len(accounts), len(numbers))
    logger.info(f"Accounts: {len(accounts)} | Numbers: {len(numbers)}")
    logger.info(f"Will process: {min_count} accounts")
    logger.info("=" * 60)

    # Process accounts sequentially
    success_count = 0
    fail_count = 0

    for i in range(min_count):
        account = accounts[i]
        number = numbers[i]

        logger.info(f"\nProcessing account {i+1}/{min_count}")

        result = process_paypal_lesotho_signup(account, number)

        if result:
            success_count += 1
        else:
            fail_count += 1

        # Small delay between accounts
        if i < min_count - 1:
            logger.info("Waiting 5 seconds before next account...")
            time.sleep(5)

    # Final summary
    logger.info("=" * 60)
    logger.info("AUTOMATION COMPLETE!")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
