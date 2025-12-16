import asyncio
import random
import string
import re
import aiohttp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime
import sys

# Configuration
MAX_EMAIL_ATTEMPTS = 15
SMS_RESEND_COUNT = 4

def random_name(length):
    """Generate random name"""
    letters = string.ascii_lowercase
    name = ''.join(random.choice(letters) for _ in range(length))
    return name.capitalize()

def clean_link(html_content):
    """Extract and clean verification link from email"""
    match = re.search(r'href="(https://wolt\.com/me/magic_login[^"]+)"', html_content)
    if not match:
        return None
    return match.group(1).replace('&amp;', '&')

async def get_temp_email(api_key, session):
    """Get temp email from API"""
    try:
        async with session.get(f'https://free.priyo.email/api/random-email/{api_key}', timeout=10) as resp:
            text = await resp.text()
            match = re.search(r'"email":"([^"]+)","password":"([^"]+)"', text)
            if match:
                return match.group(1), match.group(2)
    except Exception as e:
        print(f"❌ Error getting email: {e}")
    return None, None

async def get_verification_link(email, api_key, session, max_attempts=MAX_EMAIL_ATTEMPTS):
    """Poll API for verification email"""
    for attempt in range(max_attempts):
        try:
            await asyncio.sleep(2)  # Reduced from 3 to 2 seconds
            async with session.get(f'https://free.priyo.email/api/messages/{email}/{api_key}', timeout=10) as resp:
                messages = await resp.json()

                if messages and isinstance(messages, list):
                    for msg in messages:
                        if msg.get('sender_email') == 'info@wolt.com' and 'Welcome to Wolt' in msg.get('subject', ''):
                            link = clean_link(msg.get('content', ''))
                            if link:
                                return link
        except Exception as e:
            if attempt % 5 == 0:
                print(f"  ⏳ Checking inbox... attempt {attempt + 1}/{max_attempts}")
            continue
    return None

