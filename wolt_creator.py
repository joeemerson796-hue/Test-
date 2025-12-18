import asyncio
import random
import string
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime
import sys

# Configuration
SMS_RESEND_COUNT = 4

def random_name(length):
    """Generate random name"""
    letters = string.ascii_lowercase
    name = ''.join(random.choice(letters) for _ in range(length))
    return name.capitalize()

async def get_mailtm_email(mail_page, worker_num):
    """Get temporary email from mail.tm website"""
    print(f"[Worker {worker_num}] 📧 Opening mail.tm to get temporary email...")

    try:
        await mail_page.goto("https://mail.tm/en/", wait_until="domcontentloaded", timeout=30000)
        print(f"[Worker {worker_num}] ⏳ Waiting for email to appear...")
        await asyncio.sleep(2)

        email = None
        max_attempts = 15

        for attempt in range(max_attempts):
            # Method 1: Try to get from input field
            try:
                email_input = mail_page.locator('input#Dont_use_WEB_use_API_OK')
                if await email_input.count() > 0:
                    email = await email_input.get_attribute('value')
                    if email and email != "..." and '@' in email:
                        print(f"[Worker {worker_num}] ✅ Got email: {email}")
                        return email
            except:
                pass

            # Method 2: Try JavaScript extraction
            try:
                email = await mail_page.evaluate(
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
                    print(f"[Worker {worker_num}] ✅ Got email: {email}")
                    return email
            except Exception as e:
                pass

            await asyncio.sleep(1)

        print(f"[Worker {worker_num}] ❌ Failed to get email after {max_attempts} attempts")
        return None

    except Exception as e:
        print(f"[Worker {worker_num}] ❌ Failed to get email from mail.tm: {e}")
        return None

async def wait_for_wolt_verification_email(mail_page, worker_num):
    """Wait for and extract Wolt verification link from mail.tm inbox"""
    print(f"[Worker {worker_num}] 📬 Waiting for Wolt verification email...")

    max_wait = 90
    start_time = asyncio.get_event_loop().time()
    first_check = True

    while asyncio.get_event_loop().time() - start_time < max_wait:
        try:
            if not first_check:
                await mail_page.reload(wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(1)
            else:
                first_check = False
                await asyncio.sleep(2)

            wolt_message = None

            # Look for Wolt email (from info@wolt.com)
            try:
                spans = mail_page.locator('span.truncate')
                count = await spans.count()

                for i in range(count):
                    span = spans.nth(i)
                    text = await span.inner_text()
                    if 'wolt.com' in text.lower() or 'wolt' in text.lower():
                        wolt_message = span.locator('xpath=ancestor::li').first
                        print(f"[Worker {worker_num}] ✅ Found Wolt email!")
                        break
            except:
                pass

            # Fallback: check for any message
            if not wolt_message:
                try:
                    clickable_messages = mail_page.locator('li.cursor-pointer, li[role="button"]')
                    if await clickable_messages.count() > 0:
                        wolt_message = clickable_messages.first
                except:
                    pass

            if wolt_message:
                print(f"[Worker {worker_num}] 🖱️  Clicking on message...")
                await wolt_message.click()
                await asyncio.sleep(3)

                # Extract verification link
                try:
                    verify_link = mail_page.locator('a[href*="magic_login"]').first
                    verify_url = await verify_link.get_attribute('href', timeout=5000)

                    if verify_url:
                        # Clean the URL (remove &amp;)
                        verify_url = verify_url.replace('&amp;', '&')
                        print(f"[Worker {worker_num}] ✅ Found verification URL!")
                        return verify_url
                except:
                    pass

                # Fallback: regex extraction
                page_content = await mail_page.content()
                url_pattern = r'https://wolt\.com/me/magic_login[^"\s<>]+'
                match = re.search(url_pattern, page_content)

                if match:
                    verify_url = match.group(0)
                    # Clean the URL
                    verify_url = verify_url.replace('&amp;', '&')
                    print(f"[Worker {worker_num}] ✅ Found verification URL via regex!")
                    return verify_url
                else:
                    # Go back and try again
                    try:
                        await mail_page.go_back()
                        await asyncio.sleep(2)
                    except:
                        pass

        except Exception as e:
            pass

        print(f"[Worker {worker_num}] ⏳ Checking inbox... ({int(asyncio.get_event_loop().time() - start_time)}s elapsed)")
        await asyncio.sleep(5)

    print(f"[Worker {worker_num}] ❌ Verification email not received")
    return None

async def worker_loop(worker_num, phone_queue):
    """Worker that continuously processes phone numbers from queue"""
    success_count = 0
    fail_count = 0

    while True:
        # Get next phone number from queue
        if not phone_queue:
            break

        phone_number = phone_queue.pop(0)
        print(f"\n[Worker {worker_num}] 🔢 Trying phone: +380{phone_number} ({len(phone_queue)} remaining)")

        # Try to create account with this phone
        result = await create_account_with_retry(worker_num, phone_number, phone_queue)

        if result:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count

async def create_account_with_retry(worker_num, phone_number, phone_queue):
    """Create account with automatic retry for 'phone in use' errors"""
    browser = None
    playwright_instance = None
    start_time = datetime.now()

    try:
        # Step 1: Start browser with TWO pages (one for mail.tm, one for wolt.com)
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Create mail.tm page for email
        mail_page = await context.new_page()
        mail_page.set_default_timeout(15000)

        # Get temp email from mail.tm
        email = await get_mailtm_email(mail_page, worker_num)

        if not email:
            print(f"[Worker {worker_num}] ❌ Failed to get email, skipping number")
            return False

        # Extract password from mail.tm (it's visible on the page)
        password = "N/A"  # mail.tm doesn't provide password in same way

        # Step 2: Create Wolt page
        wolt_page = await context.new_page()
        wolt_page.set_default_timeout(15000)

        # Step 3: Go to Wolt & handle cookies
        print(f"[Worker {worker_num}] 🌐 Opening Wolt...")
        await wolt_page.goto('https://wolt.com/', wait_until='domcontentloaded')
        await asyncio.sleep(2)

        try:
            print(f"[Worker {worker_num}] 🍪 Handling cookies...")
            cookie_button = wolt_page.locator('button[data-test-id="decline-button"]')
            await cookie_button.wait_for(state='visible', timeout=8000)
            await cookie_button.click()
            await asyncio.sleep(1)
        except:
            pass

        # Step 4: Sign up flow
        print(f"[Worker {worker_num}] 🖱️  Starting signup...")
        await wolt_page.click('button[data-test-id="UserStatus.Signup"]', timeout=10000)
        await asyncio.sleep(1.5)

        await wolt_page.locator('input[data-test-id="MethodSelect.EmailInput"]').fill(email)
        await asyncio.sleep(0.5)
        await wolt_page.locator('button[data-test-id="StepMethodSelect.NextButton"]').click()

        print(f"[Worker {worker_num}] ⏳ Waiting for email confirmation...")
        await wolt_page.locator('h2:has-text("Great, check your inbox!")').first.wait_for(timeout=20000)
        print(f"[Worker {worker_num}] ✅ Email sent!")

        # Step 5: Switch to mail.tm page to check for verification email
        print(f"[Worker {worker_num}] 📧 Switching to mail.tm to check inbox...")
        await mail_page.bring_to_front()
        await asyncio.sleep(1)

        verification_link = await wait_for_wolt_verification_email(mail_page, worker_num)

        if not verification_link:
            print(f"[Worker {worker_num}] ❌ No verification email, skipping")
            return False

        # Step 6: Switch back to Wolt page and open verification link
        print(f"[Worker {worker_num}] 🔗 Opening verification link...")
        await wolt_page.bring_to_front()
        await wolt_page.goto(verification_link, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # Step 7: Find form (iframe or page)
        frames = wolt_page.frames
        form_locator = None

        for frame in frames:
            try:
                country_input = frame.locator('input#CreateAccount\\.Country')
                if await country_input.count() > 0:
                    print(f"[Worker {worker_num}] 📋 Found form in iframe")
                    form_locator = frame
                    break
            except:
                continue

        if not form_locator:
            print(f"[Worker {worker_num}] 📋 Form is on main page")
            form_locator = wolt_page

        # Step 8: Fill form - Hungary
        print(f"[Worker {worker_num}] 🇭🇺 Selecting Hungary...")
        country_input = form_locator.locator('input#CreateAccount\\.Country')
        await country_input.click()
        await asyncio.sleep(0.5)
        await country_input.press_sequentially("Hun", delay=50)
        await asyncio.sleep(0.3)
        await country_input.press("Enter")
        await asyncio.sleep(0.5)

        # Step 9: Generate and enter names
        first_name = random_name(9)
        last_name = random_name(10)
        print(f"[Worker {worker_num}] 👤 Entering name: {first_name} {last_name}")
        await form_locator.locator('input[data-test-id="CreateAccount.FirstName"]').fill(first_name)
        await asyncio.sleep(0.3)
        await form_locator.locator('input[data-test-id="CreateAccount.LastName"]').fill(last_name)
        await asyncio.sleep(0.3)

        # Step 10: Ukraine phone code
        print(f"[Worker {worker_num}] 🇺🇦 Selecting Ukraine (+380)...")
        phone_country_input = form_locator.locator('input#CreateAccount\\.PhoneNumberCountryCode')
        await phone_country_input.click()
        await asyncio.sleep(0.5)
        await phone_country_input.press_sequentially("Ukr", delay=50)
        await asyncio.sleep(0.3)
        await phone_country_input.press("Enter")
        await asyncio.sleep(0.5)

        # Step 11: Enter phone number
        print(f"[Worker {worker_num}] 📱 Entering phone: +380{phone_number}")
        await form_locator.locator('input[data-test-id="CreateAccount.PhoneNumber"]').fill(phone_number)
        await asyncio.sleep(0.5)

        # Step 12: Click Next
        await form_locator.locator('button[data-test-id="CreateAccount.Continue"]').click()
        await asyncio.sleep(2)

        # Step 13: Check for "phone already in use" error
        try:
            phone_in_use = form_locator.locator('[data-test-id="PhoneNumberInUse.Title"]')
            if await phone_in_use.is_visible(timeout=3000):
                print(f"[Worker {worker_num}] ⚠️  Phone +380{phone_number} already in use!")

                # Click back button
                try:
                    back_button = form_locator.locator('button:has(svg)').first
                    await back_button.click()
                    await asyncio.sleep(1)
                    print(f"[Worker {worker_num}] ⏪ Clicked back, will try next number...")
                except:
                    pass

                # Close browser and return False to try next number
                return False
        except:
            pass  # No error, continue

        # Step 14: Send SMS
        print(f"[Worker {worker_num}] 📲 Sending SMS verification...")
        try:
            await form_locator.locator('button[data-test-id="VerifyPhoneNumberMethodSelect.SmsButton"]').click()
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[Worker {worker_num}] ⚠️  SMS button error: {str(e)[:80]}")
            return False

        # Step 15: Resend SMS 4 times
        rate_limited = False
        for i in range(SMS_RESEND_COUNT):
            try:
                print(f"[Worker {worker_num}] 🔄 Resend {i + 1}/{SMS_RESEND_COUNT}...")

                await form_locator.locator('button[data-test-id="VerifyCode.CodeNotReceived"]').first.click()
                await asyncio.sleep(1)

                await form_locator.locator('button[data-test-id="NoCodeReceived.SmsButton"]').first.click()
                await asyncio.sleep(1.5)

                # Check for rate limit
                try:
                    rate_limit_error = form_locator.locator('[data-test-id="NoCodeReceived.Error"]')
                    if await rate_limit_error.is_visible(timeout=2000):
                        print(f"[Worker {worker_num}] ⚠️  Rate limit reached!")
                        rate_limited = True
                        break
                except:
                    pass

            except Exception as e:
                print(f"[Worker {worker_num}] ⚠️  Resend error: {str(e)[:80]}")
                break

        if rate_limited:
            print(f"[Worker {worker_num}] ⏭️  Skipping due to rate limit")

        # Step 16: Save account info
        elapsed = (datetime.now() - start_time).total_seconds()
        account_info = f"Email: {email} | Name: {first_name} {last_name} | Phone: +380{phone_number} | Time: {elapsed:.1f}s\n"

        with open('wolt_accounts.txt', 'a', encoding='utf-8') as f:
            f.write(account_info)

        print(f"[Worker {worker_num}] ✅ SUCCESS in {elapsed:.1f}s!")
        print(f"[Worker {worker_num}] 💾 Saved: {email} | +380{phone_number}")

        return True

    except Exception as e:
        print(f"[Worker {worker_num}] ❌ Error: {str(e)[:150]}")
        return False
    finally:
        # Always close browser
        if browser:
            try:
                await browser.close()
            except:
                pass
        if playwright_instance:
            try:
                await playwright_instance.stop()
            except:
                pass

async def main(workers):
    """Main function with robust queue-based processing"""
    try:
        # Read phone numbers into queue
        with open('numbers.txt', 'r', encoding='utf-8') as f:
            phone_queue = [line.strip() for line in f if line.strip()]

        if not phone_queue:
            print("❌ No phone numbers found in numbers.txt")
            return

        total_numbers = len(phone_queue)
        print(f"🚀 Starting with {total_numbers} phone numbers")
        print(f"⚙️  Workers: {workers} | SMS Resends: {SMS_RESEND_COUNT}")
        print(f"📧 Using mail.tm website for temporary emails")
        print(f"📋 Queue-based processing - workers will keep going until all numbers are done\n")

        # Start workers
        worker_tasks = []
        for i in range(workers):
            worker_tasks.append(worker_loop(i + 1, phone_queue))

        # Wait for all workers to finish
        results = await asyncio.gather(*worker_tasks, return_exceptions=True)

        # Count results
        total_success = 0
        total_fail = 0

        for i, result in enumerate(results):
            if isinstance(result, tuple):
                success, fail = result
                total_success += success
                total_fail += fail
                print(f"Worker {i+1}: ✅ {success} success, ❌ {fail} failed")
            else:
                print(f"Worker {i+1}: ❌ Error: {result}")

        print(f"\n{'='*60}")
        print(f"🎉 COMPLETED!")
        print(f"📊 Total: {total_numbers} numbers")
        print(f"✅ Success: {total_success}")
        print(f"❌ Failed: {total_fail}")
        print(f"📝 Processed: {total_success + total_fail}/{total_numbers}")
        print(f"{'='*60}")

    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}")
        print("💡 Create numbers.txt file")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    print(f"{'='*60}")
    print("🍕 Wolt Account Creator - Mail.tm Edition")
    print(f"{'='*60}\n")

    # Ask user for number of workers
    while True:
        try:
            workers_input = input("How many workers do you need? (default 3): ").strip()

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

    print(f"\n✅ Using {workers} worker(s)")
    print("🔄 Workers will process numbers from shared queue")
    print("💪 Script will continue until all numbers are processed!")
    print("📧 Each worker opens mail.tm in browser to get temporary email\n")

    asyncio.run(main(workers))
