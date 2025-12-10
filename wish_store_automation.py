import os
import time
import random
import string
import base64
import requests
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from undetected_playwright import stealth_sync
from loguru import logger
from threading import Lock
from tqdm import tqdm

# Global lock for thread-safe file operations
file_lock = Lock()

# YesCaptcha API configuration
YESCAPTCHA_CLIENT_KEY = "8d381f04402598ed227557a6acb91a6da1a909c375946"


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def savecreated(filename, message):
    """Save results to file in a thread-safe manner"""
    workcard = filename + '.txt'
    with file_lock:
        with open(workcard, "a", encoding="utf8") as file:
            file.writelines(message + '\n')


def generate_random_store_name(length=12):
    """Generate a random store name with letters and numbers"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def solve_captcha_yescaptcha(image_base64):
    """
    Solve captcha using YesCaptcha API
    Returns the solved text or None if failed
    """
    try:
        # Create task
        data = {
            "clientKey": YESCAPTCHA_CLIENT_KEY,
            "task": {
                "type": "ImageToTextTaskMuggle",
                "body": image_base64
            }
        }

        logger.info("Sending captcha to YesCaptcha API...")
        response = requests.post("https://api.yescaptcha.com/createTask", json=data, timeout=30)
        result = response.json()

        if result.get("errorId") != 0:
            logger.error(f"YesCaptcha API error: {result.get('errorDescription')}")
            return None

        task_id = result.get("taskId")
        logger.info(f"Task created: {task_id}, waiting for solution...")

        # Poll for result (max 60 seconds)
        for attempt in range(30):  # 30 attempts * 2 seconds = 60 seconds
            time.sleep(2)

            get_result_data = {
                "clientKey": YESCAPTCHA_CLIENT_KEY,
                "taskId": task_id
            }

            get_response = requests.post("https://api.yescaptcha.com/getTaskResult", json=get_result_data, timeout=30)
            get_result = get_response.json()

            if get_result.get("status") == "ready":
                captcha_text = get_result.get("solution", {}).get("text")
                logger.success(f"Captcha solved: {captcha_text}")
                return captcha_text
            elif get_result.get("status") == "processing":
                logger.info(f"Still processing... (attempt {attempt + 1}/30)")
                continue
            else:
                logger.error(f"Unexpected status: {get_result.get('status')}")
                return None

        logger.error("Captcha solving timeout")
        return None

    except Exception as e:
        logger.error(f"Error solving captcha: {e}")
        return None


def human_like_type(page, locator, text):
    """Simulate human-like typing with random delays"""
    locator.click()
    time.sleep(random.uniform(0.1, 0.3))

    for char in text:
        locator.type(char)
        time.sleep(random.uniform(0.05, 0.15))


def human_like_click(page, locator):
    """Simulate human-like click with mouse movement and delays"""
    try:
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
    except:
        # Final fallback
        locator.click()


def wish_store_automation(email, password, store_password, runner_id, progress_bar):
    """
    Automates Wish merchant store setup
    """
    url = "https://merchant.wish.com/open-express?r=802OI"

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

            # Navigate to Wish merchant signup
            logger.info(f"{runner_id}: Navigating to Wish merchant signup...")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)

            # Step 1: Generate and fill store name (12 random characters)
            store_name = generate_random_store_name(12)
            logger.info(f"{runner_id}: Generated store name: {store_name}")

            try:
                store_name_input = page.locator('input.inputBase_1os68jb-o_O-input_sqerl5[placeholder="Create a name for your store"]').first
                store_name_input.wait_for(state="visible", timeout=15000)
                human_like_type(page, store_name_input, store_name)
                time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                logger.error(f"{runner_id}: Error entering store name: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 2: Fill email address
            logger.info(f"{runner_id}: Entering email: {email}")
            try:
                email_input = page.locator('input.inputBase_1os68jb-o_O-input_sqerl5[placeholder="Enter your email address"]').first
                email_input.wait_for(state="visible", timeout=10000)
                human_like_type(page, email_input, email)
                time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                logger.error(f"{runner_id}: Error entering email: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 3: Fill password
            logger.info(f"{runner_id}: Entering password...")
            try:
                password_input = page.locator('input[type="password"].inputBase_1os68jb-o_O-input_sqerl5[placeholder="Create a password"]').first
                password_input.wait_for(state="visible", timeout=10000)
                human_like_type(page, password_input, store_password)
                time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                logger.error(f"{runner_id}: Error entering password: {e}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 4: Get captcha image and solve it
            logger.info(f"{runner_id}: Looking for captcha image...")
            try:
                # Wait for captcha image to load
                captcha_img = page.locator('img.image_1sjo3yd').first
                captcha_img.wait_for(state="visible", timeout=10000)
                time.sleep(1)

                # Get the captcha image src
                captcha_src = captcha_img.get_attribute("src")
                logger.info(f"{runner_id}: Captcha image found: {captcha_src}")

                # Fetch the captcha image
                if captcha_src.startswith('/'):
                    # Relative URL, construct full URL
                    captcha_url = f"https://merchant.wish.com{captcha_src}"
                else:
                    captcha_url = captcha_src

                # Download captcha image
                logger.info(f"{runner_id}: Downloading captcha from: {captcha_url}")
                captcha_response = page.request.get(captcha_url)
                captcha_image_bytes = captcha_response.body()

                # Convert to base64
                captcha_base64 = base64.b64encode(captcha_image_bytes).decode('utf-8')
                logger.info(f"{runner_id}: Captcha converted to base64 (length: {len(captcha_base64)})")

                # Solve captcha using YesCaptcha
                captcha_solution = solve_captcha_yescaptcha(captcha_base64)

                if not captcha_solution:
                    logger.error(f"{runner_id}: Failed to solve captcha")
                    savecreated('failed', f"{email} - Failed to solve captcha")
                    browser.close()
                    if progress_bar:
                        progress_bar.update(1)
                    return

                # Fill captcha solution
                logger.info(f"{runner_id}: Entering captcha solution: {captcha_solution}")
                captcha_input = page.locator('input.inputBase_1os68jb-o_O-input_sqerl5[placeholder="Code in the picture"]').first
                captcha_input.wait_for(state="visible", timeout=10000)
                human_like_type(page, captcha_input, captcha_solution)
                time.sleep(random.uniform(0.5, 1.0))

            except Exception as e:
                logger.error(f"{runner_id}: Error handling captcha: {e}")
                savecreated('failed', f"{email} - Error handling captcha: {str(e)}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            # Step 5: Click Continue button
            logger.info(f"{runner_id}: Clicking Continue button...")
            try:
                continue_button = page.locator('button.root_1vrerfk-o_O-rootEnabled_1d8zzey').first
                continue_button.wait_for(state="visible", timeout=10000)
                time.sleep(random.uniform(0.5, 1.5))
                human_like_click(page, continue_button)

                # Wait to see result
                time.sleep(5)

                # Check for success or errors
                current_url = page.url
                logger.info(f"{runner_id}: Current URL after submit: {current_url}")

                # Check if there's an error message
                try:
                    error_message = page.locator('div[class*="error"], span[class*="error"]').first
                    if error_message.is_visible(timeout=2000):
                        error_text = error_message.inner_text()
                        logger.warning(f"{runner_id}: Error message found: {error_text}")
                        savecreated('failed', f"{email} - Error: {error_text}")
                    else:
                        logger.success(f"{runner_id}: Store created successfully!")
                        savecreated('completed', f"{email}:{password} - Store: {store_name}")
                except:
                    # No error found, assume success
                    logger.success(f"{runner_id}: Store created successfully!")
                    savecreated('completed', f"{email}:{password} - Store: {store_name}")

            except Exception as e:
                logger.error(f"{runner_id}: Error clicking Continue: {e}")
                savecreated('failed', f"{email} - Error clicking Continue: {str(e)}")
                browser.close()
                if progress_bar:
                    progress_bar.update(1)
                return

            time.sleep(3)
            browser.close()
            if progress_bar:
                progress_bar.update(1)

        except Exception as e:
            logger.error(f"{runner_id}: Automation failed - {e}")
            savecreated('failed', f"{email} - Error: {str(e)}")
            try:
                browser.close()
            except:
                pass
            if progress_bar:
                progress_bar.update(1)


def run_worker(index, email, password, store_password, progress_bar):
    """
    Worker function to process a single account
    """
    runner_id = f"Worker-{index + 1}"

    logger.info(f"{runner_id}: Starting automation for {email}")
    wish_store_automation(email, password, store_password, runner_id, progress_bar)


if __name__ == "__main__":
    clear_console()
    logger.info("Wish Merchant Store Setup Automation Script")
    logger.info("=" * 50)

    # Load accounts from file (format: email:password)
    try:
        with open("accounts.txt", "r", encoding="utf8") as file:
            accounts = []
            for line in file:
                line = line.strip()
                if line and ':' in line:
                    email, password = line.split(':', 1)
                    accounts.append((email, password))
        logger.info(f"Loaded {len(accounts)} accounts from accounts.txt")
    except FileNotFoundError:
        logger.error("'accounts.txt' not found. Create a file with accounts (email:password format, one per line)")
        exit(1)

    if len(accounts) == 0:
        logger.error("No accounts loaded. Please add accounts to accounts.txt")
        exit(1)

    # Load store password from file (single password for all stores)
    try:
        with open("password.txt", "r", encoding="utf8") as file:
            store_password = file.read().strip()
        logger.info(f"Loaded store password from password.txt")
    except FileNotFoundError:
        logger.error("'password.txt' not found. Create a file with the store password")
        exit(1)

    if not store_password:
        logger.error("No password found in password.txt")
        exit(1)

    # Create tasks
    tasks = []
    for i, (email, password) in enumerate(accounts):
        tasks.append((i, email, password, store_password))

    logger.info(f"Created {len(tasks)} tasks")

    # Ask for number of workers
    num_workers = int(input('Number of concurrent workers: '))

    # Initialize progress bar
    with tqdm(total=len(tasks), desc="Progress", unit="account") as progress_bar:
        # Execute workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(lambda task: run_worker(task[0], task[1], task[2], task[3], progress_bar), tasks)

    logger.success("Script finished!")
    input('Press Enter to exit...')