async def create_account(worker_num, api_key, phone_number):
    """Create single Wolt account"""
    browser = None
    start_time = datetime.now()

    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Get temp email
            print(f"\n[Worker {worker_num}] 📧 Getting temp email...")
            email, password = await get_temp_email(api_key, session)

            if not email:
                print(f"[Worker {worker_num}] ❌ Failed to get email")
                return False

            print(f"[Worker {worker_num}] ✅ Email: {email}")

            # Step 2: Start browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            page.set_default_timeout(15000)  # 15 seconds timeout

            # Step 3: Go to Wolt
            print(f"[Worker {worker_num}] 🌐 Opening Wolt...")
            await page.goto('https://wolt.com/', wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Step 3.5: Handle cookie consent (ALWAYS appears)
            try:
                print(f"[Worker {worker_num}] 🍪 Waiting for cookie modal...")
                # Wait for cookie modal to appear
                cookie_button = page.locator('button[data-test-id="decline-button"]')
                await cookie_button.wait_for(state='visible', timeout=8000)
                print(f"[Worker {worker_num}] 🍪 Declining cookies...")
                await cookie_button.click()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"[Worker {worker_num}] ⚠️  Cookie modal not found: {str(e)[:50]}")

            # Step 4: Click Sign up
            print(f"[Worker {worker_num}] 🖱️  Clicking Sign up...")
            await page.click('button[data-test-id="UserStatus.Signup"]', timeout=10000)
            await asyncio.sleep(1.5)

            # Step 5: Enter email in modal (NOT iframe)
            print(f"[Worker {worker_num}] 📝 Entering email...")
            await page.locator('input[data-test-id="MethodSelect.EmailInput"]').fill(email)
            await asyncio.sleep(0.5)

            # Step 6: Click Continue
            await page.locator('button[data-test-id="StepMethodSelect.NextButton"]').click()

            # Step 7: Wait for confirmation
            print(f"[Worker {worker_num}] ⏳ Waiting for email confirmation...")
            # Use .first to avoid strict mode violation (2 elements match)
            await page.locator('h2:has-text("Great, check your inbox!")').first.wait_for(timeout=20000)
            print(f"[Worker {worker_num}] ✅ Email sent!")

            # Step 8: Get verification link
            print(f"[Worker {worker_num}] 📬 Fetching verification link...")
            verification_link = await get_verification_link(email, api_key, session)

            if not verification_link:
                print(f"[Worker {worker_num}] ❌ No verification email received")
                return False

            print(f"[Worker {worker_num}] ✅ Got verification link")

            # Step 9: Open verification link
            print(f"[Worker {worker_num}] 🔗 Opening verification link...")
            await page.goto(verification_link, wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Step 10: Fill registration form (try iframe first, fallback to page)
            # Check if form is in iframe or directly on page
            try:
                # Try iframe first
                frames = page.frames
                form_locator = None

                # Check if country input exists in iframe
                for frame in frames:
                    try:
                        country_input = frame.locator('input#CreateAccount\\.Country')
                        if await country_input.count() > 0:
                            print(f"[Worker {worker_num}] 📋 Found form in iframe")
                            form_locator = frame
                            break
                    except:
                        continue

                # If not found in iframe, use page directly
                if not form_locator:
                    print(f"[Worker {worker_num}] 📋 Form is on main page")
                    form_locator = page

                # Select Hungary
                print(f"[Worker {worker_num}] 🇭🇺 Selecting Hungary...")
                country_input = form_locator.locator('input#CreateAccount\\.Country')
                await country_input.click()
                await asyncio.sleep(0.5)
                await country_input.press_sequentially("Hun", delay=50)
                await asyncio.sleep(0.3)
                await country_input.press("Enter")
                await asyncio.sleep(0.5)

                # Generate names
                first_name = random_name(9)
                last_name = random_name(10)

                # Enter names
                print(f"[Worker {worker_num}] 👤 Entering name: {first_name} {last_name}")
                await form_locator.locator('input[data-test-id="CreateAccount.FirstName"]').fill(first_name)
                await asyncio.sleep(0.3)
                await form_locator.locator('input[data-test-id="CreateAccount.LastName"]').fill(last_name)
                await asyncio.sleep(0.3)

                # Select Ukraine phone code
                print(f"[Worker {worker_num}] 🇺🇦 Selecting Ukraine (+380)...")
                phone_country_input = form_locator.locator('input#CreateAccount\\.PhoneNumberCountryCode')
                await phone_country_input.click()
                await asyncio.sleep(0.5)
                await phone_country_input.press_sequentially("Ukr", delay=50)
                await asyncio.sleep(0.3)
                await phone_country_input.press("Enter")
                await asyncio.sleep(0.5)

                # Enter phone number
                print(f"[Worker {worker_num}] 📱 Entering phone: +380{phone_number}")
                await form_locator.locator('input[data-test-id="CreateAccount.PhoneNumber"]').fill(phone_number)
                await asyncio.sleep(0.5)

                # Click Next
                await form_locator.locator('button[data-test-id="CreateAccount.Continue"]').click()
                await asyncio.sleep(2)

                # Click Send SMS
                print(f"[Worker {worker_num}] 📲 Sending SMS verification...")
                await form_locator.locator('button[data-test-id="VerifyPhoneNumberMethodSelect.SmsButton"]').click()
                await asyncio.sleep(2)

                # Resend SMS 4 times
                rate_limited = False
                for i in range(SMS_RESEND_COUNT):
                    print(f"[Worker {worker_num}] 🔄 Resend {i + 1}/{SMS_RESEND_COUNT}...")

                    # Click "I didn't get a code"
                    await form_locator.locator('button[data-test-id="VerifyCode.CodeNotReceived"]').click()
                    await asyncio.sleep(1)

                    # Click "Resend code by SMS"
                    await form_locator.locator('button[data-test-id="NoCodeReceived.SmsButton"]').click()
                    await asyncio.sleep(1.5)

                    # Check for rate limit error
                    try:
                        rate_limit_error = form_locator.locator('[data-test-id="NoCodeReceived.Error"]')
                        if await rate_limit_error.is_visible(timeout=2000):
                            print(f"[Worker {worker_num}] ⚠️  Rate limit reached! Moving to next account...")
                            rate_limited = True
                            break
                    except:
                        pass  # No error, continue

                if rate_limited:
                    print(f"[Worker {worker_num}] ⏭️  Skipping to next account due to rate limit")

            except Exception as form_error:
                print(f"[Worker {worker_num}] ❌ Form error: {str(form_error)[:100]}")
                raise

            # Save account info
            elapsed = (datetime.now() - start_time).total_seconds()
            account_info = f"Email: {email} | Password: {password} | Name: {first_name} {last_name} | Phone: +380{phone_number} | Time: {elapsed:.1f}s\n"

            with open('wolt_accounts.txt', 'a', encoding='utf-8') as f:
                f.write(account_info)

            print(f"[Worker {worker_num}] ✅ SUCCESS in {elapsed:.1f}s!")
            print(f"[Worker {worker_num}] 💾 Saved: {email} | +380{phone_number}")

            return True

    except PlaywrightTimeout as e:
        print(f"[Worker {worker_num}] ⏰ Timeout error: {str(e)[:100]}")
        return False
    except Exception as e:
        print(f"[Worker {worker_num}] ❌ Error: {str(e)[:150]}")
        return False
    finally:
        if browser:
            try:
                await browser.close()
            except:
                pass

async def main(workers):
    """Main function"""
    try:
        # Read API keys
        with open('keys.txt', 'r', encoding='utf-8') as f:
            keys = [line.strip() for line in f if line.strip()]

        if not keys:
            print("❌ No API keys found in keys.txt")
            return

        # Read phone numbers
        with open('numbers.txt', 'r', encoding='utf-8') as f:
            numbers = [line.strip() for line in f if line.strip()]

        if not numbers:
            print("❌ No phone numbers found in numbers.txt")
            return

        print(f"🚀 Starting with {len(keys)} API keys and {len(numbers)} phone numbers")
        print(f"⚙️  Workers: {workers} | SMS Resends: {SMS_RESEND_COUNT}\n")

        success_count = 0
        fail_count = 0

        # Process in batches
        for i in range(0, len(numbers), workers):
            batch = []

            for j in range(workers):
                index = i + j
                if index >= len(numbers):
                    break

                api_key = keys[index % len(keys)]
                phone = numbers[index]
                worker_num = index + 1

                batch.append(create_account(worker_num, api_key, phone))

            # Wait for batch to complete
            results = await asyncio.gather(*batch, return_exceptions=True)

            # Count results
            for result in results:
                if result is True:
                    success_count += 1
                else:
                    fail_count += 1

            print(f"\n{'='*60}")
            print(f"📊 Progress: {i + len(batch)}/{len(numbers)} | ✅ Success: {success_count} | ❌ Failed: {fail_count}")
            print(f"{'='*60}\n")

            # Small delay between batches
            if i + workers < len(numbers):
                await asyncio.sleep(2)

        print(f"\n🎉 DONE! Total: {len(numbers)} | ✅ Success: {success_count} | ❌ Failed: {fail_count}")

    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}")
        print("💡 Create keys.txt and numbers.txt files")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    print(f"{'='*60}")
    print("🍕 Wolt Account Creator")
    print(f"{'='*60}\n")

    # Ask user for number of workers
    while True:
        try:
            workers_input = input("How many workers do you need? (default 3): ").strip()

            # Use default if empty
            if workers_input == "":
                workers = 3
                break

            workers = int(workers_input)

            if workers < 1:
                print("❌ Workers must be at least 1. Try again.")
                continue
            elif workers > 10:
                confirm = input(f"⚠️  {workers} workers may cause issues. Continue? (y/n): ").lower()
                if confirm == 'y' or confirm == 'yes':
                    break
                else:
                    continue
            else:
                break

        except ValueError:
            print("❌ Please enter a valid number. Try again.")
            continue
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled by user")
            sys.exit(0)

    print(f"\n✅ Using {workers} worker(s)\n")

    asyncio.run(main(workers))
